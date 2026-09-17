# Favicon standard — processed 2026-09-17

## What was done

Checked each item in the original request against current repo state
before touching anything:

- **`BdRDev/fleet/srvhome/`** — doesn't exist anymore. It was removed
  2026-09-11 when srvhome ownership moved to `bDotRad/BdRPiSrvAMI`
  (`BdRDev` commit `1f60164`, see
  [[srvhome-owned-by-bdrpisrvami]]). So item 2 of the request (apply
  the favicon fix to `BdRDev/fleet/srvhome/srvhome.py`) is moot — there's
  nothing left there to fix.
- **`BdRPiSrvAMI/srvhome/srvhome.py`** — already has the favicon link
  (`<link rel=icon type=image/png href=logo.png>`, line ~1641). Landed
  separately as `BdRPiSrvAMI` commit `59f245e` ("srvhome: set browser
  tab favicon to the rat logo") before this pass started. Item 3 done.
- **`BdRWebGUIDev/app/templates/index.html`** — already has
  `<link rel="icon" type="image/png" href="/static/rat-logo.png">` at
  line 7. Item 4 done.
- **`BdRDev/app/templates/index.html`** — already had it (matches the
  original request's table, which listed BdRDev as "present").

So the only outstanding piece from this repo's side was item 1: the doc
rule itself never existed. Added a **Favicon** subsection to
`_Instructions/WebUI.md`, right after the "Standard header block" /
graceful-degradation section, stating the fleet-wide rule: every web UI
links `rat-logo.png` as `<link rel="icon">` in `<head>`, not just the
in-page header image, with the reference markup and a note that the
path/route varies per app (e.g. srvhome serves it at `/logo.png`).

No fleet ecosystem/deployment facts changed (no new URL, port, box, or
service), so no Supabase/`FLEET.md` update was needed.

**Commit:** `56833f2` — "WebUI.md: document the rat-logo favicon as a
fleet-wide standard" — committed and pushed from DEV.

Dungeon's own fix (`srvhome/srvhome.py` there, commit `97e75fd`) was
already done before this request landed, per the request's own "Already
done" section — not touched further, as noted in the original ask.

## Original request (verbatim)

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
