#!/usr/bin/env python3
"""
Ecosystem access scanner -- who can reach whom, and how.

Builds the matrix behind the dashboard's ECOSYSTEM ACCESS tab: for every
chat project (a ~/projects/<name> checkout on a box with Claude Code) and
every target project (a checkout, or an ecosystem-listed deploy, on any
box), can the source

  SSH  -- get a shell on the target's box
  FLD  -- read (RO) / write (RW) the target's project folder
  DB   -- read (RO) / write (RW) the target's database

How it gathers facts, all read-only:
  * DEV runs PROBE locally, and over SSH on every other box it can reach
    (trying the ~/.ssh/config alias first, then fresh LAN addresses from
    `tailscale status`, pinned to the alias's known host key so a changed
    IP can't silently point us at a different machine).
  * Nothing ever SSHes *out* of a non-DEV box (Guardrails: AMI & co are
    leaves). Their outbound SSH is inferred statically instead: a private
    key on box A whose public half is in box B's authorized_keys, plus
    TCP :22 on B reachable from A.
  * DB credentials are never read off-box. The probe reports only each
    key's JWT role and a short sha256 prefix, which is enough to match a
    project's key to the Supabase instance that issued it.

Run by hand (writes state/access_matrix.json):
  python3 app/access_scan.py
The dashboard runs the same scan via POST /api/access/scan.
"""

import json
import re
import subprocess
import sys
import time
from pathlib import Path

import common

MATRIX_FILE = common.STATE_DIR / "access_matrix.json"

SSH_TIMEOUT = 60        # whole remote probe, seconds
CONNECT_TIMEOUT = 5

# Runs on each box (stdlib only). TARGETS is prepended by the scanner.
PROBE = r'''
import base64, glob, hashlib, json, os, re, socket, subprocess
HOME = os.path.expanduser("~")
out = {"hostname": socket.gethostname(), "user": os.environ.get("USER") or os.getlogin()}

def sh(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return ""

# LAN only: drop loopback, tailnet (100.x) and docker bridges (172.16-31).
out["ips"] = sorted({m.split("/")[0] for m in re.findall(r"inet (\S+)", sh(["ip", "-4", "-o", "addr"]))
                     if not re.match(r"(127\.|100\.|172\.(1[6-9]|2\d|3[01])\.)", m)})

# ---- SSH: config aliases, own keypairs, trusted keys
aliases, cur = [], None
try:
    for line in open(os.path.join(HOME, ".ssh/config")):
        parts = line.strip().split(None, 1)
        if len(parts) < 2 or parts[0].startswith("#"):
            continue
        k, v = parts[0].lower(), parts[1].strip()
        if k == "host":
            cur = {"alias": v, "hostname": v, "user": "", "identity": ""}
            aliases.append(cur)
        elif cur and k in ("hostname", "user", "hostkeyalias"):
            cur[k] = v
        elif cur and k == "identityfile":
            cur["identity"] = v
except OSError:
    pass
out["ssh_aliases"] = [a for a in aliases if "github.com" not in a["hostname"]]

keys = []
for pub in glob.glob(os.path.join(HOME, ".ssh/*.pub")):
    if os.path.exists(pub[:-4]):
        f = open(pub).read().split()
        if len(f) >= 2:
            keys.append({"name": os.path.basename(pub[:-4]), "blob": f[1]})
out["ssh_keys"] = keys
auth = []
try:
    for line in open(os.path.join(HOME, ".ssh/authorized_keys")):
        f = line.split()
        for i, tok in enumerate(f):
            if tok.startswith("ssh-") or tok.startswith("ecdsa-"):
                if i + 1 < len(f):
                    auth.append({"blob": f[i + 1], "comment": " ".join(f[i + 2:])})
                break
except OSError:
    pass
out["authorized"] = auth

# ---- Projects: folder perms, SQLite files, DB creds (role + hash only)
SKIP = ("/venv/", "/node_modules/", "/.git/", "/dist/", "/_Archive/")
def jwt_role(v):
    try:
        p = v.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4))).get("role", "")
    except Exception:
        return ""
def h(v):
    return hashlib.sha256(v.encode()).hexdigest()[:12]

projects = []
for d in sorted(glob.glob(os.path.join(HOME, "projects/*/"))):
    d = d.rstrip("/")
    p = {"name": os.path.basename(d), "r": os.access(d, os.R_OK | os.X_OK),
         "w": os.access(d, os.W_OK), "sqlite": [], "creds": [], "supabase": None,
         "chat": os.path.exists(os.path.join(d, "CLAUDE.md")) or os.path.isdir(os.path.join(d, ".claude"))}
    for pat in ("*.db", "*.sqlite", "*.sqlite3", "*/*.db", "*/*.sqlite", "*/*.sqlite3",
                "*/*/*.db", "*/*/*.sqlite3"):
        for f in glob.glob(os.path.join(d, pat)):
            if not any(s in f + "/" for s in SKIP):
                p["sqlite"].append({"path": os.path.relpath(f, d), "r": os.access(f, os.R_OK),
                                    "w": os.access(f, os.W_OK)})
    envs = [f for f in glob.glob(os.path.join(d, "**/.env*"), recursive=True)
            + glob.glob(os.path.join(d, "**/*.env"), recursive=True)
            if not any(s in f for s in SKIP) and not re.search(r"\.(example|orig|sample|template)", f)]
    for f in sorted(set(envs)):
        try:
            lines = open(f).read().splitlines()
        except OSError:
            continue
        vals = {}
        for line in lines:
            m = re.match(r"\s*(?:export\s+)?([A-Z0-9_]+)\s*=\s*(.*)", line)
            if m:
                vals[m.group(1)] = m.group(2).strip().strip('"').strip("'")
        rel = os.path.relpath(f, d)
        url = next((v for k, v in vals.items() if "SUPABASE" in k and "URL" in k), "")
        for k, v in vals.items():
            if v.startswith("eyJ") and jwt_role(v) in ("anon", "service_role"):
                p["creds"].append({"file": rel, "var": k, "role": jwt_role(v), "hash": h(v), "url": url})
        if "SERVICE_ROLE_KEY" in vals and "ANON_KEY" in vals and "JWT_SECRET" in vals:
            p["supabase"] = {"file": rel, "port": int(vals.get("KONG_HTTP_PORT") or 8000),
                             "anon": h(vals["ANON_KEY"]), "service": h(vals["SERVICE_ROLE_KEY"])}
    projects.append(p)
out["projects"] = projects

# ---- Reachability
def tcp(host, port):
    try:
        socket.create_connection((host, port), timeout=2).close()
        return True
    except OSError:
        return False
out["tcp"] = {"%s:%d" % (hh, pp): tcp(hh, pp) for hh, pp in TARGETS}
print(json.dumps(out))
'''


