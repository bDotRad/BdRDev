#!/usr/bin/env python3
"""srvhome - the per-server home page for this box.

Runs on a fleet server (first: BdRPiSrvAMI / the Pi), binds to
127.0.0.1:8610, and is exposed by that box's Nginx (under /status/ and,
with the updated route, at / on the bdrpisrvami name).

The page has four parts:

  1. a **server panel** - hardware, OS, uptime/load/temp, disk, the
     software stack (Docker/nginx/Python + Supabase container health),
     pending apt updates, network interfaces and Tailscale;
  2. **app tiles** - one per app this box hosts (name, description, a
     link if it has a web route yet), plus the version deployed here now
     (7-char commit SHA) and branch;
  3. a **deploy history** per app - every version this box has pulled,
     from the SQLite DB the git post-merge hook writes to;
  4. a **Claude box** - a small chat panel that shells out to the
     `claude` CLI already authenticated on this box (`claude -p`, JSON
     output). In print mode read/search tools work; edits and bash are
     auto-denied, so it answers questions but does not act.

Pure Python 3 standard library - no Flask, no pip. Config: apps.json,
srvhome.conf.json.
"""

from __future__ import annotations

import html
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
# srvhome.py always lives at <repo>/fleet/srvhome/ inside a BdRDev
# checkout; the fleet standard-header logo is the dashboard's own asset.
# Missing (loose file copy, no checkout) -> the header just omits it.
LOGO_PATH = os.path.normpath(
    os.path.join(HERE, "..", "..", "app", "static", "rat-logo.png"))
DB_PATH = os.path.join(HERE, "srvhome.db")
APPS_JSON = os.path.join(HERE, "apps.json")
CONF_JSON = os.path.join(HERE, "srvhome.conf.json")
CHAT_SESSION_FILE = os.path.join(HERE, ".chat_session")

from store import connect, history_for, latest_for  # noqa: E402

CLAUDE_BIN = (
    shutil.which("claude")
    or os.path.expanduser("~/.local/bin/claude")
)
HOME = os.path.expanduser("~")
PROJECTS_DIR = os.path.join(HOME, "projects")

# The manual "pull + apply new migrations + rebuild" script that the
# dashboard "Update" button drives per app (BdRDev/fleet/update.sh,
# deployed here as ~/projects/update.sh). Reused rather than
# reimplemented so the two paths never diverge.
UPDATE_SCRIPT = os.path.join(PROJECTS_DIR, "update.sh")
CHECK_INTERVAL_S = 900      # background "is GitHub ahead?" poll (~15 min)
UPDATE_TIMEOUT_S = 1200     # hard cap on one git pull + npm build

# srvhome tracks its OWN version the same way it tracks an app. When this
# file runs from inside a git checkout (the BdRPiSrvAMI deploy is a
# read-only BdRDev checkout, run from fleet/srvhome/ within it), "Check
# GitHub" / "Pull" / deploy history all work against that repo, keyed as
# "srvhome". When it's just a loose copy of the files, the self panel
# degrades to "not a git checkout on this box".
SELF_NAME = "srvhome"


def _self_repo_root() -> str:
    """The git work-tree root above fleet/srvhome/, or HERE when srvhome is
    just a loose copy of the files (no checkout)."""
    return _git(HERE, "rev-parse", "--show-toplevel") or HERE


def self_app() -> dict:
    """srvhome-as-an-app: the checkout it lives in, so check_one() /
    run_update() operate on the whole repo the same as for a hosted app."""
    return {"name": SELF_NAME, "path": _self_repo_root()}


def checkables() -> list[dict]:
    """Everything the version checker watches: the hosted apps + srvhome."""
    return load_apps() + [self_app()]


# --------------------------------------------------------------------------
# config
# --------------------------------------------------------------------------

def load_conf() -> dict:
    conf = {"server": os.uname().nodename, "bind_host": "127.0.0.1",
            "bind_port": 8610, "history_limit": 40,
            "chat_enabled": True, "chat_extra_args": [],
            "chat_timeout_s": 180, "chat_max_prompt": 4000}
    try:
        with open(CONF_JSON) as fh:
            conf.update(json.load(fh))
    except FileNotFoundError:
        pass
    return conf


def load_apps() -> list[dict]:
    try:
        with open(APPS_JSON) as fh:
            return json.load(fh)
    except FileNotFoundError:
        return []


# --------------------------------------------------------------------------
# small shell / file helpers
# --------------------------------------------------------------------------

def _sh(cmd: list[str], timeout: float = 5.0, want_stderr: bool = False) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=timeout)
        if out.returncode != 0 and not want_stderr:
            return ""
        text = (out.stdout or "")
        if want_stderr:
            text = (text + out.stderr) if text else (out.stderr or "")
        return text.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _read(path: str) -> str:
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError:
        return ""


