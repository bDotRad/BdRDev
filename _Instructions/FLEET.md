# FLEET.md — the fleet map

Fleet-wide layer (see [`Standards.md`](Standards.md)). The single place a
session goes to learn **what boxes exist, what runs on each, and how they
reach each other.** Names follow [`Naming.md`](Naming.md).

> **Source of truth:** the self-hosted Supabase on `DEV`
> (`http://127.0.0.1:8000` — `servers`, `projects`, `project_roles`,
> `server_software`, `fleet_meta`). `DEV` is the ecosystem master.
> `BdRDev/state/ecosystem.json` mirrors it as a read cache.
>
> **This file is meant to be generated** from that data (see the
> `rFleetMap` request) so it can't drift. Until the generator lands it is
> maintained by hand — if you change a deployment fact, update Supabase
> **and** this file in the same request (see
> [`Requests.md`](Requests.md) § "Keeping the fleet map current").
>
> Last verified by hand: **2026-09-16** (`DUNGEON`/`BdRPiSrvDungeon`:
> hardware provisioned — Raspberry Pi 5, Debian 13 (trixie), aarch64,
> LAN `10.10.10.30`, tailnet joined. `BdRatsNest` deployed and live
> there, port `8440`).

## Boxes

| handle | canonical | host | LAN | tailnet | Claude? | serves `/` |
|---|---|---|---|---|---|---|
| `DEV` | `BdRPiSrvDev` | Raspberry Pi, Ubuntu Server, 8GB | `10.10.8.11` | `bdrpisrvdev.tail0ed3f6.ts.net` / `100.116.147.74` | yes (scheduler + CloudCLI) | BdRDev dashboard |
| `AMI` | `BdRPiSrvAMI` | Raspberry Pi, 8GB | `10.10.10.20` | `bdrpisrvami.tail0ed3f6.ts.net` / `100.86.25.88` | yes | `srvhome` |
| `DUNGEON` | `BdRPiSrvDungeon` | Raspberry Pi 5, Debian 13 (trixie), aarch64 | `10.10.10.30` | `bdrpisrvdungeon.tail0ed3f6.ts.net` / `100.73.131.60` | not yet | `srvhome` (repo scaffolded, not deployed) |
| `BIRD` | `BdRBirdDetector` | Raspberry Pi, RPi OS Lite, 4GB | `192.168.1.187` | not on tailnet | no | app (`bdrbirddetector.local`) |
| `RatsNest` | `RatsNest` | Home Assistant Green appliance, Home Assistant OS | `10.10.10.100` | not on tailnet | no | Home Assistant (`ratsnest.local:8123`) |

`DEV` is the **dev host** — every repo is authored here and pushed to
GitHub from here; every other box only pulls.

## What runs where

### `DEV` — `BdRPiSrvDev`

| what | handle | URL(s) | status |
|---|---|---|---|
| BdRDev dashboard + scheduler | `DEV` | `https://bdrpisrvdev.local` · `https://bdrpisrvdev.tail0ed3f6.ts.net` | live — served at `/` |
| CloudCLI (Claude Code web UI) | `CloudCLI` | `http://bdrpisrvdev:3001` (tailnet IP only) | deployed |
| BdRWebGUIDev | `WebGUI` | `http://bdrpisrvdev.local:8430` · `…ts.net:8430` | live |
| self-hosted Supabase — fleet **ecosystem** DB | — | `http://127.0.0.1:8000` | live (this box is ecosystem master) |
| `DEV-cfg` = `BdRVSrvDev` repo | `DEV-cfg` | — | box config only, not a service |

### `AMI` — `BdRPiSrvAMI`

| what | handle | URL(s) | status |
|---|---|---|---|
| `srvhome` — box status page | `srvhome` | `https://bdrpisrvami.local/` | deployed — served at `/`, **not an app** |
| BdRAMAssist | `AMAssist` | `https://bdramassist.local` · `…ts.net:8444` | building |
| PlanBdRad | `PlanBdR` | `https://planbdrad.local` · `…ts.net:8443` | building |
| self-hosted Supabase (Studio + API) — app DB | — | `:8000` / `:8443` studio | live |
| BdRImpSys | `ImpSys` | — | checkout only, not deployed |
| `AMI-cfg` = `BdRPiSrvAMI` repo | `AMI-cfg` | — | box config + canonical `srvhome/` source |

