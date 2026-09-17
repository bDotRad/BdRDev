# BdRDev

Web dashboard + round-robin scheduler that orchestrates every Claude
Code project on this Pi (`~/projects/*`) — including itself. If you're
reading this from inside a session the scheduler just woke up, you're
working on the thing that's currently managing your own wake/sleep
cycle. Be extra careful with `app/scheduler.py` and
`app/dashboard.py`/`systemd/*.service` — a broken scheduler can't fix
itself; it just stops scheduling.

## Read first

- [README.md](README.md) — architecture (`dashboard.py` + `scheduler.py`
  + shared `common.py`), setup, systemd/nginx install steps
- [_Instructions/Requests.md](_Instructions/Requests.md) — the
  request-intake convention this project both implements *and* uses on
  itself (`_Requests/rN.md`, READY/NOT READY marker, archive process)
- [_Instructions/BdRDev.md](_Instructions/BdRDev.md) — the
  orchestration doc meant to be copied into *other* projects so their
  Claude sessions understand why they get woken/killed by this scheduler
- [_Instructions/Standards.md](_Instructions/Standards.md) — the
  two-layer standards system: `_Instructions/*` here is the canonical
  fleet-wide layer (incl. [WebUI.md](_Instructions/WebUI.md) — look &
  feel, 7-char-SHA versioning, the Edit/Save/Cancel table pattern;
  [HTTPS.md](_Instructions/HTTPS.md) — the two-front-door TLS standard,
  tailnet via `tailscale serve`, LAN via a standalone self-signed cert,
  no fleet CA); each project's own docs are the override layer
- [_Instructions/FLEET.md](_Instructions/FLEET.md) +
  [Naming.md](_Instructions/Naming.md) +
  [Guardrails.md](_Instructions/Guardrails.md) — the fleet map, the
  canonical name/handle for every box and project, and the hard rules
  for unattended sessions (never repoint `/`, tear down a service, or
  reach outside your project). Each box also has a generated
  `~/projects/CLAUDE.md` with its own identity + guardrails.
- `_Requests/_Archive/` — dated writeups of every request processed so
  far; check here before re-solving something already handled

## Things that aren't obvious from the code

- **No sudo here.** Neither this session nor any tooling working on
  this repo has passwordless sudo. `systemctl restart/start` on
  `bdrdev-dashboard`/`bdrdev-scheduler`, and anything under
  `/etc/nginx/` or `/etc/systemd/`, needs Brad to run it by hand. Leave
  the exact command for him rather than trying to work around it.
- **`kill <pid>` (SIGTERM) does not restart these services.** systemd's
  `Restart=on-failure` treats SIGTERM as an intentional stop, not a
  crash — it won't relaunch. `kill -9 <pid>` (SIGKILL) *does* count as
  a failure and does trigger a restart, which is the only way to pick
  up a code change without Brad's `sudo systemctl restart` — but that's
  a real (if brief) outage of a live single-user dashboard, so treat it
  as a deliberate, not casual, move.
- **Concurrent editing is real, not hypothetical.** The scheduler can
  wake a Claude Code session in this exact working directory while a
  human-driven session (or another tool) is also editing these same
  files. That's already happened here more than once. If you're mid-edit
  and `git status`/a file's content don't match what you expect, check
  whether another session touched it before assuming your own edit was
  lost — don't blindly overwrite.
- **Flask runs with `debug=False`, no autoreload.** Editing
  `app/templates/index.html`, `app/*.py`, or the static logo doesn't
  take effect on the live dashboard until the process restarts (see the
  sudo/SIGKILL notes above). Don't report a fix as "done" without
  actually forcing that restart and verifying via `curl`.
- **Directory/name changes ripple into state files.** `state/
  selected_projects.json` and `state/scheduler_state.json` hold plain
  project *names* (directory basenames), not paths. Renaming a project
  directory silently drops it out of the rotation until those names are
  fixed too — that's a real bug that already happened during the
  BdRGUI → BdRAIGUI rename, and again during the BdRAIGUI → BdRDev
  rename (2026-08-25).
- **This project is in its own rotation pool.** `state/
  selected_projects.json` normally includes `"BdRDev"` itself, so
  the scheduler wakes a session here whenever `_Requests/` has a READY
  item — same as any other project it manages.

## Conventions

Everything in [README.md](README.md)'s "Conventions this implements"
section applies here too, since this project both defines and follows
those conventions on itself: request intake, `.claude-status/
status.json`, SQL-output handoff. See that file rather than duplicating
it here.
