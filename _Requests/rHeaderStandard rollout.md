WAITING RESPONSE

<!-- Brad asked "is this all done?" — almost. Tasks 1/2/4/5 done, Task 2
     verified live. Only Task 3 (deploy srvhome to BdRPiSrvAMI) is left,
     and it's on the AMI Pi, unreachable from this dev box. Action block
     is in the "Restarts" section below. Set back to WAITING RESPONSE
     because that srvhome deploy is a Brad step. -->

<!-- ─────────────────────────────────────────────────────────────────
     2026-09-07: code for tasks 1–5 done, committed + pushed
     (BdRDev afc280a). srvhome deploy to BdRPiSrvAMI remains — Action
     block below. Archive once that's done and verified.
     (An earlier 13:47 pass had stopped without editing because the
     working tree held ~820 lines of unrelated uncommitted WIP; Brad
     committed that as 1fb5a13 and confirmed the standard block should
     replace whatever header each app has — including srvhome's
     .selfbar. Work then proceeded from the clean tree.) -->

## What was done (BdRDev commit `afc280a`, pushed)

**Task 1 — `_Instructions/WebUI.md`:**
- New `## Standard header block` section: LV-G description (three lines),
  reference markup, reference CSS (`sh-*`), status-pill behaviour,
  graceful-degradation rule. Points at BdRWebGUIDev Templates → Logo &
  Version for the explorations; names the BdRDev dashboard header as the
  degraded-form reference and srvhome as the full-form reference.
- Versioning section rewritten: 7-char SHA stays canonical; where the
  standard header is rendered the version line *displays* as
  `YYYY.MM.DD_HHMM · <7-char-SHA>`; footer may stay SHA-only.

**Task 2 — BdRDev dashboard (`app/templates/index.html`, `app/common.py`):**
- `#header-row` (logo + `<h1>BdR AI GUI</h1>` + `#site-version`) →
  `.site-header` standard block, **degraded form** (no status line — the
  dashboard has no version check). Name `BDR AI GUI` (`BDR` white).
- `common.app_version()` now returns the display format
  `YYYY.MM.DD_HHMM · <7-char-SHA>` (was `yymmdd_hhmmss <hash>`). It's
  the only caller of that helper. Verified via a local Jinja render:
  `2026.09.07_1358 · 1fb5a13`.

**Task 3 — srvhome (`fleet/srvhome/srvhome.py`):**
- `render_selfbar()` → `render_site_header()`: the standard block, **full
  three-line form** (srvhome has the running-vs-origin check). Pill =
  the "re-check GitHub" button, wired to the existing
  `POST /api/check {app:"srvhome"}`; `.behind` toggles amber; poll JS
  (`applyHeader`) keeps it live.
- **Deviation from the reference:** the second status chip is `running`
  (the SHA the live process started from, frozen at boot via
  `running_sha()`), not `built` — srvhome has no build step. It goes
  amber if HEAD drifts ahead of the running process (pull without
  restart). Recorded in `srvhome/DEPLOY-STATUS.md` + `README.md`, not
  forked back into WebUI.md.
- Logo: new `GET /logo.png` route serving the checkout's own
  `app/static/rat-logo.png`; degrades to no-logo when srvhome is a
  loose file copy. `sh-*` CSS ported into `PAGE_CSS` mapped to
  srvhome's literal palette.
- Smoke-tested locally: `GET /` renders the header, `/logo.png` +
  `/status/logo.png` serve the PNG, `POST /api/check {app:"srvhome"}`
  returns `self.behind`, `APPS_SCRIPT` passes `node --check`.

**Task 4 — fan-out markers flipped to `READY`** (their own schedulers
pick the work up; not edited from here):
- `BdRWebGUIDev/_Requests/rHeaderAdoptLVG.md`
- `PlanBdRad/_Requests/rAdoptStandardHeader.md`
- `BdRAMAssist/_Requests/rAdoptStandardHeader.md`

**Task 5 —** srvhome `DEPLOY-STATUS.md` + `README.md` header
descriptions updated to the new block. `apps.json` identity blocks
didn't reference the old header, so no change there.

## Restarts

**Task 2 — DONE & verified 2026-09-07 ~15:1x.** The dashboard was
restarted (admin "restart" button, 14:33) and now serves the new
header: `https://bdrpisrvdev.tail0ed3f6.ts.net/` shows
`class="site-header"`, `<b>BDR</b> AI GUI`, `sh-ver">2026.09.07_1411 ·
a687054`. NB the dashboard is on **plain 443 now** (the nginx/TLS rework
in `1fb5a13`), not `:8444` — that port has nothing listening and `:8443`
is CloudCLI UI. If you still want a `:8444` listener that's a separate
nginx-config question (`nginx/bdrdev.conf` only defines 80/443 now).

**Task 3 — still needs deploying to BdRPiSrvAMI:**

@@@ --- Action --- @@@

1. Deploy the srvhome change to BdRPiSrvAMI  # runs on the Pi, via SSH