def _git(path: str, *args: str) -> str:
    try:
        out = subprocess.run(["git", "-C", path, *args],
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


_RUNNING_SHA: str | None = None


def running_sha() -> str:
    """The 7-char SHA this srvhome *process* was started from — frozen at
    first call (module load / after a self-restart), so it can diverge
    from HEAD if someone pulls without restarting."""
    global _RUNNING_SHA
    if _RUNNING_SHA is None:
        _RUNNING_SHA = _git(HERE, "rev-parse", "--short=7", "HEAD") or ""
    return _RUNNING_SHA


def _human_secs(s: float) -> str:
    s = int(s)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, _ = divmod(s, 60)
    parts = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    if m or not parts:
        parts.append(f"{m}m")
    return " ".join(parts)


def _human_bytes(n: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(n) < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PiB"


# --------------------------------------------------------------------------
# server info
# --------------------------------------------------------------------------

_info_cache: dict = {"at": 0.0, "data": None}
_INFO_TTL = 15.0


def _meminfo() -> dict:
    info = {}
    for line in _read("/proc/meminfo").splitlines():
        k, _, rest = line.partition(":")
        try:
            info[k.strip()] = int(rest.strip().split()[0]) * 1024  # kB -> B
        except (ValueError, IndexError):
            pass
    total = info.get("MemTotal", 0)
    avail = info.get("MemAvailable", 0)
    return {"total": total, "available": avail, "used": max(total - avail, 0),
            "pct": round((total - avail) / total * 100) if total else 0}


def _disk(path: str) -> dict | None:
    try:
        st = os.statvfs(path)
    except OSError:
        return None
    total = st.f_blocks * st.f_frsize
    free = st.f_bfree * st.f_frsize
    avail = st.f_bavail * st.f_frsize
    used = total - free
    return {"mount": path, "total": total, "used": used, "avail": avail,
            "pct": round(used / total * 100) if total else 0}


def _cpu_temp() -> float | None:
    raw = _read("/sys/class/thermal/thermal_zone0/temp")
    try:
        return round(int(raw) / 1000, 1)
    except ValueError:
        return None


def _docker() -> dict:
    ver = _sh(["docker", "--version"], 6)
    ver = ver.replace("Docker version ", "").split(",")[0] if ver else ""
    lines = [ln for ln in _sh(
        ["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Status}}"], 8
    ).splitlines() if ln.strip()]
    running = healthy = total = 0
    supa = {"total": 0, "healthy": 0, "running": 0}
    for ln in lines:
        name, _, status = ln.partition("\t")
        total += 1
        is_run = status.startswith("Up")
        is_ok = "(healthy)" in status
        running += is_run
        healthy += is_ok
        if name.startswith(("supabase-", "realtime-dev.")):
            supa["total"] += 1
            supa["running"] += is_run
            supa["healthy"] += is_ok
    return {"version": ver, "containers_total": total,
            "containers_running": running, "containers_healthy": healthy,
            "supabase": supa}


def _net() -> dict:
    ifaces = []
    for ln in _sh(["ip", "-o", "-4", "addr", "show"], 5).splitlines():
        f = ln.split()
        if len(f) < 4:
            continue
        name, addr = f[1], f[3]
        if name == "lo" or name.startswith(("docker", "br-", "veth")):
            continue
        ifaces.append({"name": name, "addr": addr})
    # primary LAN IP: the src of the default route (skip tailscale)
    lan_ip = ""
    route = _sh(["ip", "-4", "route", "get", "1.1.1.1"], 5)
    for tok in route.split():
        if tok == "src":
            idx = route.split().index("src")
            lan_ip = route.split()[idx + 1]
            break
    if not lan_ip and ifaces:
        lan_ip = ifaces[0]["addr"].split("/")[0]
    return {"lan_ip": lan_ip, "ifaces": ifaces,
            "hostname": os.uname().nodename,
            "fqdn": _sh(["hostname", "-f"], 3)}


def _tailscale() -> dict:
    raw = _sh(["tailscale", "status", "--json"], 8)
    if not raw:
        return {"up": False}
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        return {"up": False}
    self_ = d.get("Self", {}) or {}
    peers = d.get("Peer", {}) or {}
    online = sum(1 for p in peers.values() if p.get("Online"))
    return {
        "up": d.get("BackendState") == "Running",
        "ips": self_.get("TailscaleIPs", []),
        "dnsname": (self_.get("DNSName") or "").rstrip("."),
        "magicdns": d.get("MagicDNSSuffix", ""),
        "tailnet": (d.get("CurrentTailnet", {}) or {}).get("Name", ""),
        "peers_total": len(peers),
        "peers_online": online,
        "peer_names": sorted(
            (p.get("DNSName", "").split(".")[0] or p.get("HostName", ""))
            for p in peers.values()
        ),
    }


def server_info() -> dict:
    now = time.time()
    if _info_cache["data"] is not None and now - _info_cache["at"] < _INFO_TTL:
        return _info_cache["data"]

    os_release = {}
    for line in _read("/etc/os-release").splitlines():
        k, _, v = line.partition("=")
        os_release[k] = v.strip().strip('"')

    uname = os.uname()
    try:
        up_secs = float(_read("/proc/uptime").split()[0])
    except (ValueError, IndexError):
        up_secs = 0.0
    try:
        load = os.getloadavg()
    except OSError:
        load = (0.0, 0.0, 0.0)

    lscpu = _sh(["lscpu"], 5)
    cpu_model = ""
    for ln in lscpu.splitlines():
        if ln.startswith("Model name:"):
            cpu_model = ln.split(":", 1)[1].strip()
            break

    reboot_required = os.path.exists("/var/run/reboot-required")
    apt_up = _sh(["apt", "list", "--upgradable"], 15)
    apt_count = max(sum(1 for ln in apt_up.splitlines()
                        if "/" in ln and "Listing" not in ln), 0)

    nginx_v = (_sh(["nginx", "-v"], 4, want_stderr=True)
               or _sh(["/usr/sbin/nginx", "-v"], 4, want_stderr=True))
    nginx_v = nginx_v.replace("nginx version: ", "").strip()

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host": {
            "hostname": uname.nodename,
            "model": _read("/proc/device-tree/model").replace("\x00", "").strip(),
            "os": os_release.get("PRETTY_NAME", ""),
            "kernel": f"{uname.sysname} {uname.release}",
            "arch": uname.machine,
            "uptime": _human_secs(up_secs),
            "booted_at": datetime.fromtimestamp(
                time.time() - up_secs, timezone.utc
            ).isoformat(timespec="seconds"),
        },
        "cpu": {
            "model": cpu_model,
            "count": os.cpu_count() or 0,
            "load": [round(x, 2) for x in load],
            "temp_c": _cpu_temp(),
        },
        "mem": _meminfo(),
        "disks": [d for d in (_disk("/"), _disk("/boot/firmware")) if d],
        "software": {
            "docker": _docker(),
            "nginx": nginx_v,
            "python": f"{uname.sysname} python "
                      f"{'.'.join(map(str, __import__('sys').version_info[:3]))}",
        },
        "updates": {"apt_upgradable": apt_count,
                    "reboot_required": reboot_required},
        "net": _net(),
        "tailscale": _tailscale(),
    }
    _info_cache.update(at=now, data=data)
    return data


# --------------------------------------------------------------------------
# version check + one-click update
# --------------------------------------------------------------------------
#
# A background thread runs `git fetch` for each app every ~15 min and holds
# {behind, remote_sha, last_checked, error} in memory. "Check" forces one
# now; "Update" shells out to ~/projects/update.sh <app> under a per-app
# lock and keeps the captured output. State is deliberately in-memory —
# a restart just re-checks within a few seconds.

_check_state: dict[str, dict] = {}
_check_state_lock = threading.Lock()
_update_locks: dict[str, threading.Lock] = {}
_update_results: dict[str, dict] = {}
_updating: set[str] = set()
_update_meta_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _update_lock_for(name: str) -> threading.Lock:
    with _update_meta_lock:
        return _update_locks.setdefault(name, threading.Lock())


def check_one(app: dict) -> dict:
    """`git fetch` one app and compare HEAD to its upstream."""
    path = os.path.expanduser(app["path"])
    name = app["name"]
    res: dict = {"last_checked": _now_iso(), "behind": None,
                 "remote_sha": "", "error": ""}
    if not os.path.isdir(os.path.join(path, ".git")):
        res["error"] = "not a git repo on this box"
    else:
        fetched = subprocess.run(
            ["git", "-C", path, "fetch", "--quiet"],
            capture_output=True, text=True, timeout=120,
        )
        if fetched.returncode != 0:
            res["error"] = (fetched.stderr or "git fetch failed").strip()[-240:]
        else:
            upstream = _git(path, "rev-parse", "@{u}")
            if not upstream:
                res["error"] = "no upstream branch configured"
            else:
                behind = _git(path, "rev-list", "--count", "HEAD..@{u}")
                res["behind"] = int(behind) if behind.isdigit() else 0
                res["remote_sha"] = upstream[:7]
    with _check_state_lock:
        _check_state[name] = res
    return res


def check_all() -> None:
    for app in checkables():
        try:
            check_one(app)
        except (OSError, subprocess.SubprocessError) as exc:
            with _check_state_lock:
                _check_state[app["name"]] = {
                    "last_checked": _now_iso(), "behind": None,
                    "remote_sha": "", "error": str(exc)[-240:],
                }


def _checker_loop() -> None:
    while True:
        check_all()
        time.sleep(CHECK_INTERVAL_S)


def start_checker() -> None:
    threading.Thread(target=_checker_loop, name="srvhome-checker",
                     daemon=True).start()


def _self_pull(path: str) -> tuple[str, bool]:
    """`git pull --ff-only` the srvhome checkout. The caller schedules a
    restart when HEAD actually moved -- there's no build step."""
    try:
        proc = subprocess.run(
            ["git", "-C", path, "pull", "--ff-only", "--no-edit"],
            capture_output=True, text=True, timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return (f"git pull failed to start: {exc}", False)
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if proc.returncode != 0:
        return (out or "git pull --ff-only failed", False)
    return (out, True)


def _schedule_self_restart(delay: float = 1.5) -> None:
    """Re-exec srvhome so the freshly pulled code takes effect. The socket
    has allow_reuse_address, so the new process rebinds the same port."""
    def _restart() -> None:
        time.sleep(delay)
        os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])
    threading.Thread(target=_restart, name="srvhome-self-restart",
                     daemon=True).start()