# ---- helpers --------------------------------------------------------------------

def _run(cmd, stdin=None, timeout=SSH_TIMEOUT):
    try:
        r = subprocess.run(cmd, input=stdin, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timed out"
    except OSError as e:
        return 127, "", str(e)


def _tailscale_peers(ts_ips):
    """{tailnet_ip: [current direct LAN ip, ...]} from DEV's tailscale view.
    CurAddr is empty until a direct path is warm, so ping each box first --
    that's how a box whose DHCP lease moved (AMI, 2026-09-23) still gets
    found at its new LAN address."""
    peers = {}
    for ip in ts_ips:
        _, out, _ = _run(["tailscale", "ping", "-c", "1", "--timeout", "3s", ip], timeout=8)
        m = re.search(r"via (\d+\.\d+\.\d+\.\d+):\d+", out)
        if m and not m.group(1).startswith("100."):
            peers[ip] = [m.group(1)]
    rc, out, _ = _run(["tailscale", "status", "--json"], timeout=10)
    if rc != 0:
        return peers
    try:
        data = json.loads(out)
    except ValueError:
        return peers
    for p in list((data.get("Peer") or {}).values()) + [data.get("Self") or {}]:
        lan = []
        cur = (p.get("CurAddr") or "").rsplit(":", 1)[0]
        if cur and not cur.startswith("100."):
            lan.append(cur)
        for ip in p.get("TailscaleIPs") or []:
            peers.setdefault(ip, [])
            peers[ip] = sorted(set(peers[ip] + lan))
    return peers


def _probe(prog, cmd):
    rc, out, err = _run(cmd, stdin=prog)
    if rc == 0:
        try:
            return json.loads(out.strip().splitlines()[-1]), None
        except (ValueError, IndexError):
            return None, "bad probe output"
    msg = (err.strip().splitlines() or ["exit %d" % rc])[-1]
    return None, msg


def _ssh_cmd(alias, host):
    """SSH to `host` using `alias`'s key + user, pinned to the host key
    known for the alias (its own HostKeyAlias if set, else its HostName)."""
    return ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=%d" % CONNECT_TIMEOUT,
            "-o", "StrictHostKeyChecking=yes", "-o", "IdentitiesOnly=yes",
            "-o", "HostKeyAlias=" + (alias.get("hostkeyalias") or alias["hostname"]),
            "-i", alias["identity"] or "~/.ssh/id_ed25519",
            "-l", alias["user"] or "bdr", host, "python3", "-"]


