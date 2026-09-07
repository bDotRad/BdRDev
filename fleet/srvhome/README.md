# srvhome — per-server "running apps" home page

A tiny status page that runs **on a fleet server** and shows, for every
app that server hosts:

- the **version deployed here right now** — the 7-char commit SHA, plus
  its commit title and branch;
- a **running badge** — deliberately neutral ("status not tracked") for
  now; live status was deferred in the request. Wire it up later in
  `app_state()` in `srvhome.py`;
- a **history of updates** — every version this box has pulled, with the
  deploy timestamp, commit title and description.

The page is **colour-coded** per the fleet WebUI standard: each tile has
a status-coloured left border (green = running, red = down, amber = not
tracked, grey = repo absent), the history row matching the SHA currently
checked out is highlighted green and tagged "live here", backfilled rows
are muted, and the footer carries a legend.

First deployment target: **BdRPiSrvAMI** (the Pi, `10.10.10.20` /
tailnet `bdrpisrvami`). Canonical source lives in `BdRDev/fleet/srvhome/`.
The Pi runs it from a **read-only `bDotRad/BdRDev` checkout** at
`~/projects/BdRPiAMI/BdRDev/`, launched from `fleet/srvhome/` within it —
so srvhome can `git pull` / version-check itself like any app (see
"srvhome tracks itself too" below). The earlier loose file-copy deploy
(`~/projects/BdRPiAMI/srvhome/`, redeployed by hand-copying `srvhome.py`)
is retired — see `DEPLOY-STATUS.md` for the one-time switch-over.

Served at **`/`** on that box (nginx → `127.0.0.1:8610`, see
`nginx-snippet.conf`) — the same role the BdRDev dashboard plays at `/`
on the dev box. It used to live under `/status/` as a sub-path purely to
avoid touching the Supabase-owned root on first deploy; that's gone as
of `rAMI web layout` (Supabase moved to its own port). The handler still
accepts an optional `/status` prefix for compatibility, but nothing
should route it there anymore.

## How history is collected

`git pull` runs the repo's `.git/hooks/post-merge` hook. `install.sh`
drops [`hooks/post-merge`](hooks/post-merge) into each app repo; on every
pull it calls `record_deploy.py`, which writes the new HEAD
(7-char SHA / title / body / commit date / **pull time**) into
`srvhome.db` (SQLite). Re-recording the same SHA is a no-op, so the
per-minute keepalive and manual re-runs never create duplicates.

`install.sh` also **back-fills** the last 30 commits per repo so the
history table isn't empty on day one (those rows are tagged
"backfilled" and dated by commit time, not pull time).

The page itself reads `git` live for the current HEAD and reads
`srvhome.db` for history — no daemon-side polling.

## Version checking & one-click update

A background thread runs `git fetch` for every app every ~15 min
(`CHECK_INTERVAL_S`) and holds `{behind, remote_sha, last_checked,
error}` in memory (in-memory by design — a restart just re-checks within
seconds).

Each tile has an always-visible **status box** (`render_statusbox`): a
status line ("up to date" / "N new commits on GitHub — Pull to deploy" /
"serving `<sha>` — rebuild needed" / "updating…" / "last update failed"),
a mono meta sub-line (`GitHub checked 4m ago · HEAD abc1234 · GitHub
def5678 · built abc1234`), and — once an update has run — the captured
`update.sh` output inline. The box's dot and the tile's left border are
colour-coded (green / amber / blue / red).

- **Check GitHub** (per tile, plus "check GitHub — all apps" in the
  section header) → `POST /api/check {app?}` forces a fetch now.
- **Pull** (`Pull (N)` when behind, `Rebuild` when only `dist/` is
  stale; hidden otherwise) → `POST /api/update {app}` takes a per-app
  lock and shells out to `~/projects/update.sh <app>` — the existing
  pull + apply-new-migrations + rebuild script, reused not
  reimplemented. **When GitHub is ahead the Pull button flashes**
  (`.flash`, a blue pulse; disabled under `prefers-reduced-motion`).
  Combined output streams into the status box.