`srvhome` runs from the box's own `bDotRad/BdRPiSrvAMI` checkout
(`~/projects/BdRPiAMI/srvhome/`, `127.0.0.1:8610`, nginx `location /`).
Canonical source is the **`BdRPiSrvAMI` repo, `srvhome/`** — moved out of
`BdRDev/fleet/srvhome/` on 2026-09-11 so the AMI box no longer needs a
BdRDev checkout. `BdRDev` still owns the fleet WebUI standard
(`_Instructions/WebUI.md`) that page follows.

### `DUNGEON` — `BdRPiSrvDungeon`

Provisioned 2026-09-16: Raspberry Pi 5, Debian 13 (trixie), aarch64.
Hostname is now `BdRPiSrvDungeon` (was briefly `BdRpi` mid-setup — don't
use that alias). LAN `10.10.10.30` (moved once during setup off an
initial `10.10.8.19`; `.30` is current), login user `bdr`, tailnet
`bdrpisrvdungeon.tail0ed3f6.ts.net` / `100.73.131.60`.

| what | handle | URL(s) | status |
|---|---|---|---|
| BdRatsNest | `BdRatsNest` | *stale — was `https://bdrpisrvdungeon:8440`, app terminating its own TLS; that's being reverted, see below* | **live** (currently the broken TLS-on-app build), manually started (`./run.sh`, plain Flask dev server) — **not a systemd service**, won't survive a reboot |

The `bDotRad/BdRPiSrvDungeon` config repo is scaffolded (mirrors
`BdRPiSrvAMI`: `srvhome/`, nginx, TLS, tailscale,
`BdRPiSrvDungeon-PROVISION.md`) but `srvhome` itself isn't deployed
there yet — nothing currently serves `/` on this box. `BdRDungeon` (the
other project slated for this box) also isn't deployed yet, just its
server row is linked.

BdRatsNest controls **real Shelly devices** over Gen2+ RPC (six relay
channels + three Pro EM50 energy meters, verified end-to-end against
the physical hardware) — not a mock/placeholder grid, see the
project's own `CLAUDE.md` Status section (as of 2026-09-16). It's
authored on `DEV` and pulled onto `DUNGEON` via its own read-only
GitHub deploy key `bdrpisrvdungeon_to_bdratsnestgit` (generated on the
`DUNGEON` box itself, registered on the private `bDotRad/BdRatsNest`
repo — a new key, doesn't replace anything).

**2026-09-18: TLS revert pending deploy.** `BdRatsNest` briefly grew
its own in-process TLS (commits `4e000b2`/`815a9cc`), which broke it
against `BdRPiSrvDungeon`'s nginx (`proxy_pass http://127.0.0.1:8440`
expects a plain-HTTP backend) — a live instance of the exact
"never terminate TLS in the app" mistake `HTTPS.md` documents. Reverted
on `DEV` (commit `7cb48de`, pushed) to plain HTTP on `127.0.0.1:8440`
per `BdRatsNest/_Requests/rHTTPSStandardAdopt.md`. **Not yet deployed**
— `DUNGEON` still needs a `git pull` + process restart (Action block
left in that request, `WAITING RESPONSE`, since a session can't
restart a remote daemon unattended). Once binding to `127.0.0.1` only,
the app is no longer reachable by direct port from the LAN/tailnet —
external reachability then depends on `DUNGEON`'s own nginx vhost /
`tailscale serve` config for this app, which is a **separate,
not-yet-done** migration tracked in the `BdRPiSrvDungeon` repo's own
`rHTTPSStandardAdopt.md` (see `HTTPS.md` adoption table — `DUNGEON` is
still "fan-out", own `fleetCA`, not migrated). The real post-fix URL
is unknown until that lands; don't fill in a guessed one here or in
the ecosystem Supabase row until it's confirmed.

### `BIRD` — `BdRBirdDetector`

Runs the edge detection pipeline (`edge/` in the `BdRBirdDetector` repo).
Pull-only from GitHub, pushes to Firebase. No Claude Code on the box.
**Unreachable from the rest of the fleet** — foreign subnet
(`192.168.1.0/24`), not on the tailnet.

### `RatsNest`

| what | handle | URL(s) | status |
|---|---|---|---|
| Home Assistant | — | `http://ratsnest.local:8123` | live |

A Home Assistant Green appliance running Home Assistant OS — not a Pi
BdRDev provisioned, no Claude Code, no repo/project of its own. Not on
the tailnet; reachable on the LAN at `10.10.10.100` / `ratsnest.local`.

## SSH matrix

