DONE

# Update the fleet ecosystem (Supabase) + FLEET.md for BdRPiSrvDungeon

## What was done — 2026-09-15

### Supabase ecosystem data

- **`servers` id 59 (`BdRPiSrvDungeon`)** — updated (not inserted):
  `address` → `10.10.10.30`, `provisioned` stays `false`, `git_notes` now
  records the `bDotRad/BdRPiSrvDungeon` config repo (pushed 2026-09-15,
  authored/pushed from DEV via deploy key
  `bdrdev_to_bdrpisrvdungeongit`). `name` was already `BdRPiSrvDungeon`
  (there's no separate hostname column). OS/specs/tailnet IP left as the
  pre-existing placeholder values — still genuinely unknown, out of scope
  here.
- **`projects` id 6 (`BdRDungeon`, the app)** — `runs_on_server_id` set to
  `59` (was `null`). This closes the drift FLEET.md's "Known drift"
  section had been flagging since 2026-09-08.
- **`projects` id 163 (new row, `BdRPiSrvDungeon`, the config repo)** —
  mirrors the `BdRPiSrvAMI`/`AMI-cfg` row's shape: `runs_on_server_id: 59`,
  `database: none`, `status: planned`, `exists_flag: true`,
  `nickname: "bdr Pi Dungeon — config repo"`. (First pass used
  `nickname: "Dungeon-cfg"` per the request's literal wording, but the
  existing `AMI-cfg` row's actual `nickname` column holds a longer display
  label — `"bdr Pi AMI — box page"` — not the short FLEET.md handle, so the
  nickname was corrected to match that convention. `Dungeon-cfg` is still
  the handle used in `FLEET.md`'s Projects table, which is a separate,
  doc-only column per the existing "no `handle` column yet" drift note.)
- No schema/migration change needed — this was a data-only write via
  PostgREST (`app/fleet_db.py`'s write path), confirmed present in the
  existing `projects`/`servers` tables. `state/ecosystem.json` was left
  untouched (it's a read cache the app overwrites, never a write target).

### Docs — `bDotRad/BdRDev`

- `7286fc0`: `_Instructions/FLEET.md` + `Naming.md` — LAN `10.10.10.30`
  and hostname target for `DUNGEON`, the `BdRPiSrvDungeon` config-repo
  scaffold note, a new `Dungeon-cfg` row in the Projects → deploy target
  table (mirrors `AMI-cfg`), and removal of the now-resolved
  `projects.BdRDungeon.runs_on_server_id` bullet from "Known drift to
  reconcile". (These edits had been hand-made and left uncommitted by the
  2026-09-15 `BdRPiSrvDungeon`-scaffolding session, alongside unrelated
  `RatsNest` additions to the same two files from other in-flight work —
  both landed in the one commit since they were already merged in the
  working tree; unrelated modified files elsewhere in the repo
  (`CLAUDE.md`, `Standards.md`, `index.html`, `doc-updater.md`) were left
  untouched as they belong to other in-progress work.)

### Not done here (explicitly out of scope, per the request)

- Physically provisioning the box — tracked in
  `BdRPiSrvDungeon/BdRPiSrvDungeon-PROVISION.md`.
- The `rFleetMap` generator/schema work (`handle` column, etc.) — separate
  `NOT READY` request.

---

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
