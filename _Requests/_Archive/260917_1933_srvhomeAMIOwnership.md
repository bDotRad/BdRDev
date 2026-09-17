# srvhome → BdRPiSrvAMI ownership + redesign — verified deployed, 2026-09-17

## What was done this pass

The code + docs work (both repos, 2026-09-11) was already done and
pushed per the request body below. This pass's job was just to verify
Brad's Task 3 Action block (on `AMI`) — the part that needed `sudo`/a
live restart this session can't run itself — actually landed, since the
file had been flipped `WAITING RESPONSE` → `READY` with no note either
way.

Read-only checks over SSH to `AMI` (`BdRPiAMI`, LAN alias — no `sudo`,
no restarts run from here):

- `curl http://127.0.0.1:8610/healthz` → `ok`.
- Page serves both `data-tab=status` and `data-tab=info` — confirms the
  two-tab redesign (`644cf6a`) is live, not just committed.
- `git log` on `~/projects/BdRPiAMI` shows the full redesign history up
  through `59f245e` (favicon) and `b27ba1b` (tile links) — later commits
  than what this request describes, so the checkout is current or
  ahead, not stale.
- Footer/tiles render as **BdRPiSrvAMI** (not "srvhome"), confirming
  `2c3a3f4` is live.
- The one `grep` hit for "Generated" on the page is the changelog prose
  in the info tab describing *removal* of that sub-line, not the
  sub-line itself — false alarm, header is clean.
- `srvhome/` file mtimes (`hook.log` etc.) are from today, and
  `install.sh` behavior (per-app hook wiring) matches what the Action
  block asked for — so steps 2 and 3 (pull, restart, re-run installer)
  were carried out.

So Task 3's deploy steps (pull / restart / re-run `install.sh`) are
confirmed done. **Task 3's OS-upgrade step was not** — `apt history.log`
on `AMI` shows no `apt upgrade -y` since the partial one on 2026-09-09
(`containerd.io` only); everything since then is routine
`unattended-upgrade` runs for individual security packages. The 6
originally-named packages, plus several more that have since become
available, are still sitting un-upgraded. Split off as its own
low-priority follow-up: **`rAMIRoutineUpdates.md`** (new, `WAITING
RESPONSE`) — this request's core ask (ownership move + redesign) doesn't
depend on it, so no reason to hold this one open for routine package
maintenance.

No fleet-map/Supabase changes needed here — the request's own "Still
open" section already deferred that to `rFleetMap`, which exists
separately and wasn't touched by this pass.

Nothing in this repo (`BdRDev`) changed as part of this verification
pass — no commit needed here beyond archiving this request.

## Original request (verbatim)

READY

<!-- 2026-09-09 diagnostic writeup → 2026-09-11 built. Code + docs done
     and pushed (both repos). Only the Task 3 Action block (apt upgrade
     + pull + restart on AMI) is left — flip to READY / archive once Brad
     has run it. -->

# Make `BdRPiSrvAMI` the canonical home of `srvhome` + redesign the page

## Decision (Brad, 2026-09-09 / 2026-09-11)

> "just make BdRPiSrvAMI the project and the page that runs"
> "up it… build away."

`srvhome` (the per-box status page at `/` on `AMI`) is now **owned by the
`bDotRad/BdRPiSrvAMI` config repo** (`srvhome/`). `BdRDev/fleet/srvhome/`
is gone. `AMI` runs srvhome from its own config-repo checkout — no
`bDotRad/BdRDev` checkout on that box. `BdRDev` still owns the fleet
WebUI standard (`_Instructions/WebUI.md`) the page follows.

## How we got here (for the archive)

Two sessions made opposite calls 36 min apart on 2026-09-08 and neither
reconciled the other's docs:

- **2026-09-07** `4f9e889` + `fleet/srvhome/DEPLOY-STATUS.md`: "deploy
  srvhome as a read-only `bDotRad/BdRDev` checkout at
  `~/projects/BdRPiAMI/BdRDev`, run from `fleet/srvhome/` inside it."
- **2026-09-08 12:07** `ad12f18`: canonical `fleet/srvhome/` still being
  actively developed on that assumption.
- **2026-09-08 12:43** `026abbd` (on `bDotRad/BdRPiSrvAMI`): a session
  reversed it — copied srvhome into the config repo as `srvhome/`,
  adapted `srvhome.py` (logo path alongside the script, dropped the
  `<repo>/fleet/srvhome/` layout assumption, footer/self-panel repointed
  at `bDotRad/BdRPiSrvAMI`), bundled `rat-logo.png`. The cutover
  happened: `~/projects/BdRPiAMI/BdRDev` was deleted, srvhome kept
  running from `~/projects/BdRPiAMI/srvhome/`. But every BdRDev doc still
  described the retired model, and `BdRDev/fleet/srvhome/` was still
  nominally canonical.

## What was done — 2026-09-11 (both repos pushed)

### `bDotRad/BdRPiSrvAMI`

