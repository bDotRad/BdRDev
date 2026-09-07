# BdRDev

Web dashboard + round-robin scheduler for the Claude Code projects under
`~/projects` on this Pi. Built from the example dropped in
`_Requests/rf GUI Files/` (see `_Requests/_Archive/` for the processed
request writeup).

Two independent processes, talking to each other only through JSON files
in `state/`:

- **`app/dashboard.py`** — the web UI (Flask). Shows every project, which
  one is currently active, what phase it's in, a rolling activity log,
  and lets you tick projects in/out of the rotation. Also surfaces any
  pending SQL a project has left for you to run by hand (see below).
  Never touches tmux or Claude directly — purely reads state and writes
  your rotation selection.
- **`app/scheduler.py`** — the always-on daemon that does the actual
  work: round-robins through whichever projects are ticked, checks each
  one's `_Requests/` folder for READY items, wakes/runs Claude Code in a
  tmux session when there's something to do, and hibernates (kills the
  tmux session) once a project's gone quiet. Appends events to
  `state/activity_log.jsonl` as it does so.

`app/common.py` holds the logic both processes share (project listing,
request scanning, state file I/O) so they can't drift out of sync on
what counts as "pending".

## Conventions this implements

- **Request intake**: `_Requests/<item>` per project, gated by a
  first-line `READY`/`NOT READY` marker, `x`-prefix to ignore, `_`-prefix
  reserved for archive/meta folders (`_Archive`, `_Archived`, ...). See
  `_Instructions/Requests.md` for the full spec. `common.scan_requests()`
  is the implementation — it's what both the dashboard's pending badge
  and the scheduler's wake trigger read from, so they always agree.
- **Orchestration context**: `_Instructions/BdRDev.md` is the doc meant
  to be copied into *other* projects' instructions so their Claude Code
  sessions understand they're running under this scheduler (why they get
  woken/killed, `.claude-status/status.json`, SQL output convention).
- **App server sync**: `_Instructions/AppServerSync.md` -- for projects
  that also run live on a separate app server, the convention for
  funneling any app-server-side edit back through this dev server
  (drop the changed file in `_AppServerDrops/`, fold it in and push from
  here, then pull it back down on the app server) instead of pushing
  straight from the app server.
- **Status line** (optional, per project): a project can write
  `.claude-status/status.json` with `{"current_task": "...",
  "last_active": "<ISO8601>"}` to show a human-readable task line on its
  card.
- **SQL output** (optional, per project): if a Claude session working on
  a project needs a human to run some SQL by hand (e.g. in the Supabase
  SQL editor), it can write the statement(s) to
  `.claude-status/sql_output.txt` (or `.sql`). The project's card then
  shows a purple **SQL** badge; clicking it opens a read-only textarea
  with a Copy button and a Clear button (deletes the file once you've
  run it).
- **Creating a request from the UI**: each card has a **+ Request**
  button — type the request, optionally attach files, and submit. With
  no attachments it writes `_Requests/rN.md`; with attachments it makes
  `_Requests/rN/` containing `request.md` plus the files. Numbering
  auto-increments per project. Meant as the first step toward dropping
  requests in remotely (e.g. over Tailscale) without opening a terminal.
- **Ecosystem / fleet data**: the Ecosystem tab renders from the fleet
  data, not hand-written HTML, with two editable (Edit / Save / Cancel)
  grids — **Servers** (address, Tailscale IP, `local_url` LAN/mDNS
  address, `ts_url` Tailscale front-door URL, host/OS/RAM/disk, the
  Claude/Nginx/Supabase/SQLite Y/N flags, git notes) and **Projects**
  (dev-agent role matrix, runs-on server, `local_url` + `ts_url`,
  database, status) —
  plus a free-text notes block. Each grid also has CSV export / import.
  Dashboard-only — the scheduler never reads it.
  - **Source of truth**: this box's own self-hosted Supabase (Postgres)
    at `http://127.0.0.1:8000` (`bdrpisrvdev` is the fleet/ecosystem
    master) — schema in `supabase/migrations/`, read back through the
    `public.fleet_ecosystem_json` view, written via PostgREST with the
    service key. `app/fleet_db.py` is the client (plain `requests`, no
    `supabase`/`psycopg2`). Configured by env vars on the dashboard
    service: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (or `SUPABASE_KEY`),
    optional `SUPABASE_VERIFY_SSL=0` / `SUPABASE_CA_BUNDLE` for the Pi's
    self-signed cert (see `systemd/bdrdev-dashboard.service`).
  - **Fallback**: `state/ecosystem.json` is a warm cache. When the
    Supabase env vars are unset or the Pi is unreachable, the dashboard
    reads/writes that file instead and never errors. Every successful DB
    read/write also rewrites the JSON file. `common.load_ecosystem()`
    seeds it from `common.DEFAULT_ECOSYSTEM` on first use; `state/` is
    gitignored, so the checked-in seed lives in `common.py`. The
    `/api/ecosystem` GET response carries `"source": "supabase" |
    "json-fallback"` plus `"supabase_configured"`, and the Fleet /
    Ecosystem 2 tabs show which one served the data (and, on a fallback,
    whether it's because Supabase isn't configured on this box or is
    configured but unreachable).
  - On the **Fleet** tab, an app's "Runs on server" is a dropdown of the
    defined servers (not free text), so the Ecosystem 2 "Apps" column —
    derived by matching `app.server` to a server name — stays in sync.