def run_update(name: str) -> dict:
    """Pull + rebuild one app via ~/projects/update.sh, capturing output.
    For srvhome itself it's a plain `git pull --ff-only` + self-restart."""
    if name == SELF_NAME:
        app = self_app()
    else:
        app = {a["name"]: a for a in load_apps()}.get(name)
    if not app:
        return {"error": f"unknown app {name!r}"}
    path = os.path.expanduser(app["path"])

    lock = _update_lock_for(name)
    if not lock.acquire(blocking=False):
        return {"error": "an update is already running for this app",
                "_busy": True}
    with _update_meta_lock:
        _updating.add(name)
    started = _now_iso()
    sha_before = _git(path, "rev-parse", "--short=7", "HEAD")
    try:
        env = os.environ.copy()
        env["HOME"] = HOME
        env["PATH"] = os.path.expanduser("~/.local/bin") + ":" + \
            env.get("PATH", "/usr/local/bin:/usr/bin:/bin")
        if name == SELF_NAME:
            output, ok = _self_pull(path)
        elif os.path.exists(UPDATE_SCRIPT):
            proc = subprocess.run(
                ["bash", UPDATE_SCRIPT, name],
                cwd=PROJECTS_DIR, capture_output=True, text=True,
                timeout=UPDATE_TIMEOUT_S, env=env,
            )
            output = ((proc.stdout or "") + (proc.stderr or "")).strip()
            ok = proc.returncode == 0
        else:
            output = f"update.sh not found at {UPDATE_SCRIPT}"
            ok = False
    except subprocess.TimeoutExpired:
        output = f"update timed out after {UPDATE_TIMEOUT_S}s"
        ok = False
    except (OSError, subprocess.SubprocessError) as exc:
        output = f"update failed to start: {exc}"
        ok = False
    finally:
        with _update_meta_lock:
            _updating.discard(name)
        lock.release()

    sha_after = _git(path, "rev-parse", "--short=7", "HEAD")
    result = {
        "ok": ok,
        "started_at": started,
        "finished_at": _now_iso(),
        "sha_before": sha_before,
        "sha_after": sha_after,
        "changed": sha_before != sha_after,
        "output_tail": output[-6000:],
    }
    if name == SELF_NAME and ok and result["changed"]:
        result["output_tail"] = (
            (output + "\n\n" if output else "")
            + f"srvhome moving {sha_before or '?'} -> {sha_after or '?'}; "
            "restarting to load it…")[-6000:]
    with _update_meta_lock:
        _update_results[name] = result
    # the pull moved HEAD (or not) — refresh the "behind" read either way
    try:
        check_one(app)
    except (OSError, subprocess.SubprocessError):
        pass
    if name == SELF_NAME and ok and result["changed"]:
        _schedule_self_restart()
    return result


def app_check_view(name: str) -> dict:
    with _check_state_lock:
        chk = dict(_check_state.get(name, {}))
    with _update_meta_lock:
        return {
            "behind": chk.get("behind"),
            "remote_sha": chk.get("remote_sha", ""),
            "last_checked": chk.get("last_checked", ""),
            "check_error": chk.get("error", ""),
            "updating": name in _updating,
            "last_update_result": _update_results.get(name),
        }


# --------------------------------------------------------------------------
# apps
# --------------------------------------------------------------------------

def _built_info(path: str) -> dict:
    """What SHA the served bundle was actually built from.

    Each app's vite.config writes app/dist/build-info.json at build time
    ({sha, version, built_at}). Without this srvhome only knows the git
    HEAD, not what nginx is serving -- which is how a 3-commit-old bundle
    went unnoticed for 8h on 2026-08-30.
    """
    for rel in ("app/dist/build-info.json", "dist/build-info.json"):
        fp = os.path.join(path, rel)
        try:
            with open(fp) as fh:
                d = json.load(fh)
            return {"built_sha": str(d.get("sha", ""))[:7],
                    "built_version": d.get("version", ""),
                    "built_at": d.get("built_at", "")}
        except (OSError, ValueError):
            continue
    return {"built_sha": "", "built_version": "", "built_at": ""}


def app_state(app: dict, history_limit: int) -> dict:
    path = os.path.expanduser(app["path"])
    name = app["name"]
    present = os.path.isdir(os.path.join(path, ".git"))

    head_sha = _git(path, "rev-parse", "--short=7", "HEAD") if present else ""
    head_subject = _git(path, "log", "-1", "--format=%s") if present else ""
    branch = _git(path, "rev-parse", "--abbrev-ref", "HEAD") if present else ""
    has_commits = bool(head_sha)
    built = _built_info(path)

    con = connect(DB_PATH)
    try:
        rows = history_for(con, name, history_limit)
        latest = latest_for(con, name)
    finally:
        con.close()

    return {
        "name": name,
        "path": path,
        "description": app.get("description", ""),
        "url": app.get("url", ""),
        "url_label": app.get("url_label", ""),
        "present": present,
        "has_commits": has_commits,
        "branch": branch,
        "head_sha": head_sha,
        "head_subject": head_subject,
        "deployed_sha": (latest or {}).get("sha", "") or head_sha,
        "deployed_at": (latest or {}).get("recorded_at", ""),
        "running": None,   # live status still deferred
        "history": rows,
        # built_sha != head_sha  =>  nginx is serving a stale bundle
        "rebuild_needed": bool(
            built["built_sha"] and head_sha
            and built["built_sha"] != head_sha
        ),
        **built,
        **app_check_view(name),
    }


def self_state(history_limit: int) -> dict:
    """srvhome's own version panel -- the same shape as app_state() so the
    tile renderer and the poll JS can treat it identically. `present` is
    False (and everything degrades) when srvhome isn't run from a checkout."""
    present = _git(HERE, "rev-parse", "--is-inside-work-tree") == "true"
    path = self_app()["path"]

    head_sha = _git(path, "rev-parse", "--short=7", "HEAD") if present else ""
    head_subject = _git(path, "log", "-1", "--format=%s") if present else ""
    head_date = (_git(path, "log", "-1", "--format=%cd",
                      "--date=format-local:%Y.%m.%d_%H%M") if present else "")
    branch = _git(path, "rev-parse", "--abbrev-ref", "HEAD") if present else ""

    con = connect(DB_PATH)
    try:
        rows = history_for(con, SELF_NAME, history_limit)
        latest = latest_for(con, SELF_NAME)
    finally:
        con.close()

    return {
        "name": SELF_NAME,
        "path": path,
        "description": "",
        "url": "", "url_label": "",
        "present": present,
        "has_commits": bool(head_sha),
        "branch": branch,
        "head_sha": head_sha,
        "head_subject": head_subject,
        "head_date": head_date,
        "running_sha": running_sha(),
        "deployed_sha": (latest or {}).get("sha", "") or head_sha,
        "deployed_at": (latest or {}).get("recorded_at", ""),
        "running": None,
        "history": rows,
        # no build step -- srvhome is plain Python, HEAD is what runs
        "rebuild_needed": False,
        "built_sha": "", "built_version": "", "built_at": "",
        **app_check_view(SELF_NAME),
    }


def full_state() -> dict:
    conf = load_conf()
    apps = load_apps()
    limit = int(conf.get("history_limit", 40))
    return {
        "server": conf.get("server") or os.uname().nodename,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "chat_enabled": bool(conf.get("chat_enabled", True))
        and bool(CLAUDE_BIN and os.path.exists(CLAUDE_BIN)),
        "info": server_info(),
        "self": self_state(limit),
        "apps": [app_state(a, limit) for a in apps],
    }


# --------------------------------------------------------------------------
# claude chat
# --------------------------------------------------------------------------

_chat_lock = threading.Lock()

CHAT_SYSTEM = (
    "You are the assistant embedded in the srvhome dashboard on the "
    "server '{server}'. Answer questions about this box and the apps it "
    "hosts concisely. You are in a read-only web context: you may read "
    "and search files under ~/projects but cannot make changes."
)