- `rebuild_needed` compares `git HEAD` to `app/dist/build-info.json`'s
  `sha` (each app's `vite.config.ts` writes that at build time), so a
  stale bundle after a no-op pull is visible.
- Tiles poll `/api/state` every 15 s so the checker and a running update
  both surface without a manual reload.

### srvhome tracks itself too

When srvhome runs from a git checkout (the intended deploy: a read-only
`bDotRad/BdRDev` clone, run from `fleet/srvhome/` within it), it treats
**its own version** as one more thing to check — keyed `"srvhome"`:

- the fleet **standard header block** at the top of the page
  (`render_site_header`, see `_Instructions/WebUI.md`) — logo + the
  app-name line (`srvhome.conf.json`'s `display_name`, uppercased —
  `"bdr AMI"` → **BDR AMI** on the AMI Pi; falls back to `SRVHOME` when
  unset) + version line (`YYYY.MM.DD_HHMM · <sha>`) + a deploy-status line whose
  `up to date` / `behind by N` pill re-checks GitHub, with `HEAD` +
  `running` SHA chips (the logo is served from the checkout's own
  `app/static/rat-logo.png` via the `/logo.png` route);
- a `srvhome` sub-tile in the **Updates** card (`render_self_updates`) —
  the same status box + **Check GitHub** / **Pull (N)** + deploy history
  an app tile gets. `state["self"]` in `/api/state`, `self_state()`.
- **Pull** here is `git pull --ff-only` then a self re-exec (`_self_pull`
  / `_schedule_self_restart`) — no build step. The browser waits ~6 s
  then reloads.
- history is path-filtered to commits touching `fleet/srvhome/`
  (`record_deploy.py --path`, plus `SRVHOME_APP_PATH` in the self repo's
  `post-merge` hook), so it isn't every unrelated BdRDev commit.

When srvhome is just a loose copy of the files, all of this degrades to
"loose file copy on this box, version not tracked".

History rows carry `committed_at` (the commit's own author/committer
date) alongside the pull time; the table renders `committed | pulled |
commit`.

## Files

| file | what |
|---|---|
| `srvhome.py` | the HTTP server (stdlib only, binds `127.0.0.1:8610`) |
| `store.py` | SQLite schema + helpers for `deploys` |
| `record_deploy.py` | records a repo's HEAD into the DB (hook + `--backfill`) |
| `apps.json` | which apps this server hosts (`name` + repo `path`) |
| `srvhome.conf.json` | `server`, header `display_name`, bind host/port, history limit |
| `hooks/post-merge` | the git hook `install.sh` copies into each app repo |
| `install.sh` | back-fill + install hooks + crontab keepalive (no sudo) |
| `run.sh` | idempotent starter used by the crontab |
| `srvhome.service` | optional systemd unit (needs sudo) |
| `nginx-snippet.conf` | the `/status/` route to add to nginx (needs sudo) |

## Deploy (on the Pi)

srvhome runs from a full `bDotRad/BdRDev` checkout so it can
version-check itself:

```bash
cd ~/projects/BdRPiAMI
git clone https://github.com/bDotRad/BdRDev.git BdRDev   # HTTPS via the box's gh PAT
cp <old-copy>/srvhome.db BdRDev/fleet/srvhome/ 2>/dev/null || true   # keep deploy history
cd BdRDev/fleet/srvhome
./install.sh
curl -s http://127.0.0.1:8610/api/state | head
```

nginx (sudo, Brad) proxies `/` → `127.0.0.1:8610` — the page is at
**https://bdrpisrvami.local/**. Deploy updates from here on: `git pull`
in `~/projects/BdRPiAMI/BdRDev` (or the dashboard **Pull** button).

## Adding another server later

Copy the dir to that box, edit `apps.json` + `srvhome.conf.json`, run
`install.sh`, add the nginx route. Nothing here is Pi-specific except
those two config files.