# ---- scan -----------------------------------------------------------------------

def run_scan(eco=None):
    started = time.time()
    eco = eco or common.load_ecosystem()
    servers = [s for s in eco.get("servers", []) if s.get("provisioned", True)]
    ts_peers = _tailscale_peers([s["tailscale"] for s in servers if s.get("tailscale")])

    # Candidate addresses per server: ecosystem LAN, tailscale's current
    # direct endpoint, tailnet IP (DB reachability only -- never SSH).
    lan_of, tsip_of = {}, {}
    for s in servers:
        lan = [s["address"]] if s.get("address") else []
        lan += ts_peers.get(s.get("tailscale") or "", [])
        lan_of[s["name"]] = list(dict.fromkeys(lan))
        tsip_of[s["name"]] = s.get("tailscale") or ""
    targets = sorted({(ip, port) for s in servers for ip in lan_of[s["name"]] + [tsip_of[s["name"]]]
                      if ip for port in (22, 8000)} | {("127.0.0.1", 8000)})
    prog = "TARGETS = %r\n" % targets + PROBE

    dev = next((s for s in servers if s.get("dev_host")), servers[0])
    boxes = {}
    local, err = _probe(prog, ["python3", "-"])
    boxes[dev["name"]] = {"probe": local, "error": err, "via": "local"}
    dev_aliases = (local or {}).get("ssh_aliases", [])
    for ip in (local or {}).get("ips", []):
        if ip not in lan_of[dev["name"]]:
            lan_of[dev["name"]].append(ip)

    for s in servers:
        name = s["name"]
        has_projects = any(p.get("runs_on") == name for p in eco.get("projects", []))
        if s is dev or not (s.get("claude") or has_projects):
            boxes.setdefault(name, {"probe": None, "error": "not a project box", "via": None})
            continue
        cands = lan_of[name]
        alias = next((a for a in dev_aliases if a["hostname"] in cands), None)
        attempts = []
        if alias:
            order = [alias["hostname"]] + [c for c in cands if c != alias["hostname"]]
        else:
            alias = {"alias": "", "hostname": cands[0] if cands else "", "user": "bdr", "identity": ""}
            order = cands
        box = {"probe": None, "error": "no address", "via": None, "alias": alias.get("alias"),
               "alias_host": alias.get("hostname"), "attempts": attempts}
        for host in order:
            data, err = _probe(prog, _ssh_cmd(alias, host))
            attempts.append({"host": host, "ok": data is not None, "error": err})
            if data is not None:
                box.update(probe=data, error=None, via=host)
                break
            box["error"] = err
        boxes[name] = box

    return _build_matrix(eco, servers, boxes, lan_of, tsip_of, dev["name"], started)


