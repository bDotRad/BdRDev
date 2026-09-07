"""
Read / write the fleet-ecosystem data from a self-hosted Supabase
(Postgres) over the PostgREST REST API, with state/ecosystem.json as a
fallback cache.

Why REST and not the `supabase` / `psycopg2` client: neither is installed
on this box and we can't add binary deps. `requests` is available, and
Supabase exposes everything we need at ${SUPABASE_URL}/rest/v1/.

Environment variables (systemd sets these; all unset = feature off, the
dashboard just uses common.load_ecosystem()/save_ecosystem()):

  SUPABASE_URL          e.g. https://bdrpiami.local  (no trailing /rest/v1)
  SUPABASE_SERVICE_KEY  the service-role JWT   (SUPABASE_KEY also accepted)
  SUPABASE_VERIFY_SSL   "0"/"false"/"no"/"off" -> don't verify TLS (the Pi
                        serves bdrpiami.local with a self-signed cert);
                        anything else -> verify normally
  SUPABASE_CA_BUNDLE    path to a CA bundle to verify against instead of
                        the system trust store

Read path:
  GET /rest/v1/fleet_ecosystem_json?select=ecosystem
  -> [{"ecosystem": {...}}], already shaped like common.load_ecosystem();
  the `ecosystem` object is fed straight through
  common._normalize_ecosystem(). On success the result is also written
  back to state/ecosystem.json as a warm cache.

Write path (push_ecosystem): upsert the base tables with the service key --
  servers (incl. nickname), server_software (the 4 tracked package links
  per server), projects (incl. nickname + the folded-in deployment columns
  runs_on_server_id / local_url / ts_url / database / status), project_roles
  (the role matrix), fleet_meta -- and delete rows that are no longer in the
  payload. On success state/ecosystem.json is updated too.

  Requires the schema from supabase/DRAFT_fold_apps_into_projects.sql
  Parts A + B (the projects deployment columns, the roles / project_roles
  tables, and the new fleet_ecosystem_json view). Part C then drops the
  now-unused apps / project_agents tables.

Everything here is defensive: not configured, or any HTTP/parse error,
means fetch_ecosystem() returns None and push_ecosystem() returns False so
the caller falls back to the JSON file. The dashboard must keep working
with the Pi down, so timeouts are short.
"""

import os

import requests

import common

# (connect, read) seconds -- a dead Pi must never hang the dashboard.
REST_TIMEOUT = (5, 5)

# Fleet-editor per-package booleans -> software.name in the catalogue.
# These are the only server_software links push_ecosystem() manages; other
# links (Scheduler, Firebase, ...) seeded in SQL are left untouched.
_SOFTWARE_FLAGS = [
    ("claude", "Claude Code"),
    ("nginx", "Nginx"),
    ("supabase", "Supabase"),
    ("sqlite", "SQLite"),
]


def _env(*names):
    for n in names:
        v = os.environ.get(n)
        if v and v.strip():
            return v.strip()
    return ""


def _base_url():
    return _env("SUPABASE_URL").rstrip("/")


def _service_key():
    return _env("SUPABASE_SERVICE_KEY", "SUPABASE_KEY")


def is_configured():
    """True when both SUPABASE_URL and a service key are set."""
    return bool(_base_url() and _service_key())


def _verify():
    flag = os.environ.get("SUPABASE_VERIFY_SSL", "").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return False
    bundle = _env("SUPABASE_CA_BUNDLE")
    return bundle or True


def _headers(write=False):
    key = _service_key()
    h = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }
    if write:
        h["Content-Type"] = "application/json"
    return h


def _rest(method, path, *, params=None, json_body=None, prefer=None):
    """One PostgREST call. Raises requests.RequestException on transport
    error or a non-2xx status; returns parsed JSON or None (204 / empty)."""
    headers = _headers(write=json_body is not None)
    if prefer:
        headers["Prefer"] = prefer
    verify = _verify()
    if verify is False:
        # self-signed cert on the Pi -- silence the per-call warning spam
        requests.packages.urllib3.disable_warnings(  # type: ignore[attr-defined]
            requests.packages.urllib3.exceptions.InsecureRequestWarning  # type: ignore[attr-defined]
        )
    resp = requests.request(
        method,
        f"{_base_url()}/rest/v1/{path}",
        headers=headers,
        params=params,
        json=json_body,
        timeout=REST_TIMEOUT,
        verify=verify,
    )
    resp.raise_for_status()
    if resp.status_code == 204 or not resp.content:
        return None
    return resp.json()


def _in_list(values):
    """PostgREST `in.(...)` literal with every value double-quoted."""
    parts = []
    for v in values:
        s = str(v).replace("\\", "\\\\").replace('"', '\\"')
        parts.append(f'"{s}"')
    return "(" + ",".join(parts) + ")"


def _delete_missing(table, col, keep):
    """Delete rows of `table` whose `col` is not in `keep`. Empty `keep`
    clears the table (every row has id >= 0)."""
    if keep:
        _rest("DELETE", table, params={col: f"not.in.{_in_list(keep)}"})
    else:
        _rest("DELETE", table, params={"id": "gte.0"})


# ---- read -------------------------------------------------------------------