"Pull the new srvhome code on the app server (it tracks BdRDev)"
cd ~/projects/BdRPiSrvAMI && git pull --ff-only

"Restart srvhome however it's run there (systemd unit name may differ)"
sudo systemctl restart srvhome

"Confirm the standard header + logo route respond"
curl -s http://localhost:8610/status/ | grep -o 'data-role=siteheader\|id=shPill'
curl -sI http://localhost:8610/status/logo.png | head -1

   NB: DEPLOY-STATUS.md says the current Pi srvhome may still be a *loose
   file copy* (not a checkout). If so: the header degrades gracefully
   (logo + `SRVHOME` + "loose file copy… version not tracked") and step
   2's `git pull` doesn't apply — copy the files the usual way, or
   redeploy srvhome as a read-only BdRDev checkout per DEPLOY-STATUS.md
   to light up the full three-line form.

@@@ ------------- @@@

Once both restarts are done and the header looks right, archive this
(`_Archive/`, commit, push). If the dashboard or srvhome header renders
wrong, flip back to `READY` with a note.

---

# Standard header block — promote LV-G to WebUI.md and roll it out

## Background

`BdRWebGUIDev/_Requests/rHeaderStandard.md` (the "chooser" request, now
archived there) built seven combined logo + app-name + version header
variations on the BdRWebGUIDev showcase page, under **Templates → Logo &
Version** (`#t2-logover`). **Brad picked `LV-G`.**

This request is the follow-up that request named: promote `LV-G` into
`_Instructions/WebUI.md` as the fleet standard header block, then make
the apps render it.

Nothing is shared as code between projects (`Standards.md`: Layer-1
conventions live here only, each app implements them against its own
palette vars / logo / `{{ version }}` wiring). So the canonical copy of
the header block is a spec + reference markup **in `WebUI.md`**, the
same way the Edit/Save/Cancel table pattern is documented there. When
the header needs to change fleet-wide in future, edit that block in
`WebUI.md` and re-run a rollout like this one.

## What LV-G is

Bigger (64px) circular B&W logo on the left, then a stacked block:

1. **App name** — the app's short/nick name, UPPERCASED, letter-spaced,
   bold ~28px. First word in `--text` (white), the rest in muted
   blue-grey `#7f97b8`. (e.g. `BDR WEB GUI DEV`, `BDR AI GUI`.)
2. **Version line** — monospace ~14px, `#c7d0dc` (white-grey), format
   `YYYY.MM.DD_HHMM · <7-char-SHA>` (local build timestamp, ` · `
   separator, 7-char short commit SHA). Turns amber (`--pending`) when
   the running build is behind the repo.
3. **Deploy-status line** (indented under the version) — **only where
   the app has srvhome-style version checking**; see "Graceful
   degradation" below. A pill (`up to date` green / `behind by N`
   amber) that *is* the "re-check GitHub" button, plus two chips
   `HEAD <sha>` and `built <sha>` — green when the two SHAs match,
   amber when they don't.

### Reference markup (from BdRWebGUIDev `index.html`, LV-G demo)

```html
<div class="site-header" id="siteHeader">
  <img class="sh-logo" src="/static/rat-logo.png" alt="">
  <div class="sh-stack">
    <span class="sh-name"><b>BDR</b> AI GUI</span>
    <span class="sh-ver">2026.09.07_0923 · 0ab1809</span>
    <!-- status line: omit entirely if the app has no version check -->
    <div class="sh-status">
      <button class="sh-pill" id="shPill" title="Re-check GitHub">up&nbsp;to&nbsp;date</button>
      <span class="sh-chip">HEAD <b>0ab1809</b></span>
      <span class="sh-chip">built <b>0ab1809</b></span>
    </div>
  </div>
</div>
```

### Reference CSS (rename the `lvg-*` classes to `sh-*`; palette vars already fleet-standard)

```css
.site-header { display: flex; align-items: center; gap: 16px; }
.sh-logo { width: 64px; height: 64px; border-radius: 50%; object-fit: cover; flex-shrink: 0; }
.sh-stack { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.sh-name {
  font-weight: 800; font-size: 28px; line-height: 1; letter-spacing: 0.04em;
  color: #7f97b8;
}
.sh-name b { color: var(--text); font-weight: 800; }
.sh-ver {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 14px; color: #c7d0dc; margin-left: 2px;
}
.site-header.behind .sh-ver { color: var(--pending); }
.sh-status { display: flex; align-items: center; gap: 8px; margin-left: 4px; flex-wrap: wrap; }
.sh-pill {
  font: inherit; font-size: 11px; font-weight: 700; line-height: 1.4;
  cursor: pointer; border: none; border-radius: 5px; padding: 1px 8px;
  color: #0f1115; background: var(--good);
}
.sh-pill.busy { background: var(--pending); cursor: default; }
.sh-pill:hover { filter: brightness(1.08); }
.site-header.behind .sh-pill { background: var(--pending); }
.sh-chip {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px; color: var(--text-dim);
  border: 1px solid var(--card-border); border-radius: 5px; padding: 1px 7px;
}
.sh-chip b { font-weight: 700; color: var(--good); }
.site-header.behind .sh-chip b { color: var(--pending); }
```

