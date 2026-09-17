READY

## Issue

The rat-logo browser-tab favicon isn't a documented fleet standard, and
isn't applied consistently. Found while working in `BdRPiSrvDungeon`
(session there, 2026-09-17).

`WebUI.md` documents the in-page header logo (`.sh-logo` /
`<img src="/static/rat-logo.png">`) but never mentions a `<link
rel="icon">` favicon at all.

Checked every project's `<head>` for `<link rel="icon">`:

| project | favicon link |
|---|---|
| BdRDev | present |
| BdRAMAssist | present |
| PlanBdRad | present |
| BdRatsNest | present |
| BdRWebGUIDev | **missing** |
| srvhome (AMI's copy, `BdRPiSrvAMI/srvhome/srvhome.py`) | **missing** |
| srvhome (Dungeon's copy) | was missing — already fixed locally, see below |
| srvhome origin (`BdRDev/fleet/srvhome/`, per its own README history) | **missing** (same code as AMI's copy) |

So it caught on ad hoc in a few app templates that happened to copy
BdRDev's `<head>`, but never made it into `srvhome.py` even though
srvhome already ships `rat-logo.png` and serves it for the header.

## Already done (in `BdRPiSrvDungeon`, not this repo)

Added `<link rel=icon type=image/png href=logo.png>` to
`srvhome/srvhome.py`'s `render_html()` `<head>` (srvhome already routes
`/logo.png` → `rat-logo.png`). Commit `97e75fd`, pushed. Not this
repo's job to touch further.

## Solution (this repo's part)

1. Add a short favicon rule to `WebUI.md` (near the existing logo
   section) — every fleet web UI links `rat-logo.png` as
   `<link rel="icon">`, not just the header image.
2. Apply the same one-line fix as Dungeon's to the origin copy,
   `BdRDev/fleet/srvhome/srvhome.py`.
3. Apply it to `BdRPiSrvAMI/srvhome/srvhome.py` too (separate repo —
   author there / push from DEV the normal way).
4. `BdRWebGUIDev` is missing it as well; lower priority (it's a
   showcase/sandbox, not a fleet-facing app) but worth a one-liner if
   touching the others anyway.
