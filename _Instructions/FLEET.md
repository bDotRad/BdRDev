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
> Last verified by hand: **2026-09-11** (srvhome moved to the
> `BdRPiSrvAMI` repo; AMI no longer runs a `BdRDev` checkout).

## Boxes

| handle | canonical | host | LAN | tailnet | Claude? | serves `/` |
|---|---|---|---|---|---|---|
| `DEV` | `BdRPiSrvDev` | Raspberry Pi, Ubuntu Server, 8GB | `10.10.8.11` | `bdrpisrvdev.tail0ed3f6.ts.net` / `100.116.147.74` | yes (scheduler + CloudCLI) | BdRDev dashboard |
| `AMI` | `BdRPiSrvAMI` | Raspberry Pi, 8GB | `10.10.10.20` | `bdrpisrvami.tail0ed3f6.ts.net` / `100.86.25.88` | yes | `srvhome` |
| `DUNGEON` | `BdRPiSrvDungeon` | not provisioned | — | — | planned | — |
| `BIRD` | `BdRBirdDetector` | Raspberry Pi, RPi OS Lite, 4GB | `192.168.1.187` | not on tailnet | no | app (`bdrbirddetector.local`) |

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

Not provisioned. Will host `BdRDungeon`.

### `BIRD` — `BdRBirdDetector`

Runs the edge detection pipeline (`edge/` in the `BdRBirdDetector` repo).
Pull-only from GitHub, pushes to Firebase. No Claude Code on the box.
**Unreachable from the rest of the fleet** — foreign subnet
(`192.168.1.0/24`), not on the tailnet.

## SSH matrix

| from → to | command | headless? | notes |
|---|---|---|---|
| `DEV` → `AMI` | `ssh BdRPiAMI` (`bdr@10.10.10.20`) | ✅ yes | LAN key `bdrdev_to_bdrpiamiserver`. Use the LAN alias/IP, **not** the `*.ts.net` name. |
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
| `BdRDungeon` | `Dungeon` | `DEV` | `DUNGEON` (planned) | `BdRDungeon` | Supabase (planned) |
| `BdRBirdDetector` | `Bird` | `DEV` | `BIRD` (pull) | `BdRBirdDetector` | SQLite on box + Firebase |
| `BdRWebGUIDev` | `WebGUI` | `DEV` | `DEV` | `BdRWebGUIDev` | none |
| `BdRPiSrvAMI` | `AMI-cfg` | `DEV` | `AMI` (pull, as `~/projects/BdRPiAMI/`) | `BdRPiSrvAMI` | SQLite `srvhome.db` |
| `BdRVSrvDev` | `DEV-cfg` | `DEV` | `DEV` | *(check repo)* | none |
| `BdRImpSys` | `ImpSys` | `DEV` | `AMI` (checkout only) | `BdRImpSys` | none yet |

## Known drift to reconcile (2026-09-08)

The Supabase data is behind reality in at least these spots — fix as part
of the next request that touches them:

- `projects.BdRIS` has `exists_flag = false`, but `~/projects/BdRImpSys`
  exists on `AMI`. Rename the row to `BdRImpSys`, set `exists_flag`.
- `projects.BdRDungeon.runs_on_server_id` is `null` despite
  `BdRPiSrvDungeon` (`servers.id 59`) existing. Point it there.
- `servers` has no column for **what each box serves at `/`** or for the
  **handle** — both are only in this file / `Naming.md` until the
  `rFleetMap` schema change lands.
- `fleet_meta.notes` is a stale prose blob (mentions the retired
  `192.168.100.x` VM, "hostname still BdRDev", etc.). Replace with a
  short pointer to this file.
