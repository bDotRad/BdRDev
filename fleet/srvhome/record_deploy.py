#!/usr/bin/env python3
"""Record the current HEAD of a git repo into the srvhome deploy DB.

Usage:
    record_deploy.py <app-name> <repo-path>
    record_deploy.py --range <A>..<B> <app-name> <repo-path>
    record_deploy.py --backfill <app-name> <repo-path> [N]

Called three ways:
  * from each app repo's .git/hooks/post-merge  -> records the new HEAD
    after a `git pull`, with recorded_at = now (a real deploy).
  * with --range ORIG_HEAD..HEAD (also from post-merge) -> records EVERY
    commit a fast-forward pull brought in, all stamped with this one pull
    time, so a K-commit pull shows K real rows not one.
  * with --backfill (from install.sh)           -> seeds the last N
    commits so history is not empty on day one (backfilled = 1,
    recorded_at = commit date).
"""

from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from store import connect, record  # noqa: E402

DB_PATH = os.path.join(HERE, "srvhome.db")
SEP = "\x1e"  # ASCII record separator, safe inside commit messages

# commit-message trailer lines that add noise to the history view
_TRAILER_PREFIXES = (
    "co-authored-by:", "claude-session:", "signed-off-by:",
    "🤖 generated with", "generated with [claude",
)


def _clean_body(body: str) -> str:
    kept = [
        ln for ln in body.splitlines()
        if not ln.strip().lower().startswith(_TRAILER_PREFIXES)
    ]
    return "\n".join(kept).strip()


def _log(repo: str, count: int, rev_range: str = "",
         path_filter: str = "") -> list[dict]:
    fmt = SEP.join(["%h", "%s", "%b", "%aI"])
    args = ["git", "-C", repo, "log", "--abbrev-commit", "--abbrev=7",
            f"--pretty=format:{fmt}%x1f"]
    if rev_range:
        args.append(rev_range)          # e.g. ORIG_HEAD..HEAD -- every commit a pull brought
    else:
        args.append(f"-n{count}")
    if path_filter:
        # only commits that touched this sub-path (srvhome's own dir), so
        # its history isn't every unrelated BdRDev commit
        args += ["--", path_filter]
    out = subprocess.run(args, capture_output=True, text=True, timeout=15)
    if out.returncode != 0:
        sys.stderr.write(out.stderr)
        return []
    commits = []
    for chunk in out.stdout.split("\x1f"):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        parts = chunk.split(SEP)
        if len(parts) < 4:
            continue
        sha, subject, body, aiso = parts[0], parts[1], parts[2], parts[3]
        commits.append({"sha": sha, "subject": subject,
                        "body": _clean_body(body), "committed_at": aiso})
    return commits


def main(argv: list[str]) -> int:
    backfill = False
    rev_range = ""
    path_filter = ""
    while argv and argv[0].startswith("--"):
        flag = argv[0]
        if flag == "--backfill":
            backfill = True
            argv = argv[1:]
        elif flag == "--range" and len(argv) >= 2:
            rev_range = argv[1]
            argv = argv[2:]
        elif flag == "--path" and len(argv) >= 2:
            path_filter = argv[1]
            argv = argv[2:]
        else:
            break

    if len(argv) < 2:
        sys.stderr.write(__doc__)
        return 2

    app, repo = argv[0], os.path.expanduser(argv[1])
    count = int(argv[2]) if len(argv) > 2 else (30 if backfill else 1)

    if not os.path.isdir(os.path.join(repo, ".git")):
        sys.stderr.write(f"record_deploy: {repo} is not a git repo\n")
        return 1

    commits = _log(repo, count, rev_range, path_filter)
    # a range that resolves to nothing (e.g. a no-op pull) -> fall back to HEAD
    if not commits and rev_range:
        commits = _log(repo, 1, "", path_filter)
    if not commits:
        sys.stderr.write("record_deploy: no commits found\n")
        return 1

    con = connect(DB_PATH)
    new = 0
    try:
        for c in commits:
            added = record(
                con, app, c["sha"], c["subject"], c["body"],
                c["committed_at"], backfilled=backfill,
                recorded_at=c["committed_at"] if backfill else None,
            )
            new += 1 if added else 0
    finally:
        con.close()

    mode = "backfilled" if backfill else "recorded"
    print(f"record_deploy: {app} {mode} {new} new / {len(commits)} seen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
