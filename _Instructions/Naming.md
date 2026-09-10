# Naming canon — one name per thing

Fleet-wide layer (see [`Standards.md`](Standards.md)). Written 2026-09-08
after a run of incidents traced to name confusion — a session on the AMI
box tore down `srvhome` because it couldn't tell "the AMI box page" from
"the BdRAMAssist app", and the Ecosystem page drifted because nobody knew
which of five names for a box was the real one.

## The rule

Every box and every project has **exactly one canonical name** and **one
short handle**. Everything else is an alias. In new writing — docs,
request files, commit messages, `_Requests/` titles, code comments — use
the **canonical name** (or the handle where brevity matters, e.g. a table
header or a chat sentence). **Never use an alias in new writing.** If you
see an alias in existing text you're editing, fix it.

Repository directory names and GitHub repo names do **not** change —
`~/projects/BdRDev`, `github.com/bDotRad/BdRDev` stay as they are.
Renaming those (plus SSH keys and systemd units) is a separate, deferred
piece of work. This doc is about what to *call* things in prose and data.

## Boxes

| handle | canonical | machine hostname | LAN | tailnet | aliases — DO NOT use |
|---|---|---|---|---|---|
| `DEV` | `BdRPiSrvDev` | `bdrpisrvdev` | `10.10.8.11` | `bdrpisrvdev.tail0ed3f6.ts.net` / `100.116.147.74` | BdRDev *(as a host)*, BdRVSrvDev, BdRSrvDev, "the dev box", `bdrdev.local` |
| `AMI` | `BdRPiSrvAMI` | `BdRPiSrvAMI` | `10.10.10.20` | `bdrpisrvami.tail0ed3f6.ts.net` / `100.86.25.88` | BdRPiAMI *(SSH alias only — see note)*, BdRSrvAMI, PlanBdRadServer, "the Pi", `bdrpiami.local` |
| `DUNGEON` | `BdRPiSrvDungeon` | *(not provisioned)* | — | — | BdRSrvDungeon |
| `BIRD` | `BdRBirdDetector` | `bdrbirddetector` | `192.168.1.187` | *(not on tailnet)* | BdRadBirdDetector, "the bird pi" |

`BdRPiAMI` survives in exactly two places for historical reasons and
nowhere else: the `~/.ssh/config` alias on DEV (`ssh BdRPiAMI`) and the
directory name `~/projects/BdRPiAMI/` on the AMI box. Don't propagate it.

## Projects

Canonical = the repo directory name. Handle is for tables and prose.

| handle | canonical repo | what it is | runs on |
|---|---|---|---|
| `DEV` | `BdRDev` | fleet dashboard + round-robin scheduler + this `_Instructions/` standards layer | `DEV` |
| `AMAssist` | `BdRAMAssist` | bulk asset-management data prep, feeds PlanBdR | `AMI` |
| `PlanBdR` | `PlanBdRad` | preventative-maintenance plan generator | `AMI` |
| `Dungeon` | `BdRDungeon` | "the Dungeon" hub — talks to ESP32 field devices | `DUNGEON` *(planned)* |
| `Bird` | `BdRBirdDetector` | distributed acoustic bird detection / localization | `BIRD` |
| `WebGUI` | `BdRWebGUIDev` | one-page web-GUI sandbox, dev only | `DEV` |
| `AMI-cfg` | `BdRPiSrvAMI` | server-config repo for the AMI box (nginx / TLS / provisioning) + **the canonical home of `srvhome`** (`srvhome/`) | `AMI` (pull-only) |
| `DEV-cfg` | `BdRVSrvDev` | server-config repo for the DEV box (nginx / TLS / tailnet front door / CloudCLI) | `DEV` |
| `ImpSys` | `BdRImpSys` | improvement-tracking system — nascent, only a checkout on `AMI` so far | `AMI` *(planned)* |
| `CloudCLI` | *(third-party, no repo)* | `@cloudcli-ai/cloudcli` — Claude Code web UI | `DEV` |

Aliases to never use in new writing: `BdRIS` → `ImpSys`/`BdRImpSys`;
`BdRAMI` → `AMI-cfg`/`BdRPiSrvAMI`; "bdr AM Assist", "Plan BdRad" and the
other `nickname` strings (those are **display-only** labels for the web
pages — never reference them in prose or data lookups).

## Special terms

- **`srvhome`** — the per-box status page served at `/` on an app host
  (currently only `AMI`). Canonical source is the **`BdRPiSrvAMI` repo,
  `srvhome/`** (moved out of `BdRDev/fleet/srvhome/` on 2026-09-11 — the
  AMI box runs it from its own config-repo checkout, not a BdRDev one).
  It is **not an app** and not tied to any one project; it reports on all
  of them. "The AMI box page" = `srvhome` on `AMI`. Do not call it "the
  AMI page", "the main page", or confuse it with `AMAssist`.
- **`/` on a box** — always means the status/control page for that box
  (`DEV` → the BdRDev dashboard, `AMI` → `srvhome`), never an
  application. Apps are only ever at their own hostname/port.
- **ecosystem** — the fleet data (boxes + projects + what runs where),
  stored in the self-hosted Supabase on `DEV` (`fleet_meta`, `servers`,
  `projects`, `project_roles`, `server_software`). `DEV` is the
  ecosystem master. `BdRDev/state/ecosystem.json` is a **read cache
  only** — never the source of truth, never hand-edited.
