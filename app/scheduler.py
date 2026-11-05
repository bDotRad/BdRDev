#!/usr/bin/env python3
"""
Claude Code round-robin scheduler.

Runs continuously, independent of the dashboard web app. Cycles through
whichever projects are currently selected (state/selected_projects.json,
written by the dashboard) and keeps up to MAX_CONCURRENT of them active at
once (each in its own tmux/Claude Code session) so one project stuck
waiting on a human response doesn't block every other selected project
from being picked up. For each active project:

  1. Check its _Requests/ folder for READY items (cheap -- just a
     directory listing + first-line reads, no Claude session needed for
     this part). See common.py / _Instructions/Requests.md for exactly
     what counts as "ready".
  2. If there are pending items: make sure that project's tmux/Claude
     Code session is running (start it if not), send it a prompt to
     process the requests, then loop back and check again shortly after.
  3. If empty: wait EMPTY_GRACE_SECONDS and check once more.
  4. If still empty on that second check: hibernate the session (kill
     the tmux session to free RAM) and free the slot for the next
     selected project with pending work.
  5. If nothing was ever running for this project, just move on straight
     away -- no point spawning Claude just to confirm there's nothing to
     do.

Writes its current state to state/scheduler_state.json so the dashboard
can display it, and appends transition events to state/activity_log.jsonl
so the dashboard can show a status log.

Run:
  python3 scheduler.py
(intended to run as a systemd service -- see ../systemd/bdrdev-scheduler.service)
"""

import json
import subprocess
import time
from datetime import datetime, timezone

import common

MAX_CONCURRENT = 2             # how many projects can have an active Claude Code session at once
EMPTY_GRACE_SECONDS = 30       # wait this long after first empty scan before rechecking
POLL_TICK_SECONDS = 5          # how often the main loop re-scans all active projects
IDLE_POOL_SLEEP = 5            # how long to sleep if no projects are selected (or none have work)
CLAIM_REFRESH_SECONDS = 10 * 60  # re-stamp our _Comms.md claim this often while a session works

# Claude Code's TUI runs on tmux's alternate screen, which tmux never adds to
# scrollback history -- capture-pane can only ever return what's currently
# drawn on screen, however many lines that is. Left at tmux's default 80x24,
# a console-tab snapshot is capped at 24 lines no matter how much has scrolled
# by, which looked like output getting silently cut off with no way to page
# back to it. Sizing the pane itself larger means each snapshot actually
# contains that much real recent history.
SESSION_COLS = 150
SESSION_ROWS = 70

# The unattended-behaviour half of the wake prompt -- kept verbatim (cancel
# interactive prompts, write questions into the request file, flip it to
# WAITING RESPONSE, end turn). The head that precedes it varies: see
# build_scan_prompt().
SCAN_PROMPT_TAIL = (
    "This session runs unattended -- nobody is watching the terminal. If you "
    "hit a decision only Brad can make, or any interactive prompt (a permission "
    "dialog, the AskUserQuestion tool, etc.), do NOT wait on it: cancel it, "
    "write your questions into the request file, set that file's first line to "
    "WAITING RESPONSE, and end your turn. See _Instructions/BdRDev.md. "
    "The scheduler has claimed this project for you in _Comms.md (line 1, "
    "`CLAIMED by scheduler`); read its log first, and if someone else's claim "
    "replaces it, stop editing and follow _Instructions/Comms.md."
)

SCAN_PROMPT_GENERIC_HEAD = (
    "Check the requests folder for new or updated files and process them now. "
)


def build_scan_prompt(project):
    """Build the wake prompt, leading with the READY request title(s).

    Session-naming surfaces (CloudCLI's sidebar, `claude --resume`) derive a
    session's name from the first few words of its first user message. The
    scheduler otherwise sends an identical string every wake, so every
    unattended session reads as "Check the requests folder...". Leading with
    the titles of whatever is pending at first prompt makes the name mean
    something. A session handles whatever goes READY over its whole life, so
    this only reflects the first prompt -- acceptable, still far better than
    identical names.

    Falls back to the generic wording if no titles resolve (race / edge
    case) rather than sending an empty list.
    """
    try:
        titles = [
            item["title"]
            for item in common.list_requests(project)
            if item["status"] in ("Ready", "Processing")
        ]
    except Exception:
        titles = []

    if titles:
        quoted = ", ".join(f'"{t}"' for t in titles)
        head = f"Process these pending requests now: {quoted}. "
    else:
        head = SCAN_PROMPT_GENERIC_HEAD
    return head + SCAN_PROMPT_TAIL