def run_claude(message: str, reset: bool) -> dict:
    conf = load_conf()
    max_prompt = int(conf.get("chat_max_prompt", 4000))
    if len(message) > max_prompt:
        return {"error": f"message too long (max {max_prompt} chars)"}
    if not (CLAUDE_BIN and os.path.exists(CLAUDE_BIN)):
        return {"error": "claude CLI not found on this server"}

    if not _chat_lock.acquire(blocking=False):
        return {"error": "busy", "_busy": True}
    try:
        args = [CLAUDE_BIN, "-p", message, "--output-format", "json"]
        args += list(conf.get("chat_extra_args", []))
        sid = "" if reset else _read(CHAT_SESSION_FILE)
        if sid:
            args += ["--resume", sid]
        else:
            args += ["--append-system-prompt",
                     CHAT_SYSTEM.format(server=conf.get("server", ""))]

        env = os.environ.copy()
        env["HOME"] = HOME
        env["PATH"] = (os.path.dirname(CLAUDE_BIN) + ":"
                       + env.get("PATH", "/usr/bin:/bin"))

        def _invoke(argv):
            return subprocess.run(
                argv, cwd=PROJECTS_DIR, capture_output=True, text=True,
                timeout=float(conf.get("chat_timeout_s", 180)), env=env,
            )

        try:
            proc = _invoke(args)
            if proc.returncode != 0 and sid:
                # stale/invalid session - retry once, fresh
                fresh = [CLAUDE_BIN, "-p", message, "--output-format", "json"]
                fresh += list(conf.get("chat_extra_args", []))
                fresh += ["--append-system-prompt",
                          CHAT_SYSTEM.format(server=conf.get("server", ""))]
                proc = _invoke(fresh)
        except subprocess.TimeoutExpired:
            return {"error": "claude timed out"}

        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "").strip()[-300:]
            return {"error": f"claude exited {proc.returncode}: {tail}"}

        try:
            data = json.loads(proc.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            return {"error": "could not parse claude output"}

        new_sid = data.get("session_id")
        if new_sid:
            try:
                with open(CHAT_SESSION_FILE, "w") as fh:
                    fh.write(new_sid)
            except OSError:
                pass

        return {
            "reply": data.get("result", "") or "(no output)",
            "is_error": bool(data.get("is_error")),
            "cost_usd": data.get("total_cost_usd"),
            "num_turns": data.get("num_turns"),
            "denials": [d.get("tool_name") for d in
                       (data.get("permission_denials") or [])],
        }
    finally:
        _chat_lock.release()


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

PAGE_CSS = """
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:#0f1216;color:#d7dde3;
     font:15px/1.5 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
a{color:#6cb6ff}
header{padding:22px 28px;border-bottom:1px solid #232a31;background:#12171d}
/* fleet standard header block (BdRDev/_Instructions/WebUI.md), full
   three-line form -- srvhome has a running-vs-origin check so it shows
   the deploy-status line. Palette mapped to srvhome's literal colours. */
header .site-header{display:flex;align-items:center;gap:16px}
header .sh-logo{width:64px;height:64px;border-radius:50%;object-fit:cover;flex:none}
header .sh-stack{display:flex;flex-direction:column;gap:4px;min-width:0}
header .sh-name{font-weight:800;font-size:28px;line-height:1;letter-spacing:.04em;color:#7f97b8}
header .sh-name b{color:#e8edf2;font-weight:800}
header .sh-ver{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
               font-size:14px;color:#c7d0dc;margin-left:2px}
header .site-header.behind .sh-ver{color:#e3b341}
header .sh-status{display:flex;align-items:center;gap:8px;margin-left:2px;flex-wrap:wrap}
header .sh-pill{font:inherit;font-size:11px;font-weight:700;line-height:1.4;cursor:pointer;
               border:none;border-radius:5px;padding:1px 8px;color:#0f1115;background:#3fb950}
header .sh-pill.busy{background:#e3b341;cursor:default}
header .sh-pill:hover{filter:brightness(1.08)}
header .site-header.behind .sh-pill{background:#e3b341}
header .sh-chip{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;
               color:#8b96a1;border:1px solid #232a31;border-radius:5px;padding:1px 7px}
header .sh-chip b{font-weight:700;color:#3fb950}
header .site-header.behind .sh-chip b{color:#e3b341}
header .sh-status .s-none{color:#8b96a1;font-size:12px}
header .sub{color:#8b96a1;font-size:13px;margin-top:8px}
main{padding:24px 28px;max-width:1100px;margin:0 auto}
h2.sec{font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:#8b96a1;
       margin:34px 0 12px;border-bottom:1px solid #202730;padding-bottom:6px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}
.card{background:#141a20;border:1px solid #232a31;border-radius:10px;padding:14px 16px}
.card h3{margin:0 0 8px;font-size:12px;text-transform:uppercase;letter-spacing:.4px;
         color:#8b96a1}
.kv{display:flex;justify-content:space-between;gap:12px;padding:3px 0;font-size:13.5px}
.kv .k{color:#8b96a1}
.kv .v{text-align:right;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:#dbe3ea}
.bar{height:6px;border-radius:4px;background:#232a31;margin-top:6px;overflow:hidden}
.bar > i{display:block;height:100%;background:#3fb950}
.bar.warn > i{background:#d29922}
.bar.hot > i{background:#f85149}
.pill{display:inline-block;font-size:11px;padding:1px 8px;border-radius:20px;
      border:1px solid #333d47;color:#aab4bf;background:#1a2129;margin:2px 4px 2px 0}
.pill.ok{color:#7fd18c;border-color:#2f5136;background:#132018}
.pill.warn{color:#e3b341;border-color:#5c4813;background:#211c0f}
.tile{background:#141a20;border:1px solid #232a31;border-left:4px solid #3a4550;
      border-radius:10px;padding:18px 20px;margin-bottom:22px}
.card.updates{grid-column:1/-1}
.tile.selftile{margin:12px 0 0;padding:12px 14px;background:#0f151b}
.tile.selftile .row{margin:0 0 8px}
.tile.is-running{border-left-color:#3fb950}
.tile.is-unknown{border-left-color:#d29922}
.tile.is-stopped{border-left-color:#f85149}
.tile.is-absent {border-left-color:#3a4550}
.linkbtn{background:none;border:0;color:#6cb6ff;font:inherit;font-size:11px;
         text-transform:none;letter-spacing:0;cursor:pointer;padding:0 0 0 8px}
.tile h3{margin:0 0 4px;font-size:16px}
.tile .desc{color:#c2cbd4;font-size:13.5px;margin:2px 0 10px;max-width:70ch}
.row{display:flex;flex-wrap:wrap;gap:14px;align-items:baseline;margin:6px 0 12px}
.badge{font-size:12px;padding:2px 9px;border-radius:20px;border:1px solid #333d47;
       color:#aab4bf;background:#1a2129}
.sha{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:#e2c08d}
.sha.live{color:#7fd18c}
.muted{color:#8b96a1}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid #202730;vertical-align:top}
th{color:#8b96a1;font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.4px}
td.v{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:#e2c08d;white-space:nowrap}
td.v.live{color:#7fd18c}
td.t{white-space:nowrap;color:#9aa5b0}
td.desc{color:#9aa5b0;white-space:pre-wrap}
tr.live td{background:#122017}
tr.backfilled td.v{color:#8b96a1}
.live-tag{display:inline-block;margin-left:7px;padding:0 6px;font-size:10.5px;
          color:#7fd18c;border:1px solid #2f5136;border-radius:20px}
.empty{color:#8b96a1;font-style:italic;padding:6px 0}
details.hist{margin-top:8px}
details.hist summary{cursor:pointer;color:#8b96a1;font-size:12.5px}
/* version check / update */
.badge.ok{color:#7fd18c;border-color:#2f5136;background:#132018}
.badge.behind{color:#e3b341;border-color:#5c4813;background:#211c0f}
.badge.busy{color:#6cb6ff;border-color:#1f4b7a;background:#0f1b28}
.badge.fail{color:#e08a8a;border-color:#5a2f2f;background:#201313}
.acts{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:2px 0 10px}
.acts button{background:#20262d;border:1px solid #333d47;color:#cdd6df;border-radius:7px;
             padding:4px 12px;font:inherit;font-size:12.5px;cursor:pointer}
.acts button.primary{background:#1f6feb;border-color:#1f6feb;color:#fff}
.acts button:disabled{opacity:.45;cursor:default}
/* the Pull button flashes while GitHub is ahead of this box */
@keyframes srvpulse{0%,100%{box-shadow:0 0 0 0 rgba(31,111,235,.6)}
                    50%{box-shadow:0 0 0 7px rgba(31,111,235,0)}}
.acts button.flash{background:#1f6feb;border-color:#1f6feb;color:#fff;
                   animation:srvpulse 1.4s ease-in-out infinite}
@media (prefers-reduced-motion:reduce){
  .acts button.flash{animation:none;outline:2px solid #6cb6ff;outline-offset:2px}}
/* per-tile status box */
.statusbox{background:#0f151b;border:1px solid #232a31;border-radius:8px;
           padding:10px 12px;margin:2px 0 12px}
.statusbox .sline{font-size:13.5px;font-weight:600;color:#d7dde3;
                  display:flex;align-items:center;gap:8px}
.statusbox .sline::before{content:'';width:8px;height:8px;border-radius:50%;
                          background:#8b96a1;flex:none}
.statusbox.s-ok .sline::before{background:#3fb950}
.statusbox.s-behind .sline::before{background:#e3b341}
.statusbox.s-busy .sline::before{background:#6cb6ff;
                                 animation:srvpulse 1.4s ease-in-out infinite}
.statusbox.s-fail .sline::before{background:#f85149}
.statusbox .smeta{color:#8b96a1;font-size:11.5px;margin-top:4px;
                  font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.statusbox pre{background:#0c0f13;border:1px solid #202730;border-radius:6px;
               padding:9px 11px;font-size:11.5px;line-height:1.45;overflow:auto;
               max-height:240px;white-space:pre-wrap;color:#c2cbd4;margin:8px 0 0}
footer{max-width:1100px;margin:0 auto;padding:8px 28px 40px;color:#6b7580;font-size:12px}
/* chat */
#chat{background:#141a20;border:1px solid #232a31;border-radius:10px;padding:16px}
#chatlog{max-height:340px;overflow-y:auto;display:flex;flex-direction:column;gap:10px;
         margin-bottom:12px}
.msg{padding:9px 12px;border-radius:9px;font-size:14px;white-space:pre-wrap;max-width:88%}
.msg.u{align-self:flex-end;background:#1d2733;border:1px solid #2b3a4d}
.msg.a{align-self:flex-start;background:#161d24;border:1px solid #253039}
.msg.e{align-self:flex-start;background:#201313;border:1px solid #5a2f2f;color:#e08a8a}
.msg .meta{display:block;margin-top:5px;color:#6b7580;font-size:11px}
#chatform{display:flex;gap:8px}
#chatinput{flex:1;background:#0f1419;border:1px solid #2b3a4d;border-radius:8px;
           color:#e6edf3;padding:9px 11px;font:inherit;resize:vertical;min-height:42px}
#chat button{background:#1f6feb;border:0;color:#fff;border-radius:8px;padding:0 16px;
             font:inherit;cursor:pointer}
#chat button.ghost{background:#20262d;color:#aab4bf}
#chat button:disabled{opacity:.5;cursor:default}
"""


def _fmt_ts(iso: str, tz: bool = False) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return iso
    # commit dates carry their author's offset, recorded_at is UTC -- normalise
    # everything to this box's local time so the two columns line up.
    if dt.tzinfo is not None:
        dt = dt.astimezone()
    return dt.strftime("%Y-%m-%d %H:%M %Z" if tz else "%Y-%m-%d %H:%M")


def _kv(k: str, v: str) -> str:
    return f"<div class=kv><span class=k>{html.escape(k)}</span>" \
           f"<span class=v>{html.escape(str(v))}</span></div>"


def _meter(k: str, used: float, total: float, extra: str = "") -> str:
    pct = round(used / total * 100) if total else 0
    cls = "bar" + (" hot" if pct >= 90 else " warn" if pct >= 75 else "")
    return (f"<div class=kv><span class=k>{html.escape(k)}</span>"
            f"<span class=v>{_human_bytes(used)} / {_human_bytes(total)}"
            f"{(' · ' + extra) if extra else ''} ({pct}%)</span></div>"
            f"<div class='{cls}'><i style='width:{min(pct,100)}%'></i></div>")


def render_server_panel(info: dict, self_s: dict) -> str:
    h, c, m = info["host"], info["cpu"], info["mem"]
    sw, up, net, ts = info["software"], info["updates"], info["net"], info["tailscale"]
    dk = sw["docker"]
    o = ["<h2 class=sec>Server</h2><div class=grid>"]

    o.append("<div class=card><h3>Host</h3>")
    o.append(_kv("name", h["hostname"]))
    o.append(_kv("model", h["model"] or "—"))
    o.append(_kv("os", h["os"] or "—"))
    o.append(_kv("kernel", f"{h['kernel']} ({h['arch']})"))
    o.append(_kv("uptime", h["uptime"]))
    o.append(_kv("booted", _fmt_ts(h["booted_at"], tz=True)))
    o.append("</div>")

    o.append("<div class=card><h3>CPU &amp; memory</h3>")
    o.append(_kv("cpu", f"{c['model']} ×{c['count']}" if c["model"]
                 else f"×{c['count']}"))
    o.append(_kv("load", " / ".join(f"{x:.2f}" for x in c["load"])))
    if c["temp_c"] is not None:
        o.append(_kv("temp", f"{c['temp_c']} °C"))
    o.append(_meter("ram", m["used"], m["total"],
                    f"{_human_bytes(m['available'])} avail"))
    o.append("</div>")

    o.append("<div class=card><h3>Disk</h3>")
    for d in info["disks"]:
        o.append(_meter(d["mount"], d["used"], d["total"],
                        f"{_human_bytes(d['avail'])} free"))
    o.append("</div>")

    o.append("<div class=card><h3>Stack</h3>")
    o.append(_kv("docker", dk["version"] or "—"))
    o.append(_kv("containers",
                 f"{dk['containers_running']}/{dk['containers_total']} up"))
    sp = dk["supabase"]
    if sp["total"]:
        o.append(_kv("supabase",
                     f"{sp['healthy']}/{sp['total']} healthy"))
    o.append(_kv("nginx", sw["nginx"] or "—"))
    o.append(_kv("python", ".".join(map(str,
                 __import__("sys").version_info[:3]))))
    o.append("</div>")

    o.append("<div class='card updates'><h3>Updates</h3>")
    apt = up["apt_upgradable"]
    o.append(f"<span class='pill {'warn' if apt else 'ok'}'>"
             f"{apt} apt update{'s' if apt != 1 else ''}</span>")
    o.append(f"<span class='pill {'warn' if up['reboot_required'] else 'ok'}'>"
             f"{'reboot required' if up['reboot_required'] else 'no reboot needed'}"
             f"</span>")
    o.append(render_self_updates(self_s))
    o.append("</div>")

    o.append("<div class=card><h3>Network</h3>")
    o.append(_kv("lan ip", net["lan_ip"] or "—"))
    for i in net["ifaces"]:
        o.append(_kv(i["name"], i["addr"]))
    o.append("</div>")

    o.append("<div class=card><h3>Tailscale</h3>")
    if ts.get("up"):
        for ip in ts.get("ips", []):
            o.append(_kv("ip", ip))
        if ts.get("dnsname"):
            o.append(_kv("name", ts["dnsname"]))
        if ts.get("tailnet"):
            o.append(_kv("tailnet", ts["tailnet"]))
        o.append(_kv("peers",
                     f"{ts.get('peers_online', 0)}/{ts.get('peers_total', 0)} online"))
        for p in ts.get("peer_names", []):
            if p:
                o.append(f"<span class=pill>{html.escape(p)}</span>")
    else:
        o.append("<span class='pill warn'>not running</span>")
    o.append("</div>")

    o.append("</div>")
    return "".join(o)


def render_chat_panel() -> str:
    return """
<h2 class=sec>Ask Claude about this server</h2>
<div id=chat>
  <div id=chatlog></div>
  <form id=chatform>
    <textarea id=chatinput placeholder="e.g. which containers are unhealthy? what changed in PlanBdRad recently?"
              autocomplete=off></textarea>
    <button type=submit id=chatsend>Send</button>
    <button type=button id=chatreset class=ghost title="start a new conversation">New</button>
  </form>
  <div class=empty style="font-size:11.5px;margin-top:6px">
    Runs <code>claude -p</code> on this box (read-only: it can read and search
    <code>~/projects</code> but not change anything).
  </div>
</div>
<script>
(function(){
  var log=document.getElementById('chatlog'),
      form=document.getElementById('chatform'),
      input=document.getElementById('chatinput'),
      send=document.getElementById('chatsend'),
      reset=document.getElementById('chatreset');
  function add(cls,text,meta){
    var d=document.createElement('div'); d.className='msg '+cls; d.textContent=text;
    if(meta){var s=document.createElement('span'); s.className='meta'; s.textContent=meta; d.appendChild(s);}
    log.appendChild(d); log.scrollTop=log.scrollHeight; return d;
  }
  function ask(msg,doReset){
    send.disabled=true;
    var pend=add('a','…');
    fetch('api/chat',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:msg,reset:!!doReset})})
    .then(function(r){return r.json().then(function(j){return {ok:r.ok,j:j};});})
    .then(function(res){
      var j=res.j;
      if(!res.ok||j.error){pend.className='msg e';pend.textContent=j.error||('HTTP '+'error');return;}
      pend.textContent=j.reply;
      var bits=[];
      if(typeof j.cost_usd==='number') bits.push('$'+j.cost_usd.toFixed(4));
      if(j.num_turns) bits.push(j.num_turns+' turn'+(j.num_turns>1?'s':''));
      if(j.denials&&j.denials.length) bits.push('blocked: '+j.denials.join(', '));
      if(bits.length){var s=document.createElement('span');s.className='meta';s.textContent=bits.join(' · ');pend.appendChild(s);}
    })
    .catch(function(e){pend.className='msg e';pend.textContent=String(e);})
    .finally(function(){send.disabled=false;input.focus();});
  }
  form.addEventListener('submit',function(e){
    e.preventDefault();
    var msg=input.value.trim(); if(!msg)return;
    add('u',msg); input.value=''; ask(msg,false);
  });
  reset.addEventListener('click',function(){
    log.innerHTML=''; add('a','New conversation started.'); input.focus();
    fetch('api/chat',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:'',reset:true})}).catch(function(){});
  });
})();
</script>
"""


def _rel_age(iso: str) -> str:
    if not iso:
        return "never"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return iso
    secs = (datetime.now(timezone.utc) - dt).total_seconds()
    if secs < 90:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)}m ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    return f"{int(secs // 86400)}d ago"