- `644cf6a` **page redesign** (`srvhome/srvhome.py`, `srvhome/README.md`):
  - removed the `"<server> — hardware, stack, hosted apps and deploy
    history. Generated <ts>."` sub-line under the standard header.
  - **two tabs**, active tab persisted in `location.hash` (`#status` /
    `#info`) so the 15s poll / a refresh doesn't bounce off it:
    - **App status** — one interactive status tile per app + srvhome
      (deployed SHA / branch / link, live status box, Check GitHub /
      Pull). Same `data-app` / `data-role` hooks, so the existing poll +
      click JS drives it unchanged.
    - **Server & app info** — the server panel (srvhome's own update
      tile no longer jammed into it; "Updates" card renamed "OS
      updates"), then a per-application block: description, URL, repo
      path, deployed SHA, full deploy-history table.
  - Claude chat box stays below the tabs, always visible.
  - `render_apps()` + `render_self_updates()` → `render_status_tile()` /
    `render_app_status()` / `render_app_info()`; `render_history_rows()`
    gained a `bare` mode. Compiles, renders, serves `200` locally.
- `1a5af39` brought `update.sh` into `srvhome/` (was
  `BdRDev/fleet/update.sh`).
- Task 1 "final port" was a no-op — `026abbd` was already current with
  canonical through `ad12f18` (the last `fleet/srvhome/` commit);
  `store.py` / `record_deploy.py` byte-identical.

### `bDotRad/BdRDev` — `1f60164`

- removed `fleet/srvhome/` and `fleet/update.sh`; `fleet/README.md` left
  as a tombstone pointer.
- `_Instructions/FLEET.md` / `Naming.md`: srvhome canonical source is now
  `BdRPiSrvAMI/srvhome/`; dropped the `~/projects/BdRPiAMI/BdRDev` story;
  "last verified" → 2026-09-11.
- `_Instructions/WebUI.md`: **Q1 resolved → option 2** — the srvhome
  reference-implementation pointers now name `srvhome/srvhome.py` in the
  sibling `BdRPiSrvAMI` repo (checked out at `~/projects/BdRPiSrvAMI/` on
  DEV); the canonical markup + CSS were always in WebUI.md itself, so
  nothing is lost. (Option 1 didn't work — the dashboard header only
  demonstrates the *two*-line form; srvhome is the only full three-line
  example.)
- `app/common.py`: fixed the stale `BdRAMI` seed hostname
  (`bdrpiami.local` → `bdrpisrvami.local`).
- committed the previously-untracked fleet-map docs (`FLEET.md`,
  `Naming.md`, `Guardrails.md`) + `rFleetMap.md` alongside, since the
  root `CLAUDE.md` already points readers at them.

### `bDotRad/BdRPiSrvAMI` — feedback pass 2026-09-11

- `2c3a3f4`: the page now shows as **BdRPiSrvAMI** (not "srvhome") in
  the App status tile, the info block and the footer — still keyed
  `srvhome` internally. Deploy history is a **collapsible `<details>`
  dropdown** again on the App status tiles (removed from the info tab).
  `apply()` now keeps each tile's left-border colour in sync with the
  poll — it was stuck amber ("not checked yet") even after the status
  box said "up to date", because the server renders the border once and
  only JS could correct it. Network + Tailscale cards span 2 columns;
  page width 1100 → 1200 (Tailscale was too cramped).

## Still open

### Fleet map / Supabase (whoever runs `rFleetMap` picks this up)

`servers.serves_root` for AMI + the `BdRAMI` project row: srvhome's repo
is `bDotRad/BdRPiSrvAMI`, it is not an app. Left for `rFleetMap` since
that request adds the `serves_root` / `is_app` columns anyway.

### Task 3 — Action block for Brad (on `AMI`)

The OS-updates question: the `apt upgrade` on 2026-09-09 20:35 only had
`containerd.io` available at that moment — the other 6 were still inside
Ubuntu's *phased* rollout. They've since gone to 100%; `apt-get -s
upgrade` on AMI now shows all 6 upgrading cleanly, 0 held back. So it's
just a re-run, not a stuck state.

@@@ --- Action --- @@@

1. Clear the 6 remaining OS updates (they were phased-held on the 9th; now available)

"on AMI"
sudo apt update && sudo apt upgrade -y
sudo apt autoremove -y      # drops the now-unused libfwupd2 / libgusb2

2. Pull the redesigned page and restart it

"on AMI — the running page is the BdRPiSrvAMI checkout at ~/projects/BdRPiAMI"
cd ~/projects/BdRPiAMI && git pull --ff-only

"on AMI — restart so the new code loads (per-minute run.sh cron brings
it back on :8610). SIGTERM is fine here — run.sh restarts it, not systemd"
pkill -f 'BdRPiAMI/srvhome/srvhome.py'
sleep 90    # or run: ~/projects/BdRPiAMI/srvhome/run.sh

"on AMI — re-run the installer so the post-merge hook / history backfill
pick up update.sh now living in the repo"
cd ~/projects/BdRPiAMI/srvhome && ./install.sh

"on AMI — verify: healthz ok, page 200, and the header no longer has the
'Generated …' sub-line / now shows the App status + Server & app info tabs"
curl -s http://127.0.0.1:8610/healthz
curl -s http://127.0.0.1:8610/ | grep -o 'data-tab=[a-z]*'

@@@ ------------- @@@
