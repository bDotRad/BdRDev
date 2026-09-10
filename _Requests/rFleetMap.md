NOT READY

# Fleet map — make it generated, schema-backed, and self-updating

Follow-up to the 2026-09-08 session that added the doc layer:
`_Instructions/Naming.md`, `_Instructions/FLEET.md`,
`_Instructions/Guardrails.md`, per-box `~/projects/CLAUDE.md` (DEV
written in place; AMI deployed + tracked at
`BdRPiSrvAMI/projects-root-CLAUDE.md`), plus the doc-updater /
`Requests.md` "keep the fleet map current" rule.

Those are hand-maintained today. This request makes the map generated so
it can't drift, and closes the known gaps.

## Work

### 1. Schema: add the identity + `/` columns the map needs

`supabase/` migration (draft it, don't run it — Brad runs migrations,
updates `SQL_RUN.md`):

- `servers.handle` text unique — `DEV` / `AMI` / `DUNGEON` / `BIRD`.
- `servers.serves_root` text — what that box serves at `/` (e.g.
  `"BdRDev dashboard"`, `"srvhome"`). This is the field whose absence
  let a session mistake `srvhome` for an app.
- `projects.handle` text unique — `AMAssist` / `PlanBdR` / `WebGUI` / …
- `projects.is_app` bool — false for `BdRDev`, `AMI-cfg`, `srvhome`-like
  entries that are served at `/` and aren't applications.
- new table `fleet_aliases (kind enum('server','project'), canonical
  text, alias text)` — the "do not use" list, so the generator and any
  future lint can resolve an alias → canonical.
- replace the `fleet_meta.notes` blob with a one-liner pointing at
  `_Instructions/FLEET.md`.

Then extend `app/fleet_db.py` + `app/common.py` `_normalize_ecosystem()`
+ the Ecosystem editor UI to read/write the new columns.

### 2. Reconcile the current drift (from FLEET.md § "Known drift")

- `projects` row `BdRIS` → rename `BdRImpSys`, `exists_flag = true`,
  handle `ImpSys` (checkout exists on AMI: `~/projects/BdRImpSys`).
- `projects.BdRDungeon.runs_on_server_id` → `59` (`BdRPiSrvDungeon`).
- Fill `handle` / `serves_root` / `is_app` for every existing row.

### 3. Generator

`fleet/gen-fleet-md.py` (stdlib only, same terse style the `srvhome`
page in the `BdRPiSrvAMI` repo is written in):

- reads the live ecosystem data (`fleet_db.fetch_ecosystem()`), falls
  back to `state/ecosystem.json`;
- renders `_Instructions/FLEET.md` (everything except the hand-written
  intro/SSH-matrix prose — keep those in a small tracked
  `fleet/fleet-map.header.md` include, since the SSH matrix and
  guardrail text are stable identity/safety data, not deployment data);
- renders each box's `~/projects/CLAUDE.md` from a template +
  that box's row (`serves_root`, hosted projects, SSH reach, guardrail
  block);
- writes the AMI copy to `BdRPiSrvAMI/projects-root-CLAUDE.md` in this
  repo's sibling checkout path if present, else prints it.

### 4. Wiring — keep the on-box files fresh

Pick one (see Q1):

- (a) `scheduler.py` `spawn_session()` / `ensure_independent_session()`
  regenerate `~/projects/CLAUDE.md` before the `tmux new-session` (cheap,
  always current, but couples it to the scheduler);
- (b) a `systemd --user` timer on each box, every ~30 min, runs the
  generator (decoupled; AMI needs the generator shipped in its BdRDev
  checkout);
- (c) both — scheduler on DEV, timer on AMI.

CloudCLI can't be hooked without patching the npm package, so the file
must exist on disk regardless — (b) or (c) covers that.

### 5. Ecosystem page

The dashboard Ecosystem tab is what Brad tried to use as the map and it
had dead links / wrong names. Audit it against the regenerated data:
fix the link columns (`local_url` / `ts_url` rendering), show `handle`
and `serves_root`, add a "last verified" line, and reuse `srvhome`'s
reachability probe to flag rows that don't actually respond.

## Decisions

??? --- Question --- ???

Q1. Which wiring option for keeping `~/projects/CLAUDE.md` fresh?

Options:
1. (c) scheduler regenerates on DEV + a user timer on AMI (recommended)
2. (b) user timer on every box only
3. (a) scheduler only — leaves AMI's file to go stale

Answer:

??? --------------- ???

??? --- Question --- ???

Q2. Handles — confirm the set in `_Instructions/Naming.md`
(`DEV`, `AMI`, `DUNGEON`, `BIRD` for boxes; `AMAssist`, `PlanBdR`,
`WebGUI`, `Dungeon`, `Bird`, `DEV`, `AMI-cfg`, `DEV-cfg`, `ImpSys` for
projects). Any you want changed before they get baked into the DB?

Answer:

??? --------------- ???

??? --- Question --- ???

Q3. `BdRVSrvDev` (`DEV-cfg`) — does it have a GitHub remote? FLEET.md
has a "(check repo)" placeholder. Needed to complete the projects table.

Answer:

??? --------------- ???