- **Processing tab**: a live view of where request processing is right
  now, backed by `/api/proc-status`. One card per project session
  (`proj-<name>` tmux) showing whether the session is alive, what the
  pane is doing — `working` (Claude Code's "esc to interrupt" indicator
  is up, or the pane produced output between two captures 1.5s apart),
  `waiting_input` (parked on a permission / plan prompt), or `idle` — how
  many requests are still READY, and the last ~40 transcript lines. A
  project with READY work and a live session that isn't `working` is
  flagged **stuck** (red), which usually means a session hit an
  interactive prompt without setting its request to `WAITING RESPONSE`.
  Also shows the last 30 scheduler activity-log events.

## Setup

```bash
cd ~/projects/BdRDev
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Try it manually first, in two terminals:

```bash
# terminal 1
source venv/bin/activate && python3 app/dashboard.py
# terminal 2
source venv/bin/activate && python3 app/scheduler.py
```

Open `http://<pi-ip>:8420`, tick a project into the rotation, and drop a
`READY`-marked item in its `_Requests/` folder to watch the scheduler
pick it up.

### Run both permanently

Service files in `systemd/` are already pointed at `/home/bdr/...` and
user `bdr`, matching this machine. Install once the venv above exists:

```bash
sudo cp systemd/bdrdev-dashboard.service systemd/bdrdev-scheduler.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bdrdev-dashboard bdrdev-scheduler
```

Check they're both up:

```bash
systemctl status bdrdev-dashboard bdrdev-scheduler
```

### HTTPS / trusted certs

`nginx/bdrdev.conf` reverse-proxies `:8420` behind HTTPS with two
front doors, split by SNI:

- `https://bdrpisrvdev.tail0ed3f6.ts.net` — a real Let's Encrypt cert
  from `tailscale cert`, trusted on every device with no setup
  (tailnet-only).
- `https://bdrpisrvdev.local` / `https://bdrdev.local` / LAN IP — a leaf
  signed by a local root CA; install `tls/ca/bdr-fleet-ca.crt` once per
  device and the warning is gone on the LAN and offline.

Full setup, per-device trust steps and the 90-day Tailscale-cert renewal
cron are in [tls/README.md](tls/README.md).

## Notes

- State lives in `./state/` (gitignored) — `selected_projects.json`
  (dashboard writes, scheduler reads), `scheduler_state.json` (scheduler
  writes, dashboard reads), `activity_log.jsonl` (scheduler appends,
  dashboard reads, capped to the last ~500 lines).
- Port `8420` is arbitrary — change it at the bottom of `dashboard.py` if
  it clashes with something else.
- `EMPTY_GRACE_SECONDS` (30s) and `POLL_WHILE_PROCESSING` (5s) in
  `scheduler.py` are the two timing knobs if you want it snappier or more
  relaxed.
- `CLAUDE_LAUNCH_CMD` defaults to whatever `claude` resolves to on
  `PATH` at import time (falls back to the bare string `"claude"`).
  Systemd's `PATH` is minimal and won't see `~/.local/bin`, so the
  scheduler service file pins it explicitly:
  `Environment=CLAUDE_LAUNCH_CMD=/home/bdr/.local/bin/claude`. Update
  that line if `which claude` ever resolves somewhere else.
- With just one project ticked, the scheduler still applies the same
  logic to it — it'll hibernate that session after two empty checks and
  simply loop back to itself, so it only ever restarts when there's
  actually new work.
