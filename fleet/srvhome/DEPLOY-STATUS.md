# srvhome on BdRPiSrvAMI — deploy status (updated 2026-09-06)

Built for request `rEach server running apps`. First target: the Pi.

## srvhome self-version panel — 2026-09-06 — NEEDS RE-DEPLOY AS A CHECKOUT

srvhome now tracks **its own version** the same way it tracks a hosted
app: the fleet **standard header block** (`_Instructions/WebUI.md`) at
the top of the page, full three-line form — logo + `SRVHOME` + a
version line (`2026.09.07_1358 · abc1234`) + a deploy-status line whose
`up to date` / `behind by N` pill *is* the "re-check GitHub" button,
with `HEAD` and `running` SHA chips (srvhome has no build step, so the
second chip is the SHA the live process started from — it goes amber if
someone pulls without restarting). Also, in the **Updates** card, a
`srvhome` sub-tile with a status box, **Check GitHub** / **Pull (N)**
buttons and its own deploy history. `Pull` does `git pull --ff-only`
then re-execs the process (no build step). Keyed `"srvhome"` in
`srvhome.db`; the background checker and the "check all" button now
include it. Code: `self_state()`, `self_app()`, `render_site_header()`,
`render_self_updates()`, `_self_pull()`, `_schedule_self_restart()`,
`running_sha()`, the `/logo.png` route in
`srvhome.py`; `--path` filter in `record_deploy.py`; `SRVHOME_APP_NAME`
/ `SRVHOME_APP_PATH` in `hooks/post-merge`; self-hook block in
`install.sh`.

**This only lights up when srvhome runs from a git checkout.** The
current Pi deploy is a loose file copy in `~/projects/BdRPiAMI/srvhome/`,
so until it's re-deployed the panel shows "loose file copy on this box,
version not tracked". Re-deploy as a **read-only BdRDev checkout**, run
from `fleet/srvhome/` inside it:

```sh
# on BdRPiSrvAMI (needs a read-only deploy key for bDotRad/BdRDev — see SSH.md)
cd ~/projects/BdRPiAMI
git clone <bdrdev-ro-remote> BdRDev
# carry over the gitignored runtime state from the old copy
cp srvhome/srvhome.db srvhome/srvhome.conf.json BdRDev/fleet/srvhome/ 2>/dev/null || true
cd BdRDev/fleet/srvhome
./install.sh                       # rewrites the crontab keepalive to this path,
                                   # installs the self-hook, backfills "srvhome"
pkill -f 'srvhome/srvhome.py'      # per-minute run.sh restarts from the new path
# once healthy on :8610, retire the old dir:
rm -rf ~/projects/BdRPiAMI/srvhome
```