def status_badge(app: dict) -> tuple[str, str, str]:
    """(tile-class, badge-class, badge-text) for an app's update status."""
    if not app["present"]:
        return "is-absent", "", "repo not on this box"
    if not app["has_commits"]:
        return "is-unknown", "", "repo empty"
    if app.get("updating"):
        return "is-unknown", "busy", "updating…"
    res = app.get("last_update_result")
    if res and not res.get("ok"):
        return "is-stopped", "fail", "last update failed"
    if app.get("check_error"):
        return "is-unknown", "", "check failed"
    behind = app.get("behind")
    if behind is None:
        return "is-unknown", "", "not checked yet"
    if behind > 0:
        return "is-unknown", "behind", (
            f"{behind} new commit{'s' if behind != 1 else ''} on GitHub "
            f"— Pull to deploy"
        )
    if app.get("rebuild_needed"):
        return "is-unknown", "behind", (
            f"serving {app.get('built_sha') or '?'} — rebuild needed"
        )
    return "is-running", "ok", "up to date"


def render_history_rows(app: dict) -> str:
    rows = app["history"]
    if not rows:
        return "<div class=empty data-role=hist>No deploy history recorded yet.</div>"
    out = [f"<details class=hist data-role=hist><summary>deploy history "
           f"({len(rows)})</summary>",
           "<table><thead><tr><th>Committed</th><th>Pulled</th>"
           "<th>Version</th><th>Commit</th></tr></thead><tbody>"]
    for r in rows:
        is_live = bool(r["sha"]) and r["sha"] == app["deployed_sha"]
        cls = " ".join(x for x in (
            "live" if is_live else "",
            "backfilled" if r.get("backfilled") else "") if x)
        tr = f" class='{cls}'" if cls else ""
        tag = " <span class=muted>(backfilled)</span>" if r.get("backfilled") else ""
        live_tag = " <span class=live-tag>live here</span>" if is_live else ""
        body = (r.get("body") or "").strip()
        title = html.escape(r["subject"] or "")
        if body:
            title += (f"<span class=muted title='{html.escape(body)}'> "
                      f"— {html.escape(body.splitlines()[0][:120])}</span>")
        out.append(
            f"<tr{tr}>"
            f"<td class=t>{html.escape(_fmt_ts(r.get('committed_at') or ''))}</td>"
            f"<td class=t>{html.escape(_fmt_ts(r['recorded_at']))}{tag}</td>"
            f"<td class='v{' live' if is_live else ''}'>"
            f"{html.escape(r['sha'])}{live_tag}</td>"
            f"<td>{title}</td></tr>")
    out.append("</tbody></table></details>")
    return "".join(out)


