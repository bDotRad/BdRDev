READY

# Update the fleet ecosystem (Supabase) + FLEET.md for BdRPiSrvDungeon

From a 2026-09-15 session in `BdRPiSrvDungeon` that scaffolded that box's
config repo (mirroring `BdRPiSrvAMI`: `srvhome/`, nginx, TLS, tailscale,
provisioning runbook) and got new deployment facts from Brad. Per
`_Instructions/Requests.md` § "Keeping the fleet map current", those facts
need to land in the Supabase ecosystem tables (and this repo's hand-maintained
docs), same as any other project's deployment-fact change.

## Facts to record

- **`servers` row for `BdRPiSrvDungeon`** (already exists as `servers.id 59`
  per FLEET.md's "Known drift" note — update it, don't create a new row):
  - `address` (LAN) = `10.10.10.30` (reserved 2026-09-15, confirmed by Brad)
  - hostname target = `BdRPiSrvDungeon`
  - `provisioned` = still **false** — this is a LAN reservation + a
    config-repo scaffold on DEV, not a physical box yet. OS/specs/tailnet
    IP are all still unknown.
  - `git_notes` (or equivalent) — config repo `bDotRad/BdRPiSrvDungeon`
    exists, pushed 2026-09-15, authored/pushed from DEV via deploy key
    `bdrdev_to_bdrpisrvdungeongit`.

- **`projects` row for `BdRDungeon`** — this is the drift FLEET.md already
  flags ("`projects.BdRDungeon.runs_on_server_id` is `null` despite
  `BdRPiSrvDungeon` (`servers.id 59`) existing. Point it there.") — fix it
  now that the server row is more filled in.

- **New/updated `projects` row for `BdRPiSrvDungeon` itself** (the config
  repo, same shape as the existing `AMI-cfg` = `BdRPiSrvAMI` row): authored
  on `DEV`, deployed on `DUNGEON` (pull-only, once provisioned), GitHub
  `bDotRad/BdRPiSrvDungeon`, no DB.

## Docs already updated, need review + commit

I hand-edited `_Instructions/FLEET.md` and `_Instructions/Naming.md` in this
checkout to add the LAN address and hostname for `DUNGEON` (the "until the
generator lands it's maintained by hand" path) — **left uncommitted**
on purpose, since this repo had unrelated in-progress changes sitting in the
working tree at the time and I didn't want to bundle or push over them.
Please review those two files' diffs, fold them into whatever's already in
flight (or commit separately if cleaner), and push once the Supabase side
above is also done — same "map updated is part of request done" rule.

## Not in scope here

- Physically provisioning the box (hardware/OS still TBD) — that's
  `BdRPiSrvDungeon/BdRPiSrvDungeon-PROVISION.md`, a separate follow-up.
- The `rFleetMap` generator work (`handle`/`serves_root` schema columns,
  etc.) — that's the existing `NOT READY` request in this folder; this
  request only updates data in the *current* schema.
