# DUNGEON provisioned + BdRatsNest live — fleet map updated

Processed 2026-09-16. Raised from a `BdRatsNest` session that had already
done the actual provisioning/deploy work but (per its own `CLAUDE.md`)
doesn't reach into `BdRDev` to touch the ecosystem tables itself.

## What was done

**Verified directly** (didn't just trust the request text) before
writing anything:
- `ssh BdRPiDungeon` (LAN key `bdrdev_to_bdrpidungeonserver`) — confirmed
  the box is really `BdRPiSrvDungeon`, aarch64, Debian 13 (trixie), and
  that the `.pub` file matches `ssh-keygen -y` output on the private key.
- `curl http://10.10.10.30:8440` → `200`, and `ps aux` over SSH shows
  `./venv/bin/python3 app/ratsnest.py` running — BdRatsNest is really up.

**Supabase ecosystem (source of truth, `http://127.0.0.1:8000`)**:
- `servers` id 59 (`BdRPiSrvDungeon`): `provisioned` → `true`, `host` →
  "Raspberry Pi 5", `os` → "Debian 13 (trixie)", `tailscale_ip` →
  `100.73.131.60`, `tag`/`git_notes` updated. Left `ram`/`disk` blank
  rather than keep the old placeholder VM-era guesses — the request
  didn't supply real figures for the Pi 5 and the row previously
  described a VM (`host: "VM"`), not this hardware.
- `projects`: inserted new row `BdRatsNest` (id 165) — `runs_on_server_id`
  59, `local_url` `http://10.10.10.30:8440`, `ts_url`
  `http://100.73.131.60:8440`, `database` `none`, `status` `live`. (The
  "not a systemd service, won't survive reboot" caveat has nowhere to go
  in the `projects` schema — `status` is a closed enum — so it's carried
  in `FLEET.md` prose instead, see below.)
- `projects.BdRDungeon.runs_on_server_id` was already `59` — the "known
  drift" item #3 in `FLEET.md` asking to fix this was **already stale**,
  fixed sometime before this pass. Removed that item from the drift list
  rather than re-doing it.

**`_Instructions/FLEET.md`**:
- "Last verified by hand" banner updated.
- `DUNGEON` row in the Boxes table: host/tailnet columns filled in.
- New `### DUNGEON` section: hardware details, a "what runs where" table
  for BdRatsNest (flagged as **live but not a systemd service**), and a
  note that `srvhome`/`BdRDungeon` are still not deployed there despite
  the box existing now.
- SSH matrix: added `DEV → DUNGEON` row.
- Projects → deploy target table: added `BdRatsNest` row, updated
  `BdRDungeon`'s "deployed on" note to distinguish "server provisioned"
  from "app deployed" (it's the former only).
- Added a **"Naming note: two RatsNest's, temporarily"** section — see
  below, this is the one judgment call in this pass.

**`_Instructions/Naming.md`**:
- `DUNGEON` box row: hostname/tailnet filled in, added the transient
  mid-setup hostname `BdRpi` to the "don't use" aliases list.
- Added a `BdRatsNest` row to the Projects table.

**`_Instructions/SSH.md`**:
- Added `bdrdev_to_bdrpidungeonserver` (confirmed working, key verified
  against its `.pub`) and `bdrpisrvdungeon_to_bdratsnestgit` (generated
  on `DUNGEON` itself, not this host — a deploy key for the private
  `BdRatsNest` repo) to the inventory table.

## Judgment call made without asking Brad

`BdRatsNest` (the new home-automation project) is explicitly meant to
**replace** the existing `RatsNest` Home Assistant appliance (confirmed
in `BdRatsNest/Description.md`), but that appliance hasn't been retired
yet — so both a box handle `RatsNest` and a would-be project handle
`RatsNest` exist at the same time, which `Naming.md`'s one-canonical-name
rule doesn't allow. Rather than stopping the whole pass on this, gave the
new project the unabbreviated handle `BdRatsNest` (instead of the usual
BdR-prefix-stripped short form other projects get, e.g. `BdRDungeon` →
`Dungeon`) so it can't collide with the appliance's `RatsNest` handle,
and left a note in `FLEET.md` to revisit once the appliance is actually
decommissioned. This is a naming convention, not a deployment fact, so
it's easily changed later without breaking anything if Brad wants a
different handle.

## Not done (out of scope for this request)

- No systemd unit for BdRatsNest — the request itself flagged this as
  "known follow-up, not done," and fixing it would mean `sudo`/service
  work on a remote box, which the fleet rules route through an Action
  block, not just quietly doing it.
- `projects.BdRIS` / `fleet_meta.notes` drift (both pre-existing,
  unrelated to this request) left alone.
- Didn't touch `~/projects/BdRatsNest`'s own `CLAUDE.md`/`Description.md`
  — those already read as current and per the fleet rule, work belonging
  to another project's directory isn't this request's job.

Committed and pushed as part of this pass.

---

Original request:

READY

# Update fleet ecosystem — DUNGEON provisioned, BdRatsNest deployed

Raised from a `BdRatsNest` session on 2026-09-16. That session set the
box up and confirmed everything below directly, but per its own
`CLAUDE.md` it doesn't reach into `BdRDev` to edit the ecosystem tables
itself — that's this request.

## What changed

**DUNGEON (`BdRPiSrvDungeon`) is now provisioned** — flip it out of
"not provisioned" everywhere that's recorded (`FLEET.md`, `Naming.md`,
the `servers` table).

- Hardware: Raspberry Pi 5, Debian 13 (trixie), aarch64. Hostname is
  now `BdRPiSrvDungeon` (was `BdRpi` before a rename during setup).
  Login user `bdr`.
- LAN IP: `10.10.10.30` (moved once during setup off an initial
  `10.10.8.19` — `.30` is current).
- Tailnet: `bdrpisrvdungeon.tail0ed3f6.ts.net` / `100.73.131.60`.
- SSH from DEV: `ssh BdRPiDungeon` (alias in DEV's `~/.ssh/config`),
  key `bdrdev_to_bdrpidungeonserver` — headless, LAN key-based, same
  pattern as `BdRPiAMI`. Add a row to the SSH matrix in `FLEET.md` and
  the key to the inventory table in `SSH.md`.

**BdRatsNest is now deployed on DUNGEON** (previously authored-only on
DEV, target listed as "not yet provisioned").

- Cloned at `~/projects/BdRatsNest` on DUNGEON, via its own read-only
  GitHub deploy key `bdrpisrvdungeon_to_bdratsnestgit` registered on
  the `bDotRad/BdRatsNest` repo (private repo, so this key was
  required — new key, doesn't replace anything).
- Running as a plain `./run.sh` background process (Flask dev server)
  on port `8440` — **not yet a systemd service**, so it won't survive
  a reboot. That's a known follow-up, not done.
- Reachable at `http://10.10.10.30:8440` (LAN) and
  `http://100.73.131.60:8440` (tailnet) — confirmed both work.

## Suggested updates

1. `servers` row for `BdRPiSrvDungeon` (id 59, per the "known drift"
   note already in `FLEET.md`) — fill in the LAN/tailnet IPs above,
   mark provisioned.
2. `projects.BdRatsNest.runs_on_server_id` → point at that server row.
3. While in there: `FLEET.md` already flags
   `projects.BdRDungeon.runs_on_server_id` as `null` despite
   `BdRPiSrvDungeon` existing — same server row, worth fixing in the
   same pass.
4. `FLEET.md`: move `DUNGEON` out of "not provisioned" in the Boxes
   table (fill in host/LAN/tailnet columns), add the DEV→DUNGEON SSH
   matrix row, add a "What runs where" section for DUNGEON listing
   BdRatsNest (mock/placeholder device grid, no real Shelly/ESP32
   integration yet — see BdRatsNest's own `CLAUDE.md`).
5. `Naming.md`: fill in `BdRPiSrvDungeon`'s LAN/tailnet columns (blank
   while unprovisioned).
6. Note in `FLEET.md` that BdRatsNest on DUNGEON is a manually-started
   dev server, not a systemd service — so "live" here means "running
   right now", not "survives a reboot".