def _status_meta(app: dict) -> str:
    """The mono sub-line under the status box: what's where, right now."""
    bits: list[str] = []
    if app.get("last_checked"):
        bits.append(f"GitHub checked {_rel_age(app['last_checked'])}")
    elif app["present"] and app["has_commits"]:
        bits.append("GitHub not checked yet")
    if app.get("head_sha"):
        bits.append(f"HEAD {app['head_sha']}")
    if (app.get("behind") or 0) > 0 and app.get("remote_sha"):
        bits.append(f"GitHub {app['remote_sha']}")
    if app.get("built_sha"):
        bits.append(f"built {app['built_sha']}"
                    + (" (stale)" if app.get("rebuild_needed") else ""))
    res = app.get("last_update_result")
    if res and res.get("finished_at"):
        verb = "pulled" if res.get("changed") else "rebuilt"
        outcome = verb if res.get("ok") else "update failed"
        bits.append(f"last {outcome} {_rel_age(res['finished_at'])}")
    return " · ".join(bits)


def render_statusbox(app: dict) -> str:
    """Always-visible per-tile status panel: a status line, a mono meta
    sub-line, and (when an update has run) its captured output."""
    _tile_cls, bcls, btext = status_badge(app)
    skind = bcls or "none"
    tail = (app.get("last_update_result") or {}).get("output_tail", "")
    return (
        f"<div class='statusbox s-{skind}' data-role=statusbox>"
        f"<div class=sline data-role=status>{html.escape(btext)}</div>"
        f"<div class=smeta data-role=smeta>{html.escape(_status_meta(app))}</div>"
        f"<pre data-role=outpre{'' if tail else ' hidden'}>"
        f"{html.escape(tail)}</pre>"
        f"</div>"
    )


def render_site_header(s: dict) -> str:
    """The fleet standard header block (WebUI.md "Standard header
    block"): 64px logo + stacked app-name / version / deploy-status.
    srvhome renders the full three-line form -- it has a
    running-vs-origin check -- with the version-pill doubling as the
    "re-check GitHub" button. Degrades to name + version when srvhome
    isn't run from a checkout."""
    logo = ('<img class=sh-logo src="logo.png" alt="">'
            if os.path.isfile(LOGO_PATH) else "")
    name = "<span class=sh-name><b>SRV</b>HOME</span>"

    if not s["present"] or not s.get("has_commits"):
        why = ("loose file copy on this box, version not tracked"
               if not s["present"] else "repo present but empty")
        return (
            f"<div class='site-header' data-role=siteheader>{logo}"
            f"<div class=sh-stack>{name}"
            f"<span class=sh-ver>—</span>"
            f"<div class=sh-status><span class=s-none>srvhome — {why}</span>"
            f"</div></div></div>")

    behind = s.get("behind")
    head = s.get("head_sha", "")
    run = s.get("running_sha") or head
    drift = bool(run and head and run != head)
    is_behind = bool(behind) or drift or bool(s.get("check_error"))
    ver = " · ".join(x for x in (s.get("head_date", ""), head) if x) or head
    if s.get("updating"):
        pill = "checking…"
    elif s.get("check_error"):
        pill = "check failed"
    elif behind is None:
        pill = "check GitHub"
    elif behind > 0:
        pill = f"behind by {behind}"
    else:
        pill = "up to date"
    return (
        f"<div class='site-header{' behind' if is_behind else ''}' data-role=siteheader>"
        f"{logo}<div class=sh-stack>{name}"
        f"<span class=sh-ver>{html.escape(ver)}</span>"
        f"<div class=sh-status>"
        f"<button class=sh-pill id=shPill data-act=selfcheck "
        f"title='Re-check GitHub'>{html.escape(pill)}</button>"
        f"<span class=sh-chip>HEAD <b data-role=sh-head>{html.escape(head)}</b></span>"
        f"<span class=sh-chip>running <b data-role=sh-run>{html.escape(run)}</b></span>"
        f"</div></div></div>")


