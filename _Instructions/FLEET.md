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
> Last verified by hand: **2026-09-27** (box formerly `DUNGEON` /
> `BdRPiSrvDungeon` renamed to `RATSNEST` / `BdRPiSrvRatsNest` per Brad;
> OS hostname, mDNS and tailnet name all verified renamed and surviving
> a reboot. `tailscale serve` + nginx on it broken since that reboot —
> see the `RATSNEST` section. `HA` Green appliance being retired).

## Boxes

| handle | canonical | host | LAN | tailnet | Claude? | serves `/` |
|---|---|---|---|---|---|---|
| `DEV` | `BdRPiSrvDev` | Raspberry Pi, Ubuntu Server, 8GB | `10.10.8.11` | `bdrpisrvdev.tail0ed3f6.ts.net` / `100.116.147.74` | yes (scheduler + CloudCLI) | BdRDev dashboard |
| `AMI` | `BdRPiSrvAMI` | Raspberry Pi, 8GB | `10.10.10.20` | `bdrpisrvami.tail0ed3f6.ts.net` / `100.86.25.88` | yes | `srvhome` |
| `RATSNEST` | `BdRPiSrvRatsNest` | Raspberry Pi 5, Debian 13 (trixie), aarch64 | `10.10.10.30` | `bdrpisrvratsnest.tail0ed3f6.ts.net` / `100.73.131.60` | not yet | `srvhome` (running on `127.0.0.1:8610`; front doors broken — see below) |
| `BIRD` | `BdRBirdDetector` | Raspberry Pi, RPi OS Lite, 4GB | `192.168.1.187` | not on tailnet | no | app (`bdrbirddetector.local`) |
| `HA` | `HA` | Home Assistant Green appliance, Home Assistant OS — **being retired** | `10.10.10.100` | not on tailnet | no | Home Assistant (`ratsnest.local:8123`) |

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

### `RATSNEST` — `BdRPiSrvRatsNest`

Provisioned 2026-09-16: Raspberry Pi 5, Debian 13 (trixie), aarch64.
**Renamed 2026-09-27** from `DUNGEON` / `BdRPiSrvDungeon` — it hosts
two projects: `BdRDungeon` (circuits and testing in the Dungeon) and
`BdRatsNest` (the new home automation, replacing the `HA` Green).
OS hostname `BdRPiSrvRatsNest` (was the Imager name `BdRpi`, never
actually `BdRPiSrvDungeon`). **cloud-init gotcha:** Imager's
`/boot/firmware/user-data` sets `hostname:` and cloud-init re-applies it
every boot, which silently undid the first rename. Fixed by changing
that line and adding `/etc/cloud/cloud.cfg.d/99-keep-hostname.cfg`
(`preserve_hostname: true`). On a fresh install, set the name in
Imager. LAN `10.10.10.30` / `bdrpisrvratsnest.local`, login user `bdr`,
tailnet `bdrpisrvratsnest.tail0ed3f6.ts.net` / `100.73.131.60`. Things
that keep the old name for now
(renaming them is separate, deferred work — see `Naming.md`): SSH alias
`BdRPiDungeon` + key `bdrdev_to_bdrpidungeonserver`, the config repo
`BdRPiSrvDungeon`, and the deploy keys named `*bdrpisrvdungeon*`.

| what | handle | URL(s) | status |
|---|---|---|---|
| `srvhome` — box status page | `srvhome` | `https://bdrpisrvratsnest.tail0ed3f6.ts.net/` (`tailscale serve` → `127.0.0.1:8610`) | running from `~/projects/BdRPiSrvDungeon/srvhome/`; **unreachable since 2026-09-27**, see below |
| BdRatsNest | `BdRatsNest` | `https://bdrpisrvratsnest.tail0ed3f6.ts.net:8441` (`tailscale serve` → `127.0.0.1:8440`) | **live**, systemd `bdratsnest.service`, plain HTTP backend; **unreachable since 2026-09-27**, see below |
| *(unknown)* | — | `…ts.net:8445` → `127.0.0.1:8085` | `tailscale serve` mapping exists, nothing listening on `:8085` |

**2026-09-27: front doors broken by the rename + reboot.** Backends
are fine (`127.0.0.1:8610` and `:8440` both return 200 on the box). Two
separate faults:
- **`tailscale serve`** config is still keyed to the old name
  `bdrpisrvdungeon.tail0ed3f6.ts.net`, so a TLS handshake to
  `bdrpisrvratsnest…` fails with `tlsv1 alert internal error`. It needs
  a reset and the mappings re-adding. Action block in
  `_Requests/rRatsNestRename.md`.
- **nginx** is `failed`: `bind() to 0.0.0.0:443 … Address already in
  use`. On this boot `tailscale serve` grabbed the tailnet IP's `:443`
  first. This is a latent config fault, not caused by the rename: per
  `HTTPS.md`, nginx must `listen` on the LAN IP + `127.0.0.1` only.
  The fix belongs in the `BdRPiSrvDungeon` repo (its
  `rHTTPSStandardAdopt.md`). Until then there is no LAN HTTPS
  (`bdrpisrvratsnest.local`).