def write_state(active, pool):
    """active: dict of project name -> {"phase": ..., "pending": ...}."""
    active_list = [
        {"project": name, "phase": info["phase"], "pending": info["pending"]}
        for name, info in active.items()
    ]
    primary = active_list[0] if active_list else None
    common.SCHEDULER_STATE_FILE.write_text(
        json.dumps({
            "active_projects": active_list,
            # Kept for backward compatibility with anything still reading the
            # old single-project fields (e.g. an older dashboard build) --
            # reflects the first active project only.
            "active_project": primary["project"] if primary else None,
            "phase": primary["phase"] if primary else "idle",
            "pending": primary["pending"] if primary else None,
            "rotation_pool": pool,
            "last_update": datetime.now(timezone.utc).isoformat(),
        }, indent=2)
    )


def tmux_alive(project):
    session = f"{common.TMUX_SESSION_PREFIX}{project}"
    try:
        return subprocess.run(["tmux", "has-session", "-t", session], capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


SPAWN_READY_TIMEOUT = 20   # max seconds to wait for Claude Code's input box before giving up
SPAWN_READY_MARKER = "auto mode on"  # only appears once the input box is live


def _wait_until_ready(session, timeout=SPAWN_READY_TIMEOUT):
    """Poll the pane until Claude Code's input box is actually up.

    A fixed sleep after `tmux new-session` is unreliable -- boot time
    varies (network hiccups, auto-update checks, first-run trust prompt),
    and typing into a pane that hasn't switched into raw/interactive mode
    yet gets silently dropped rather than queued. Wait for a marker that
    only shows once the box is live instead of guessing a delay.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        out = subprocess.run(
            ["tmux", "capture-pane", "-t", session, "-p"],
            capture_output=True, text=True,
        )
        pane = out.stdout if out.returncode == 0 else ""
        if SPAWN_READY_MARKER in pane:
            return True
        if "Yes, I trust this folder" in pane:
            # First-run trust prompt. Claude Code now highlights "No, exit"
            # by default (Enter on it kills the session), so move the cursor
            # until "Yes" is the highlighted line, then confirm.
            yes_selected = any(
                "❯" in line and "Yes, I trust this folder" in line
                for line in pane.splitlines()
            )
            key = "Enter" if yes_selected else "Down"
            subprocess.run(["tmux", "send-keys", "-t", session, key])
        time.sleep(0.5)
    return False


def claim_for_scheduler(project):
    try:
        titles = [
            item["title"]
            for item in common.list_requests(project)
            if item["status"] in ("Ready", "Processing")
        ]
    except Exception:
        titles = []
    common.write_claim(project, common.SCHEDULER_CLAIMANT, ", ".join(titles) or "_Requests")


def spawn_session(project):
    session = f"{common.TMUX_SESSION_PREFIX}{project}"
    project_dir = common.PROJECTS_DIR / project
    claim_for_scheduler(project)
    subprocess.run([
        "tmux", "new-session", "-d", "-s", session,
        "-x", str(SESSION_COLS), "-y", str(SESSION_ROWS),
        "-c", str(project_dir), common.CLAUDE_LAUNCH_CMD,
    ])
    _wait_until_ready(session)


def ensure_independent_session():
    """Keep the always-on Independent Claude session alive.

    Unlike a normal project session, this one runs from PROJECTS_DIR
    itself (not a project's own directory), is never nudged with the
    scan-requests prompt, and is never hibernated for being idle -- it
    sits ready for the dashboard's Independent Claude tab to send it
    questions directly (via /api/console/<name>/send -> tmux_send).
    """
    session = f"{common.TMUX_SESSION_PREFIX}{common.INDEPENDENT_SESSION}"
    if tmux_alive(common.INDEPENDENT_SESSION):
        return
    subprocess.run([
        "tmux", "new-session", "-d", "-s", session,
        "-x", str(SESSION_COLS), "-y", str(SESSION_ROWS),
        "-c", str(common.PROJECTS_DIR), common.CLAUDE_LAUNCH_CMD,
    ])
    _wait_until_ready(session)


def send_prompt(project):
    session = f"{common.TMUX_SESSION_PREFIX}{project}"
    # Sending text and Enter in the same tmux send-keys call delivers them as
    # one fast burst, which Claude Code's input box treats as a paste -- the
    # trailing Enter becomes a newline instead of submitting. Splitting them
    # into two calls with a brief pause replicates an actual keypress and
    # submits properly.
    subprocess.run(["tmux", "send-keys", "-t", session, build_scan_prompt(project)])
    time.sleep(0.4)
    subprocess.run(["tmux", "send-keys", "-t", session, "Enter"])


def hibernate(project):
    session = f"{common.TMUX_SESSION_PREFIX}{project}"
    subprocess.run(["tmux", "kill-session", "-t", session], capture_output=True)
    common.release_claim(project, common.SCHEDULER_CLAIMANT)


def pick_next_candidate(pool, active, start_idx, last_seen_pending):
    """Scan the pool once, starting at start_idx, for a project that isn't
    already active and has pending work. Returns (project_or_None, next_idx)
    -- next_idx is where the following search should resume from, so
    projects get a fair round-robin turn instead of the same early project
    always winning a freed slot.
    """
    n = len(pool)
    for offset in range(n):
        idx = (start_idx + offset) % n
        project = pool[idx]
        if project in active:
            continue
        pending = common.pending_count(project)
        if pending != last_seen_pending.get(project):
            if pending > 0:
                common.log_event(project, "requests_ready", {"pending": pending})
            last_seen_pending[project] = pending
        if pending > 0 and not tmux_alive(project) and common.claimed_by_other(project):
            # Another session (e.g. Brad's interactive one) holds the
            # project -- don't start a second one on top of it.
            continue
        if pending > 0:
            return project, (idx + 1) % n
    return None, start_idx


def main_loop():
    active = {}              # project -> {"quiet_since": float|None, "prompted": int, "phase": ..., "pending": ...}
    rotation_idx = 0
    last_seen_pending = {}   # project -> last pending count we logged, for edge-triggered logging

    while True:
        ensure_independent_session()

        pool = common.load_selected()

        if not pool:
            write_state({}, [])
            time.sleep(IDLE_POOL_SLEEP)
            continue

        # Drop anything that fell out of the selected pool since it went active.
        for name in list(active.keys()):
            if name not in pool:
                del active[name]

        # Fill any free slots, round-robin, skipping projects already active.
        while len(active) < MAX_CONCURRENT:
            candidate, rotation_idx = pick_next_candidate(pool, active, rotation_idx, last_seen_pending)
            if candidate is None:
                break
            active[candidate] = {"quiet_since": None, "prompted": 0, "phase": "waking", "pending": 0}

        if not active:
            write_state({}, pool)
            time.sleep(IDLE_POOL_SLEEP)
            continue

        # One tick of work for every currently active project.
        for project in list(active.keys()):
            tracked = active[project]
            pending = common.pending_count(project)
            if pending != last_seen_pending.get(project):
                if pending > 0:
                    common.log_event(project, "requests_ready", {"pending": pending})
                last_seen_pending[project] = pending

            if pending > 0:
                just_spawned = False
                alive = tmux_alive(project)
                if common.claimed_by_other(project):
                    # Someone else claimed it in _Comms.md. Never spawn on
                    # top of them, and don't type into our own session
                    # either -- it reads the claim and stands down itself.
                    if not alive:
                        common.log_event(project, "claimed_elsewhere", {"pending": pending})
                        del active[project]
                    continue
                if not alive:
                    common.log_event(project, "session_waking", {"pending": pending})
                    spawn_session(project)
                    just_spawned = True
                    tracked["claim_refreshed"] = time.time()
                elif time.time() - tracked.get("claim_refreshed", 0) >= CLAIM_REFRESH_SECONDS:
                    # Keep our claim fresh so a long job never reads as
                    # abandoned (also re-claims a session that predates a
                    # scheduler restart).
                    claim_for_scheduler(project)
                    tracked["claim_refreshed"] = time.time()
                # Only nudge once per wake, and again if *more* items showed
                # up since the last nudge -- not on every poll tick. Claude
                # Code may still be mid-task (or showing a permission
                # prompt) between polls, and repeatedly typing into that
                # isn't safe or useful.
                if just_spawned or pending > tracked["prompted"]:
                    send_prompt(project)
                    tracked["prompted"] = pending
                tracked["quiet_since"] = None
                tracked["phase"] = "processing"
                tracked["pending"] = pending
                continue

            # Nothing pending right now.
            if tmux_alive(project):
                if tracked["quiet_since"] is None:
                    # Just went quiet -- give it one grace period before giving up.
                    tracked["quiet_since"] = time.time()
                    tracked["phase"] = "waiting"
                    tracked["pending"] = 0
                elif time.time() - tracked["quiet_since"] >= EMPTY_GRACE_SECONDS:
                    recheck = common.pending_count(project)
                    if recheck == 0:
                        common.log_event(project, "session_hibernated")
                        hibernate(project)
                        del active[project]
                    else:
                        # Something showed up during the grace period.
                        tracked["quiet_since"] = None
                        tracked["phase"] = "processing"
                        tracked["pending"] = recheck
                # else: still within the grace period, leave it "waiting".
            else:
                # Already quiet, nothing to wake for -- free the slot.
                del active[project]

        write_state(active, pool)
        time.sleep(POLL_TICK_SECONDS)


if __name__ == "__main__":
    common.record_scheduler_start()
    main_loop()