def render_self_updates(s: dict) -> str:
    """srvhome's own GitHub block for the Updates card -- same machinery as
    an app tile (statusbox + Check/Pull + deploy history), keyed 'srvhome'
    so the existing delegated click + poll JS drives it unchanged."""
    tile_cls, _b, _t = status_badge(s)
    behind = s.get("behind") or 0
    out = [f"<div class='tile selftile {tile_cls}' data-app='{SELF_NAME}'>"]
    out.append("<div class=row><strong>srvhome</strong>")
    if s.get("head_sha"):
        out.append(f"<span>HEAD <span class='sha live' data-role=sha>"
                   f"{html.escape(s['head_sha'])}</span></span>")
    if s.get("branch"):
        out.append(f"<span class=muted>branch {html.escape(s['branch'])}</span>")
    out.append("</div>")

    if s["present"] and s["has_commits"]:
        out.append(render_statusbox(s))
        out.append("<div class=acts>")
        out.append("<button data-act=check>Check GitHub</button>")
        out.append(f"<button data-act=update class='primary flash' "
                   f"{'' if behind > 0 else 'hidden'}>Pull ({behind})</button>")
        out.append("</div>")
    else:
        out.append(
            "<div class='statusbox s-none' data-role=statusbox>"
            "<div class=sline data-role=status>not a git checkout on this box"
            "</div><div class=smeta data-role=smeta>redeploy srvhome from a "
            "BdRDev checkout to enable self version-check — see "
            "DEPLOY-STATUS.md</div>"
            "<pre data-role=outpre hidden></pre></div>")
    out.append(render_history_rows(s))
    out.append("</div>")
    return "".join(out)


def render_apps(apps: list[dict]) -> str:
    out = ["<h2 class=sec>Apps hosted here "
           "<button id=checkall class=linkbtn>check GitHub — all apps + srvhome</button></h2>"]
    if not apps:
        out.append("<p class=empty>No apps configured (see apps.json).</p>")
    for app in apps:
        name = app["name"]
        tile_cls, _bcls, _btext = status_badge(app)
        behind = app.get("behind") or 0

        out.append(f"<div class='tile {tile_cls}' data-app='{html.escape(name)}'>")
        out.append(f"<h3>{html.escape(name)}</h3>")
        if app["description"]:
            out.append(f"<div class=desc>{html.escape(app['description'])}</div>")

        out.append("<div class=row>")
        if app["has_commits"]:
            out.append(f"<span>HEAD <span class='sha live' data-role=sha>"
                       f"{html.escape(app['head_sha'] or '?')}</span></span>")
            built = app.get("built_sha")
            if built:
                cls = "sha" if app.get("rebuild_needed") else "sha live"
                out.append(f"<span>· built <span class='{cls}' data-role=builtsha>"
                           f"{html.escape(built)}</span></span>")
            if app["branch"]:
                out.append(f"<span class=muted>branch {html.escape(app['branch'])}</span>")
        if app["url"]:
            label = app["url_label"] or app["url"]
            out.append(f"<span>· <a href='{html.escape(app['url'])}' "
                       f"target=_blank rel=noopener>{html.escape(label)}</a></span>")
        out.append("</div>")

        if app["has_commits"]:
            out.append(render_statusbox(app))

            show_update = behind > 0 or app.get("rebuild_needed")
            update_label = f"Pull ({behind})" if behind > 0 else "Rebuild"
            btn_cls = "primary flash" if behind > 0 else "primary"
            out.append("<div class=acts>")
            out.append("<button data-act=check>Check GitHub</button>")
            out.append(f"<button data-act=update class='{btn_cls}' "
                       f"{'' if show_update else 'hidden'}>{update_label}</button>")
            out.append("</div>")

        out.append(render_history_rows(app))
        out.append("</div>")
    return "".join(out)


APPS_SCRIPT = r"""
<script>
(function(){
  var POLL_MS = 15000;
  function post(url, body){
    return fetch(url, {method:'POST', headers:{'Content-Type':'application/json'},
                       body:JSON.stringify(body||{})})
           .then(function(r){ return r.json().then(function(j){return {ok:r.ok,j:j};}); });
  }
  function rel(iso){
    if(!iso) return 'never';
    var s=(Date.now()-new Date(iso).getTime())/1000;
    if(s<90) return 'just now';
    if(s<3600) return Math.floor(s/60)+'m ago';
    if(s<86400) return Math.floor(s/3600)+'h ago';
    return Math.floor(s/86400)+'d ago';
  }
  function badge(app){
    if(app.updating) return ['busy','updating…'];
    if(app.last_update_result && !app.last_update_result.ok) return ['fail','last update failed'];
    if(app.check_error) return ['none','check failed'];
    if(app.behind===null||app.behind===undefined) return ['none','not checked yet'];
    if(app.behind>0) return ['behind',
      app.behind+' new commit'+(app.behind===1?'':'s')+' on GitHub — Pull to deploy'];
    if(app.rebuild_needed) return ['behind','serving '+(app.built_sha||'?')+' — rebuild needed'];
    return ['ok','up to date'];
  }
  function metaLine(app){
    var b=[];
    if(app.last_checked) b.push('GitHub checked '+rel(app.last_checked));
    else if(app.head_sha) b.push('GitHub not checked yet');
    if(app.head_sha) b.push('HEAD '+app.head_sha);
    if(app.behind>0 && app.remote_sha) b.push('GitHub '+app.remote_sha);
    if(app.built_sha) b.push('built '+app.built_sha+(app.rebuild_needed?' (stale)':''));
    var r=app.last_update_result;
    if(r && r.finished_at){
      var v=r.changed?'pulled':'rebuilt';
      b.push('last '+(r.ok?v:'update failed')+' '+rel(r.finished_at));
    }
    return b.join(' · ');
  }
  function applyHeader(s){
    var sh=document.querySelector('[data-role=siteheader]');
    if(!sh || !s) return;
    var beh=s.behind;
    var drift=!!(s.running_sha && s.head_sha && s.running_sha!==s.head_sha);
    sh.classList.toggle('behind', !!beh || drift || !!s.check_error);
    var pill=sh.querySelector('#shPill');
    if(pill && !pill.classList.contains('busy'))
      pill.textContent = s.updating ? 'checking…'
                       : s.check_error ? 'check failed'
                       : (beh===null||beh===undefined) ? 'check GitHub'
                       : (beh>0 ? 'behind by '+beh : 'up to date');
    var hd=sh.querySelector('[data-role=sh-head]');
    if(hd && s.head_sha) hd.textContent=s.head_sha;
    var rn=sh.querySelector('[data-role=sh-run]');
    if(rn && s.running_sha) rn.textContent=s.running_sha;
  }
  function apply(state){
    applyHeader(state.self);
    var all=(state.apps||[]).slice();
    if(state.self && state.self.present) all.push(state.self);
    all.forEach(function(app){
      var tile=document.querySelector('.tile[data-app="'+app.name+'"]');
      if(!tile) return;
      var b=badge(app), box=tile.querySelector('[data-role=statusbox]');
      if(box && !tile.dataset.busy){
        box.className='statusbox s-'+b[0];
        var st=box.querySelector('[data-role=status]');
        if(st) st.textContent=b[1];
        var mt=box.querySelector('[data-role=smeta]');
        if(mt) mt.textContent=metaLine(app);
        var pre=box.querySelector('[data-role=outpre]'),
            tail=(app.last_update_result||{}).output_tail||'';
        if(pre){ pre.hidden=!tail; if(tail) pre.textContent=tail; }
      }
      var sha=tile.querySelector('[data-role=sha]');
      if(sha && app.head_sha) sha.textContent=app.head_sha;
      var bs=tile.querySelector('[data-role=builtsha]');
      if(bs && app.built_sha){ bs.textContent=app.built_sha;
        bs.className = app.rebuild_needed ? 'sha' : 'sha live'; }
      var upd=tile.querySelector('[data-act=update]');
      if(upd && !upd.dataset.busy){
        if(app.behind>0 || app.rebuild_needed){
          upd.hidden=false;
          upd.textContent = app.behind>0 ? 'Pull ('+app.behind+')' : 'Rebuild';
          upd.className = app.behind>0 ? 'primary flash' : 'primary';
        } else { upd.hidden=true; }
      }
    });
  }
  function refresh(){
    return fetch('api/state').then(function(r){return r.json();}).then(apply).catch(function(){});
  }
  document.addEventListener('click', function(ev){
    var btn=ev.target.closest('button'); if(!btn) return;

    if(btn.id==='checkall'){
      btn.disabled=true; btn.textContent='checking…';
      post('api/check').then(function(){ return refresh(); })
        .finally(function(){ btn.disabled=false; btn.textContent='check GitHub — all apps + srvhome'; });
      return;
    }
    if(btn.id==='shPill'){
      if(btn.classList.contains('busy')) return;
      btn.classList.add('busy'); btn.textContent='checking…';
      post('api/check',{app:'srvhome'}).then(function(){ return refresh(); })
        .finally(function(){ btn.classList.remove('busy'); });
      return;
    }
    var tile=btn.closest('.tile[data-app]'); if(!tile) return;
    var app=tile.dataset.app;
    var box=tile.querySelector('[data-role=statusbox]');
    function setStatus(kind,text){
      if(!box) return;
      box.className='statusbox s-'+kind;
      var st=box.querySelector('[data-role=status]');
      if(st) st.textContent=text;
    }

    if(btn.dataset.act==='check'){
      btn.disabled=true; var t=btn.textContent; btn.textContent='checking…';
      post('api/check',{app:app}).then(function(){ return refresh(); })
        .finally(function(){ btn.disabled=false; btn.textContent=t; });
    }
    else if(btn.dataset.act==='update'){
      var isSelf=(app==='srvhome');
      var ask=isSelf
        ? 'Pull the latest srvhome from GitHub and restart this dashboard now?'
        : 'Pull the latest '+app+' from GitHub and rebuild it on this server now?';
      if(!confirm(ask)) return;
      tile.dataset.busy='1';
      btn.dataset.busy='1'; btn.disabled=true; btn.textContent='Pulling…';
      btn.className='primary';
      setStatus('busy', isSelf ? 'pulling from GitHub and restarting…'
                               : 'pulling from GitHub and rebuilding…');
      var pre=box && box.querySelector('[data-role=outpre]');
      if(pre){ pre.hidden=false;
        pre.textContent=isSelf ? 'git pull --ff-only srvhome …'
                               : 'running update.sh '+app+' …'; }
      post('api/update',{app:app}).then(function(res){
        var j=res.j||{};
        if(pre) pre.textContent=j.output_tail||j.error||'(no output)';
        if(j.ok){
          if(isSelf && j.changed){
            setStatus('busy','restarting srvhome — reloading shortly');
            setTimeout(function(){ location.reload(); }, 6000);
          } else if(isSelf){
            setStatus('ok','already up to date');
            delete tile.dataset.busy;
            delete btn.dataset.busy; btn.disabled=false; btn.textContent='Pull (0)';
          } else {
            setStatus('ok','pulled — reloading');
            setTimeout(function(){ location.reload(); }, 1800);
          }
        } else {
          setStatus('fail','update failed — see output below');
          delete tile.dataset.busy;
          delete btn.dataset.busy; btn.disabled=false; btn.textContent='Retry Pull';
        }
      }).catch(function(e){
        if(pre){ pre.hidden=false; pre.textContent=String(e); }
        setStatus('fail','update failed — see output below');
        delete tile.dataset.busy;
        delete btn.dataset.busy; btn.disabled=false; btn.textContent='Retry Pull';
      });
    }
  });
  setInterval(refresh, POLL_MS);
})();
</script>
"""


