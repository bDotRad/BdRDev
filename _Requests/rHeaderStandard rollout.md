WAITING RESPONSE

<!-- ─────────────────────────────────────────────────────────────────
     2026-09-07 13:47 — unattended session, could not start safely.
     Blocked on the state of the BdRDev working tree. Details below;
     original request text is intact underneath. -->

## Why this pass didn't touch anything

The BdRDev checkout has a large pile of **uncommitted, unrelated
work-in-progress** — ~820 changed lines across 17 tracked files plus a
new untracked `tls/` dir. `origin/master..master` is empty, so none of
it is on GitHub; it's all live in the working tree, dating from Sep 4–6
(and `app/templates/index.html` was modified today at 13:21, i.e. after
this session's tmux was created at 13:45 — a second Claude session,
`proj-_IndependentClaude`, has been running since 13:07 and may still be
editing these files).

The three files this request has to edit are **all** in that pile:

- `_Instructions/WebUI.md` — has an uncommitted new "Import / export"
  section + a "Confirm destructive saves" note.
- `app/templates/index.html` — uncommitted `ecoFallbackReason` plumbing.
- `fleet/srvhome/srvhome.py` — **+412 uncommitted lines**: an
  in-progress "srvhome tracks its own version" feature that *adds* the
  `header .selfbar` block. Task 3 says to *replace* `header h1` +
  `.selfbar` with the standard block — i.e. this request and that
  unfinished feature collide directly in the same code region.

Given that, I can't:

1. **Commit tasks 1–3 in isolation.** `_Instructions/Requests.md`
   requires commit + push before a request is done, and Task 4 of this
   request is explicitly gated on "tasks 1–3 are committed and pushed."
   `git add <file>` stages the whole file, so any commit here sweeps the
   unrelated WIP into a "HeaderStandard rollout" commit. `git add -p` /
   interactive staging isn't available in this environment.
2. **Safely rewrite the srvhome header region** while an unfinished
   self-versioning feature is mid-flight in that exact block and may be
   getting actively edited by the other session.
3. **Verify Task 2** — swapping the live dashboard header needs a
   `sudo systemctl restart bdrdev-dashboard` (no passwordless sudo here;
   `kill -9` is blocked by the unattended safety classifier), so I can't
   restart + curl-check as the task requires.

So this pass made **zero edits** rather than add a fourth layer to an
already-tangled tree that a later session would have to untangle.

??? --- Question --- ???

How do you want the uncommitted BdRDev working-tree WIP handled so this
request can proceed?

Options:
1. **(recommended)** You (or the other session) commit + push the
   existing WIP — the srvhome self-versioning feature, the eco
   fallback-reason plumbing, the WebUI.md import/export section, the
   SSH/nginx/TLS doc edits, the `tls/` dir. Then flip this file's first
   line back to `READY` and a fresh session starts from a clean tree.
   Note: if the srvhome self-versioning feature lands first, Task 3's
   "replace `header h1` + `.selfbar`" needs re-reading against the new
   `.selfbar` block — the standard 3-line header and that feature's
   self-status bar overlap and someone should decide whether the
   standard block subsumes it or sits alongside it.
2. Tell me the WIP is abandoned / safe to discard, and I'll
   `git checkout -- .` + remove `tls/` before starting. (Only if you're
   sure — it's days of work and spans srvhome, the dashboard and docs.)
3. Tell me to proceed and fold the header changes into the same big
   uncommitted blob, committing **everything** together under one
   commit. Task 2's dashboard restart still needs your sudo either way.
4. Narrow this request — e.g. do only Task 1 (the `WebUI.md` spec
   section) now. Still sweeps the uncommitted WebUI.md import/export
   section into that commit, so this only helps if you're fine with
   that content shipping too.

Answer:
<Brad writes here>

??? --------------- ???

When this is unblocked, Task 2 will also need (after the code change):

@@@ --- Action --- @@@

1. Pick up the new dashboard template on the live service

"Restart the dashboard so the new header markup/CSS loads (no
autoreload; debug=False)"
sudo systemctl restart bdrdev-dashboard

"Confirm the standard header rendered"
curl -s http://localhost:8501/ | grep -A6 'site-header'

@@@ ------------- @@@

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