def fetch_ecosystem():
    """Fleet dict from Supabase (normalized to common's shape), or None on
    any failure / when not configured. On success also refreshes the
    state/ecosystem.json warm cache."""
    if not is_configured():
        return None
    try:
        rows = _rest("GET", "fleet_ecosystem_json", params={"select": "ecosystem"})
        if not rows:
            return None
        eco = common._normalize_ecosystem(rows[0].get("ecosystem"))
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
        return None
    try:
        common.save_ecosystem(eco)
    except OSError:
        pass
    return eco


# ---- write ----------------------------------------------------------------

def push_ecosystem(eco):
    """Write the whole fleet object to the Supabase base tables. Returns
    True on full success (and mirrors it to state/ecosystem.json), False if
    not configured or any call fails -- the caller then just keeps the JSON
    file as the source of truth."""
    if not is_configured():
        return False
    data = common._normalize_ecosystem(eco)
    try:
        _write_all(data)
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return False
    try:
        common.save_ecosystem(data)
    except OSError:
        pass
    return True


def _write_all(data):
    servers = data["servers"]
    projects = data["projects"]

    # -- software catalogue: ensure the 4 tracked names exist, collect ids
    existing = _rest("GET", "software", params={"select": "id,name"}) or []
    sw_id = {r["name"]: r["id"] for r in existing}
    missing = [name for _flag, name in _SOFTWARE_FLAGS if name not in sw_id]
    if missing:
        created = _rest(
            "POST", "software",
            json_body=[{"name": n} for n in missing],
            prefer="return=representation,resolution=merge-duplicates",
        ) or []
        for r in created:
            sw_id[r["name"]] = r["id"]
    tracked_ids = [sw_id[name] for _f, name in _SOFTWARE_FLAGS if name in sw_id]

    # -- servers (upsert on name, sort_order from list position)
    server_rows = [{
        "name": s["name"],
        "nickname": s.get("nickname", ""),
        "tag": s["tag"],
        "address": s["address"],
        "tailscale_ip": s.get("tailscale", ""),
        "local_url": s.get("local_url", ""),
        "ts_url": s.get("ts_url", ""),
        "host": s["host"],
        "os": s["os"],
        "ram": s["ram"],
        "disk": s["disk"],
        "git_notes": s["git"],
        "provisioned": s["provisioned"],
        "dev_host": s["dev_host"],
        "sort_order": i + 1,
    } for i, s in enumerate(servers)]
    saved_servers = []
    if server_rows:
        saved_servers = _rest(
            "POST", "servers",
            params={"on_conflict": "name"},
            json_body=server_rows,
            prefer="return=representation,resolution=merge-duplicates",
        ) or []
    srv_id = {r["name"]: r["id"] for r in saved_servers}
    _delete_missing("servers", "name", [s["name"] for s in servers if s["name"]])

    # -- server_software: replace only the 4 tracked links, per server
    for s in servers:
        sid = srv_id.get(s["name"])
        if sid is None:
            continue
        if tracked_ids:
            _rest("DELETE", "server_software", params={
                "server_id": f"eq.{sid}",
                "software_id": f"in.{_in_list(tracked_ids)}",
            })
        links = [
            {"server_id": sid, "software_id": sw_id[name]}
            for flag, name in _SOFTWARE_FLAGS
            if s.get(flag) and name in sw_id
        ]
        if links:
            _rest("POST", "server_software", json_body=links,
                  prefer="resolution=merge-duplicates")

    # -- roles catalogue: role key -> id (seeded by the migration; we only read)
    role_rows = _rest("GET", "roles", params={"select": "id,name"}) or []
    role_id = {r["name"]: r["id"] for r in role_rows}

    # -- projects (+ folded-in deployment columns)
    proj_rows = []
    for i, p in enumerate(projects):
        proj_rows.append({
            "name": p["name"],
            "nickname": p.get("nickname", ""),
            "exists_flag": p["exists"],
            "runs_on_server_id": srv_id.get(p.get("runs_on") or ""),
            "local_url": p.get("local_url", ""),
            "ts_url": p.get("ts_url", ""),
            "database": p.get("database", ""),
            "status": p.get("status") or "planned",
            "sort_order": i + 1,
        })
    saved_projects = []
    if proj_rows:
        saved_projects = _rest(
            "POST", "projects",
            params={"on_conflict": "name"},
            json_body=proj_rows,
            prefer="return=representation,resolution=merge-duplicates",
        ) or []
    proj_id = {r["name"]: r["id"] for r in saved_projects}
    _delete_missing("projects", "name", [p["name"] for p in projects if p["name"]])

    # -- project_roles: replace every link per project from the payload's roles[]
    for p in projects:
        pid = proj_id.get(p["name"])
        if pid is None:
            continue
        _rest("DELETE", "project_roles", params={"project_id": f"eq.{pid}"})
        links = [
            {"project_id": pid, "role_id": role_id[r]}
            for r in dict.fromkeys(p.get("roles") or [])
            if r in role_id
        ]
        if links:
            _rest("POST", "project_roles", json_body=links,
                  prefer="resolution=merge-duplicates")

    # -- fleet_meta (single row, id forced to 1)
    _rest("POST", "fleet_meta",
          params={"on_conflict": "id"},
          json_body={"id": 1, "notes": data["notes"]},
          prefer="resolution=merge-duplicates")