The `bDotRad/BdRPiSrvDungeon` config repo mirrors `BdRPiSrvAMI`
(`srvhome/`, nginx, TLS, tailscale, `BdRPiSrvDungeon-PROVISION.md`).
`BdRDungeon` isn't deployed yet, only its server row is linked.

BdRatsNest controls **real Shelly devices** over Gen2+ RPC (six relay
channels + three Pro EM50 energy meters, verified end-to-end against
the physical hardware) — not a mock/placeholder grid, see the
project's own `CLAUDE.md` Status section (as of 2026-09-16). It's
authored on `DEV` and pulled onto `RATSNEST` via its own read-only
GitHub deploy key `bdrpisrvdungeon_to_bdratsnestgit` (generated on the
`RATSNEST` box itself, registered on the private `bDotRad/BdRatsNest`
repo — a new key, doesn't replace anything).

**TLS revert: deployed.** `BdRatsNest`'s brief in-process TLS
(2026-09-18, reverted in `7cb48de`) is gone from the box. As of
2026-09-27 it runs as `bdratsnest.service` on plain HTTP
`127.0.0.1:8440` (checkout at `3d17cfa`) behind `tailscale serve`
`:8441`. The nginx/LAN side of the `HTTPS.md` migration is still open
in the `BdRPiSrvDungeon` repo's `rHTTPSStandardAdopt.md`.

### `BIRD` — `BdRBirdDetector`

Runs the edge detection pipeline (`edge/` in the `BdRBirdDetector` repo).
Pull-only from GitHub, pushes to Firebase. No Claude Code on the box.
**Unreachable from the rest of the fleet** — foreign subnet
(`192.168.1.0/24`), not on the tailnet.

### `HA` — Home Assistant Green (being retired)

| what | handle | URL(s) | status |
|---|---|---|---|
| Home Assistant | — | `http://ratsnest.local:8123` | live — **being retired** |

A Home Assistant Green appliance running Home Assistant OS — not a Pi
BdRDev provisioned, no Claude Code, no repo/project of its own. Not on
the tailnet; reachable on the LAN at `10.10.10.100` / `ratsnest.local`.
Being made redundant by `BdRatsNest` on `RATSNEST`, then given to
Brad's parents — at that point drop its row from Supabase and here.
Its device hostname `ratsnest` is an alias now; "RatsNest" means the
`RATSNEST` Pi.

## SSH matrix

| from → to | command | headless? | notes |
|---|---|---|---|
| `DEV` → `AMI` | `ssh BdRPiAMI` (`bdr@10.10.10.20`) | ✅ yes | LAN key `bdrdev_to_bdrpiamiserver`. Use the LAN alias/IP, **not** the `*.ts.net` name. |
| `DEV` → `RATSNEST` | `ssh BdRPiDungeon` (`bdr@10.10.10.30`) | ✅ yes | LAN key `bdrdev_to_bdrpidungeonserver`, same pattern as `AMI`. Use the LAN alias/IP, **not** the `*.ts.net` name. |
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
| `BdRDungeon` | `Dungeon` | `DEV` | `RATSNEST` (planned — server provisioned, app not deployed yet) | `BdRDungeon` | Supabase (planned) |
| `BdRatsNest` | `BdRatsNest` | `DEV` | `RATSNEST` (live, dev server) | `BdRatsNest` | none |
| `BdRBirdDetector` | `Bird` | `DEV` | `BIRD` (pull) | `BdRBirdDetector` | SQLite on box + Firebase |
| `BdRWebGUIDev` | `WebGUI` | `DEV` | `DEV` | `BdRWebGUIDev` | none |
| `BdRPiSrvAMI` | `AMI-cfg` | `DEV` | `AMI` (pull, as `~/projects/BdRPiAMI/`) | `BdRPiSrvAMI` | SQLite `srvhome.db` |
| `BdRPiSrvDungeon` | `RatsNest-cfg` | `DEV` | `RATSNEST` (pull) | `BdRPiSrvDungeon` *(repo name kept)* | none |
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

## Naming note: "RatsNest" (settled 2026-09-27)

- **Box:** `RATSNEST` / `BdRPiSrvRatsNest` — the Pi 5 at `10.10.10.30`
  (formerly `DUNGEON` / `BdRPiSrvDungeon`).
- **Home-automation project:** `BdRatsNest` — name unchanged, confirmed
  with Brad.
- **Dungeon circuits/testing project:** `BdRDungeon` — name unchanged,
  lives on the `RATSNEST` box. "The Dungeon" is the room, not a box.
- **Old appliance:** the Home Assistant Green is handle `HA`, no longer
  `RatsNest`. Being retired and given to Brad's parents.