| from → to | command | headless? | notes |
|---|---|---|---|
| `DEV` → `AMI` | `ssh BdRPiAMI` (`bdr@10.10.10.20`) | ✅ yes | LAN key `bdrdev_to_bdrpiamiserver`. Use the LAN alias/IP, **not** the `*.ts.net` name. |
| `DEV` → `DUNGEON` | `ssh BdRPiDungeon` (`bdr@10.10.10.30`) | ✅ yes | LAN key `bdrdev_to_bdrpidungeonserver`, same pattern as `AMI`. Use the LAN alias/IP, **not** the `*.ts.net` name. |
| `DEV` → `BIRD` | — | ❌ | no key, foreign subnet, off tailnet |
| `AMI` → anywhere | — | ❌ | `AMI` is a leaf; don't SSH out from it |
| any → `DEV` | `ssh` as `bdr` | — | only one key trusted in `authorized_keys` |
| Tailscale SSH (any `*.ts.net`) | — | ❌ | gated by interactive re-auth — hangs an unattended session forever. See [`SSH.md`](SSH.md). |

**Rule:** an SSH session into another box is for read-only checks and
file copies only. Never start/restart a daemon or run `sudo` remotely —
write an Action block for Brad ([`Requests.md`](Requests.md)).

## Projects → deploy target

| project | handle | authored on | deployed on | GitHub `bDotRad/` | DB |
|---|---|---|---|---|---|
| `BdRDev` | `DEV` | `DEV` | `DEV` | `BdRDev` (DEV pushes **and** pulls) | none |
| `BdRAMAssist` | `AMAssist` | `DEV` | `AMI` (pull) | `BdRAMAssist` | shares PlanBdR's Supabase |
| `PlanBdRad` | `PlanBdR` | `DEV` | `AMI` (pull) | `PlanBdRad` | Supabase on `AMI` |
| `BdRDungeon` | `Dungeon` | `DEV` | `DUNGEON` (planned — server provisioned, app not deployed yet) | `BdRDungeon` | Supabase (planned) |
| `BdRatsNest` | `BdRatsNest` | `DEV` | `DUNGEON` (live, dev server) | `BdRatsNest` | none |
| `BdRBirdDetector` | `Bird` | `DEV` | `BIRD` (pull) | `BdRBirdDetector` | SQLite on box + Firebase |
| `BdRWebGUIDev` | `WebGUI` | `DEV` | `DEV` | `BdRWebGUIDev` | none |
| `BdRPiSrvAMI` | `AMI-cfg` | `DEV` | `AMI` (pull, as `~/projects/BdRPiAMI/`) | `BdRPiSrvAMI` | SQLite `srvhome.db` |
| `BdRPiSrvDungeon` | `Dungeon-cfg` | `DEV` | `DUNGEON` (pull) | `BdRPiSrvDungeon` | none |
| `BdRVSrvDev` | `DEV-cfg` | `DEV` | `DEV` | *(check repo)* | none |
| `BdRImpSys` | `ImpSys` | `DEV` | `AMI` (checkout only) | `BdRImpSys` | none yet |

## Known drift to reconcile (2026-09-08)

The Supabase data is behind reality in at least these spots — fix as part
of the next request that touches them:

- `projects.BdRIS` has `exists_flag = false`, but `~/projects/BdRImpSys`
  exists on `AMI`. Rename the row to `BdRImpSys`, set `exists_flag`.
- `servers` has no column for **what each box serves at `/`** or for the
  **handle** — both are only in this file / `Naming.md` until the
  `rFleetMap` schema change lands.
- `fleet_meta.notes` is a stale prose blob (mentions the retired
  `192.168.100.x` VM, "hostname still BdRDev", etc.). Replace with a
  short pointer to this file.

## Naming note: two "RatsNest"s, temporarily

`BdRatsNest` (new project, this box's `DUNGEON` deploy) is built to
**replace** the existing `RatsNest` Home Assistant Green appliance
(separate box, `10.10.10.100`, see the `RatsNest` row above) — Brad
found full Home Assistant overkill and is retiring that box once
`BdRatsNest` takes over, per `BdRatsNest/Description.md`. Until that
retirement happens, both exist at once, so per `Naming.md`'s
one-canonical-name rule the **project** keeps the unabbreviated handle
`BdRatsNest` (not shortened to `RatsNest`) specifically to avoid
colliding with the appliance box's handle `RatsNest`. When the appliance
is decommissioned, revisit whether the project should absorb the shorter
handle.