### Behaviour of the status pill

Clicking `.sh-pill` re-runs the version check (in the BdRWebGUIDev demo
it's a mock that toggles between the two states). Real implementation:
hit the app's own "compare running SHA to origin" endpoint, add/remove
`.behind` on `.site-header`, set the pill text to `up to date` /
`behind by N`, and update the `HEAD` chip's SHA. srvhome
(`fleet/srvhome/srvhome.py`) already does this comparison server-side —
reuse that pattern.

## Graceful degradation

The deploy-status line **couples the header to srvhome-style
version-checking, which only srvhome does today.** So:

- Apps **with** a running-vs-origin check (srvhome; any app that adds
  one): render all three lines.
- Apps **without** one (BdRDev dashboard, BdRWebGUIDev, BdRAMAssist
  today): render **logo + name + version only** — drop the
  `.sh-status` div entirely. The version line still goes amber if the
  app has any other way to know it's behind; otherwise it stays
  white-grey.

Building the check into each app is out of scope here — that's a
per-app follow-up if Brad wants the status line everywhere.

## Tasks

1. **`_Instructions/WebUI.md`:**
   - Update the **Versioning** section: the 7-char SHA is still the
     canonical version identifier, but where an app renders the
     standard header block the version is *displayed* as
     `YYYY.MM.DD_HHMM · <7-char-SHA>` (build timestamp + SHA). Footer
     may stay SHA-only.
   - Add a **`## Standard header block`** section: the LV-G spec above
     (description + reference markup + CSS + status-pill behaviour +
     graceful-degradation rule). Point at BdRWebGUIDev **Templates →
     Logo & Version** as where the seven explorations live and LV-G is
     the chosen one, and name the BdRDev dashboard header as the
     reference implementation once task 2 lands.
2. **BdRDev dashboard** (`app/templates/index.html`): replace the
   current `#header-row` (logo + `<h1>BdR AI GUI</h1>` + `#site-version`)
   with the standard block, degraded form (no status line — the
   dashboard has no version check). Keep `{{ version }}` as the SHA;
   the build-timestamp half can be blank or `git log -1 --format=%cd`
   formatted if easy, otherwise just show the SHA for now and note it.
   Restart + curl-check.
3. **srvhome** (`fleet/srvhome/srvhome.py`, in this repo): swap its
   `header h1` + `.selfbar` block to the standard block — **full form
   with the status line**, since srvhome already does the
   running-vs-origin check (`app_state()` / the version-check +
   one-click-update code). This is the reference implementation for the
   three-line form. srvhome's inline CSS is a Python string — port the
   `sh-*` rules into it, mapping the palette to srvhome's existing
   colours. Restart srvhome + check.
4. **Fan out to the other web apps.** Once tasks 1–3 are committed and
   pushed, this is what "roll it out everywhere" means — each app is
   updated by its **own** scheduled session working in its **own**
   repo, triggered by a `READY` item in that repo's `_Requests/`. From
   this session (the dev box sees every checkout), drop / flip these:
   - `BdRWebGUIDev/_Requests/rHeaderAdoptLVG.md` — already staged
     `NOT READY`; flip its first line to `READY`.
   - `PlanBdRad/_Requests/rAdoptStandardHeader.md` — already staged
     `NOT READY`; flip to `READY`. (React/Vite/Tailwind SPA — header is
     a component; it already renders `__BUILD_VERSION__ · __GIT_HASH__`,
     so it's mostly logo + name styling. Deploys on BdRPiSrvAMI,
     pull-only — the change is built + pushed from here, the Pi pulls.)
   - `BdRAMAssist/_Requests/rAdoptStandardHeader.md` — already staged
     `NOT READY`; flip to `READY`. (Same stack as PlanBdRad; its
     `App.tsx` top bar already has the uppercase name + yellow mono
     `{__BUILD_VERSION__} · {__GIT_HASH__}` — needs the 64px logo and
     the first-word-white name treatment.)
   Don't edit those apps' code from this session — just flip the
   markers so their own schedulers pick the work up. Keep the SPA
   deviations (Tailwind classes instead of the reference CSS, no
   `rat-logo.png` if they use their own asset) recorded in each app's
   own docs per `Standards.md`, not forked back into `WebUI.md`.
5. Update the **fleet ecosystem / srvhome `apps.json`** notes if any
   app's identity block description references the old header. Optional.

## Notes / decisions already made

- Brad's pick is **LV-G**, not LV-A (LV-A was his earlier stated
  favourite from the first six; he then asked for LV-G and picked it).
- App name is the **short/nick name**, uppercased — `BDR AI GUI` for
  the dashboard, `BDR WEB GUI DEV` for the showcase.
- Logo asset is `rat-logo.png` served at `/static/rat-logo.png`
  (already present in BdRDev and now BdRWebGUIDev).