def render_html(state: dict) -> str:
    e = html.escape
    out = [
        "<!doctype html><html lang=en><head><meta charset=utf-8>",
        "<meta name=viewport content='width=device-width,initial-scale=1'>",
        f"<title>{e(state['server'])} — server dashboard</title>",
        f"<style>{PAGE_CSS}</style></head><body>",
        "<header>",
        render_site_header(state["self"]),
        f"<div class=sub>{e(state['server'])} — hardware, stack, hosted apps "
        f"and deploy history. "
        f"Generated {e(_fmt_ts(state['generated_at'], tz=True))}.</div>",
        "</header><main>",
        render_server_panel(state["info"], state["self"]),
        render_apps(state["apps"]),
        APPS_SCRIPT,
    ]
    if state.get("chat_enabled"):
        out.append(render_chat_panel())
    out.append("</main>")
    out.append(
        "<footer>srvhome &middot; canonical source: BdRDev/fleet/srvhome "
        "&middot; GitHub checked every ~15&nbsp;min; tiles refresh every ~15s; "
        "history written by each repo's git post-merge hook</footer></body></html>")
    return "".join(out)


# --------------------------------------------------------------------------
# server
# --------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "srvhome/1.1"

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _route(self) -> str:
        path = self.path.split("?", 1)[0].rstrip("/")
        if path.startswith("/status"):
            path = path[len("/status"):]
        return path

    def do_GET(self) -> None:  # noqa: N802
        path = self._route()
        if path in ("", "/"):
            self._send(200, render_html(full_state()).encode(),
                       "text/html; charset=utf-8")
        elif path in ("/api/state", "/api"):
            self._send(200, json.dumps(full_state(), indent=2).encode(),
                       "application/json")
        elif path in ("/healthz", "/health"):
            self._send(200, b"ok\n", "text/plain")
        elif path == "/logo.png":
            try:
                with open(LOGO_PATH, "rb") as fh:
                    self._send(200, fh.read(), "image/png")
            except OSError:
                self._send(404, b"not found\n", "text/plain")
        else:
            self._send(404, b"not found\n", "text/plain")

    do_HEAD = do_GET

    def _read_json_body(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length > 32768:
            self._send(413, b'{"error":"payload too large"}', "application/json")
            return None
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            self._send(400, b'{"error":"invalid json"}', "application/json")
            return None

    def do_POST(self) -> None:  # noqa: N802
        path = self._route()
        if path in ("/api/check", "/api/update"):
            body = self._read_json_body()
            if body is None:
                return
            if path == "/api/check":
                app = body.get("app")
                if app:
                    apps = {a["name"]: a for a in checkables()}
                    if app not in apps:
                        self._send(404, b'{"error":"unknown app"}', "application/json")
                        return
                    check_one(apps[app])
                else:
                    check_all()
                self._send(200, json.dumps(full_state(), indent=2).encode(),
                           "application/json")
                return
            # /api/update
            app = (body.get("app") or "").strip()
            if not app:
                self._send(400, b'{"error":"app required"}', "application/json")
                return
            result = run_update(app)
            code = 429 if result.get("_busy") else (
                400 if result.get("error") and not result.get("output_tail") else 200)
            result.pop("_busy", None)
            self._send(code, json.dumps(result).encode(), "application/json")
            return
        if path != "/api/chat":
            self._send(404, b"not found\n", "text/plain")
            return
        body = self._read_json_body()
        if body is None:
            return

        message = (body.get("message") or "").strip()
        reset = bool(body.get("reset"))
        if not message:
            # a bare reset ping is fine
            if reset:
                try:
                    os.remove(CHAT_SESSION_FILE)
                except OSError:
                    pass
                self._send(200, b'{"ok":true}', "application/json")
            else:
                self._send(400, b'{"error":"empty message"}',
                           "application/json")
            return

        result = run_claude(message, reset)
        code = 429 if result.get("_busy") else (
            400 if result.get("error") and not result.get("reply") else 200)
        result.pop("_busy", None)
        self._send(code, json.dumps(result).encode(), "application/json")

    def log_message(self, fmt: str, *args) -> None:  # quieter logs
        pass


def main() -> None:
    conf = load_conf()
    host = conf.get("bind_host", "127.0.0.1")
    port = int(conf.get("bind_port", 8610))
    connect(DB_PATH).close()
    running_sha()  # freeze the running-code SHA at process start
    start_checker()
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"srvhome listening on http://{host}:{port}  (db: {DB_PATH})",
          flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