nginx is unchanged (still proxies `127.0.0.1:8610`). `~/projects/update.sh`
is unchanged. After this, `git pull` in `~/projects/BdRPiAMI/BdRDev`
(or the dashboard's own **Pull** button) is the deploy path — the
manual `cp srvhome.py` dance below is retired.

## srvhome moves to `/`, Supabase gets its own port — 2026-09-05 — WAITING ON BRAD

Request `rAMI web layout` (`_Requests/`) supersedes the "`/status/` is
401" item below rather than fixing it in place: root cause was Supabase
owning `location /` in the same `listen 443` block that serves
`/status/`, so any `auth_basic`/proxy hiccup on the Supabase side took
srvhome down with it. Fix moves Supabase off `/` entirely (its own
Tailscale-served `:8000`) and gives srvhome `/` outright — see
`nginx-snippet.conf` (rewritten) and the request's Action block for the
exact commands. **Nothing left to code here** — `srvhome.py` already
tolerates being served at `/` (see its docstring), `apps.json` URLs
fixed to point at each app's real route. Blocked on Brad running the
`tailscale serve` + nginx swap + redeploy steps.

## Flashing Pull button + per-tile status box — 2026-09-04 — NEEDS REDEPLOY

Direct request from Brad (no request file): a "Main Summary page" ask
that turned out to already be this page. UI-only changes to `srvhome.py`
— no API / schema / `update.sh` change:

- The update button is now **Pull (N)** (was "Update (N)") / **Rebuild**,
  and **flashes** (blue pulse, `.flash`) whenever GitHub is ahead.
  `prefers-reduced-motion` swaps the pulse for a static outline.
- The small status pill is replaced by an **always-visible status box**
  per tile — status line + mono meta sub-line (`GitHub checked … · HEAD …
  · GitHub <remote sha> · built …`) + inline `update.sh` output (no more
  `<details>` to expand). `render_statusbox` / `_status_meta`.
- "Check" → "Check GitHub"; header "check all now" → "check GitHub — all
  apps". Footer / comments corrected 5 min → 15 min.

**Redeploy:** copy `srvhome.py` to `~/projects/BdRPiAMI/srvhome/` on the
Pi and kill the running process (the per-minute cron `run.sh` restarts
it). `store.py`, `record_deploy.py`, `apps.json`, `update.sh`, hooks all
unchanged.

## Version check + one-click update (request `rSrvhome version check + update`) — DONE / deployed 2026-08-30

- `srvhome.py`, `record_deploy.py`, `store.py`, `hooks/post-merge` and
  `~/projects/update.sh` on the Pi are byte-identical to canonical
  (`BdRDev/fleet/srvhome/`) as of commit `6f3e041`. The stale
  `srvhome/hooks/post-merge` template on the Pi was re-synced 2026-08-30
  (it lagged the `--range ORIG_HEAD..HEAD` change; the *installed* hooks
  in PlanBdRad / BdRAMAssist `.git/hooks/` were already current).
- Verified live on `127.0.0.1:8610`: background checker running
  (15-min loop, `last_checked` fresh), both apps report `behind: 0`,
  `built_sha == head_sha`, `rebuild_needed: false`; history table
  renders `committed | pulled | commit` with `committed_at` populated.
- **`POST /api/check`** (per tile + "check all"), **`POST /api/update`**
  (shells `~/projects/update.sh <app>` under a per-app lock, output
  captured to a `<details>`), tiles poll `/api/state` every 15 s.

### Open — needs Brad (nginx) — SUPERSEDED, see the 2026-09-05 entry above

Don't fix this in place; `rAMI web layout` replaces the `/status/`
sub-path with srvhome owning `/` outright, which removes the shared
`listen 443` block that caused it.

`https://<pi>/status/` is **401 again** (localhost, `bdrpiami`, all
paths) — the `/status/` route in the Pi's nginx site config has
regressed since it was verified working 2026-08-28, so requests fall
through to Supabase auth. srvhome itself is healthy on `:8610`; only the
web route is broken. Re-add / restore the `nginx-snippet.conf` block in
the `listen 443` server block and `sudo nginx -s reload`. Can't be
diagnosed from the dev box (no sudo, can't read `/etc/nginx/`).

## Done

- Code deployed to `~/projects/BdRPiAMI/srvhome/` on the Pi.
- Deploy DB `srvhome.db` back-filled from `git log`:
  PlanBdRad (23 commits), BdRAMAssist (17 commits).
- `post-merge` hook installed in `~/projects/PlanBdRad/.git/hooks/` and
  `~/projects/BdRAMAssist/.git/hooks/` — every future `git pull` on the
  Pi records the pulled version into `srvhome.db`.
- **`install.sh` run by Brad** — user-crontab keepalive active
  (`@reboot` + per-minute `run.sh`); server running on `127.0.0.1:8610`,
  `/healthz` → `ok`.
- **Colour-coding added** (request follow-up) and redeployed to the Pi:
  tiles carry a status-coloured left border (green running / red down /
  amber not-tracked / grey absent), the history row whose SHA matches
  the currently-deployed checkout is highlighted green with a "live
  here" tag, backfilled rows are muted, and the footer has a colour
  legend. Old process killed so the per-minute cron picked up the new
  code; verified rendering on the Pi.

## Nginx route — DONE (Brad, 2026-08-28)

The `nginx-snippet.conf` block is in the `listen 443` server block of
the Pi's site config. Verified live from the dev box:

```
https://10.10.10.20/status/    → 200   (page renders, full history)
https://bdrpiami/status/       → 200
https://100.86.25.88/status/   → 200   (Tailscale)
```

Supabase stays on `/`, untouched.

### Hostname note — rename DONE (confirmed 2026-09-06)

The Pi's on-box hostname **is** now `BdRPiSrvAMI` (`hostname`,
`hostname -f`, `/etc/hostname` all agree) and its Tailscale node is
`bdrpisrvami` / `bdrpisrvami.tail0ed3f6.ts.net`. So its mDNS name is now
`bdrpisrvami.local`, **not** `bdrpiami.local`. Still stale: the nginx
site *file* is named `bdrpiami` and its `server_name` lines likely still
list `bdrpiami.local` (see `rAMI web layout` — the nginx swap is
Brad's). Working URLs today: `https://bdrpisrvami.local/status/` (mDNS
machines), `https://10.10.10.20/status/` (LAN), or the tailnet name.
`bdrpiami.local` may still resolve from machines with a stale
`/etc/hosts` or nginx `server_name` entry, but don't rely on it.

If you'd rather use systemd than the crontab keepalive:
`sudo cp srvhome.service /etc/systemd/system/ && sudo systemctl enable
--now srvhome`, then delete the two `srvhome/run.sh` lines from
`crontab -e`.

## Design decisions made (flagged for review — see request answers)

- **Lives on the Pi** (answer #1) at `~/projects/BdRPiAMI/srvhome/`;
  canonical source is version-controlled in `BdRDev/fleet/srvhome/`.
- **Live "running" status deferred** (answer #2) — tiles show a neutral
  "status not tracked" badge. Hook point: `app_state()` in `srvhome.py`.
- **History from git log + a pull-time DB** (answer #3) — the post-merge
  hook writes each pulled version to `srvhome.db`; `install.sh`
  back-fills the last 30 commits so history isn't empty on day one
  (those rows tagged "backfilled", dated by commit time not pull time).
- **Version = 7-char short SHA** (answer #4).
- **Scope = PlanBdRad + BdRAMAssist** (answer #5, "as per the
  Ecosystem 2 table" — BdRIS/BdRImpSys is an empty repo, skipped). Edit
  `apps.json` to add more.
- **Sits alongside** the dashboard's Ecosystem / Ecosystem 2 tabs; does
  not replace them. It's a per-server page, not a fleet aggregator.