def _build_matrix(eco, servers, boxes, lan_of, tsip_of, dev_name, started):
    issues = []
    eco_projects = {p["name"]: p for p in eco.get("projects", [])}
    srv_by_name = {s["name"]: s for s in servers}
    for s in servers:
        pr = boxes[s["name"]]["probe"]
        if pr:
            lan_of[s["name"]] = list(dict.fromkeys(pr["ips"] + lan_of[s["name"]]))

    # ---- nodes: rows = chat checkouts on Claude boxes; cols = every checkout/deploy
    nodes, proj_on = [], {}
    for s in servers:
        name, pr = s["name"], boxes[s["name"]]["probe"]
        if pr:
            for p in pr["projects"]:
                proj_on[(name, p["name"])] = p
                nodes.append({"id": name + "/" + p["name"], "server": name, "project": p["name"],
                              "row": bool(s.get("claude")) and p.get("chat", True), "scanned": True})
        else:
            for p in eco_projects.values():
                if p.get("runs_on") == name and p.get("exists", True):
                    nodes.append({"id": name + "/" + p["name"], "server": name, "project": p["name"],
                                  "row": False, "scanned": False})
    nodes_by_server = {}
    for n in nodes:
        nodes_by_server.setdefault(n["server"], []).append(n)
    server_list = [{"name": s["name"], "nickname": s.get("nickname", ""),
                    "scanned": boxes[s["name"]]["probe"] is not None,
                    "error": boxes[s["name"]]["error"], "via": boxes[s["name"]]["via"],
                    "hostname": (boxes[s["name"]]["probe"] or {}).get("hostname"),
                    "ips": (boxes[s["name"]]["probe"] or {}).get("ips") or lan_of[s["name"]],
                    "tailscale": tsip_of[s["name"]]}
                   for s in servers if s["name"] in nodes_by_server]

    # ---- drift / problems worth shouting about
    for s in servers:
        b, pr = boxes[s["name"]], boxes[s["name"]]["probe"]
        if pr and s.get("address") and s["address"] not in pr["ips"]:
            issues.append("%s: ecosystem LAN address %s is stale -- box now has %s."
                          % (s["name"], s["address"], ", ".join(pr["ips"])))
        if pr and pr["hostname"].lower() != s["name"].lower():
            issues.append("%s: machine hostname is '%s', not '%s'." % (s["name"], pr["hostname"], s["name"]))
        if b.get("alias") and b.get("via") and b["via"] != b.get("alias_host"):
            issues.append("%s: DEV's ssh alias '%s' points at %s, which doesn't answer; box is "
                          "reachable at %s. Fix HostName in DEV ~/.ssh/config."
                          % (s["name"], b["alias"], b["alias_host"], b["via"]))
        if s["name"] != dev_name and not pr and b["error"] != "not a project box":
            tried = "; ".join("%s: %s" % (a["host"], a["error"]) for a in b.get("attempts", [])) or b["error"]
            issues.append("%s: could not be scanned from DEV (%s)." % (s["name"], tried))

    # ---- supabase instances + key hash -> (instance, role)
    instances, key_role = {}, {}
    for (srv, pname), p in proj_on.items():
        if p.get("supabase"):
            inst = dict(p["supabase"], server=srv, project=pname)
            instances[(srv, pname)] = inst
            key_role[inst["anon"]] = (inst, "RO")
            key_role[inst["service"]] = (inst, "RW")

    def target_db(srv, pname):
        """What database does target (srv, pname) own? -> dict or None."""
        seen = set()
        while (srv, pname) not in seen:
            seen.add((srv, pname))
            if (srv, pname) in instances:
                return {"kind": "supabase", "inst": instances[(srv, pname)]}
            p = proj_on.get((srv, pname))
            if p and p["sqlite"]:
                return {"kind": "sqlite", "files": p["sqlite"]}
            ep = eco_projects.get(pname) or {}
            if ep.get("runs_on") and ep["runs_on"] != srv:
                return None  # a source checkout, not the deploy -- its DB lives elsewhere
            dbdesc = ep.get("database", "") or ""
            if dbdesc.startswith("shares:"):
                pname = dbdesc.split(":", 1)[1].strip()
                srv = (eco_projects.get(pname) or {}).get("runs_on", srv)
                continue
            if dbdesc.lower().startswith("supabase"):
                inst = next((i for i in instances.values() if i["server"] == srv), None)
                return {"kind": "supabase", "inst": inst} if inst else {"kind": "supabase", "inst": None}
            return None
        return None

    def reach(src_srv, dst_srv, port):
        pr = boxes[src_srv]["probe"]
        if not pr:
            return False
        if src_srv == dst_srv and pr["tcp"].get("127.0.0.1:%d" % port):
            return True
        return any(pr["tcp"].get("%s:%d" % (ip, port)) for ip in lan_of[dst_srv] + [tsip_of[dst_srv]] if ip)

    def ssh_cell(src_srv, dst_srv):
        if src_srv == dst_srv:
            return {"v": "=", "note": "same box -- no SSH needed"}
        src, dst = boxes[src_srv]["probe"], boxes[dst_srv]["probe"]
        if src_srv == dev_name:
            b = boxes[dst_srv]
            if b["probe"] is None:
                return {"v": "N", "note": "DEV can't SSH in: " + (b["error"] or "unreachable")}
            if b.get("alias") and b["via"] == b["alias_host"]:
                return {"v": "Y", "note": "ssh %s (%s) -- verified live" % (b["alias"], b["via"])}
            return {"v": "!", "note": "works only via %s -- alias '%s' -> %s is stale"
                    % (b["via"], b.get("alias") or "(none)", b.get("alias_host"))}
        if not src or not dst:
            return {"v": "?", "note": "box not scanned"}
        trusted = {a["blob"]: a["comment"] for a in dst["authorized"]}
        keys = [k["name"] for k in src["ssh_keys"] if k["blob"] in trusted]
        port = any(src["tcp"].get("%s:22" % ip) for ip in lan_of[dst_srv])
        alias = next((a for a in src["ssh_aliases"] if a["hostname"] in lan_of[dst_srv]), None)
        if not keys:
            return {"v": "N", "note": "no key on %s is in %s's authorized_keys" % (src_srv, dst_srv)}
        if not port:
            return {"v": "N", "note": "key %s is trusted, but %s:22 isn't reachable" % (keys[0], dst_srv)}
        if not alias:
            return {"v": "!", "note": "key %s works, but no ~/.ssh/config alias for %s" % (keys[0], dst_srv)}
        return {"v": "Y", "note": "ssh %s (key %s) -- inferred, not dialled" % (alias["alias"], keys[0])}

    def perm(r, w):
        return "RW" if w and r else ("RO" if r else "N")

    cells = {}
    for rn in (n for n in nodes if n["row"]):
        row = cells.setdefault(rn["id"], {})
        src_p = proj_on[(rn["server"], rn["project"])]
        for cn in nodes:
            ssh = ssh_cell(rn["server"], cn["server"])
            same = rn["server"] == cn["server"]
            can_shell = same or ssh["v"] in ("Y", "!")
            tp = proj_on.get((cn["server"], cn["project"]))
            # folder
            if tp is None:
                fld = {"v": "?", "note": "not scanned"} if not cn["scanned"] else {"v": "", "note": ""}
            elif not can_shell:
                fld = {"v": "N", "note": "no shell on " + cn["server"]}
            else:
                fld = {"v": perm(tp["r"], tp["w"]),
                       "note": ("local" if same else "over ssh") + " ~/projects/" + cn["project"]}
            # database
            db = {"v": "", "note": "no database"}
            tdb = target_db(cn["server"], cn["project"]) if cn["scanned"] else None
            if not cn["scanned"]:
                db = {"v": "?", "note": "not scanned"}
            elif tdb and tdb["kind"] == "sqlite":
                f = tdb["files"][0]
                db = ({"v": perm(f["r"], f["w"]), "note": "SQLite %s (file access%s)"
                       % (f["path"], "" if same else ", over ssh")} if can_shell
                      else {"v": "N", "note": "SQLite %s -- no shell on %s" % (f["path"], cn["server"])})
            elif tdb and tdb["kind"] == "supabase":
                inst = tdb["inst"]
                if inst is None:
                    db = {"v": "?", "note": "Supabase expected on %s but no instance found" % cn["server"]}
                else:
                    best = None
                    for c in src_p["creds"]:
                        hit = key_role.get(c["hash"])
                        if hit and hit[0] is inst and (best is None or hit[1] == "RW"):
                            best = (hit[1], c)
                    where = "Supabase @ %s (%s)" % (inst["server"], inst["project"])
                    if best is None:
                        db = {"v": "N", "note": where + " -- no key for it in this project"}
                    elif not reach(rn["server"], inst["server"], inst["port"]):
                        db = {"v": "N", "note": "%s -- has %s key (%s) but :%d unreachable"
                              % (where, best[1], best[0]["file"], inst["port"])}
                    else:
                        db = {"v": best[0], "note": "%s -- %s key in %s%s" % (
                            where, "service_role" if best[0] == "RW" else "anon (RLS-governed)",
                            best[1]["file"], "" if best[1]["url"] else " (no URL var set alongside it)")}
            row[cn["id"]] = {"ssh": ssh, "fld": fld, "db": db}

    result = {
        "scanned_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_s": round(time.time() - started, 1),
        "servers": server_list,
        "nodes": nodes,
        "cells": cells,
        "issues": issues,
    }
    tmp = MATRIX_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, indent=1))
    tmp.replace(MATRIX_FILE)
    return result


def load_matrix():
    try:
        return json.loads(MATRIX_FILE.read_text())
    except (OSError, ValueError):
        return None


if __name__ == "__main__":
    r = run_scan()
    print("scanned in %ss -> %s" % (r["duration_s"], MATRIX_FILE))
    for s in r["servers"]:
        print("  %-18s %s" % (s["name"], "ok via " + s["via"] if s["scanned"] else "NOT SCANNED: " + str(s["error"])))
    for i in r["issues"]:
        print("  ! " + i)
    sys.exit(0)
