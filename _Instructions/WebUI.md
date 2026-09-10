# Web UI standard (fleet-wide)

Generic look-and-feel and interaction rules for **every** web app on the
fleet (BdRDev dashboard, PlanBdRad, BdRAMAssist, BdRDungeon, …). This is
the **top layer** — see [`Standards.md`](Standards.md) for how the
two-layer doc system works. A project only documents where it
*deviates*; if its `CLAUDE.md` / `_Instructions/` say nothing, these
rules apply.

## Versioning

- The **version** of a running app is the **7-character short commit
  SHA** of its deployed checkout. That SHA is the canonical version
  identifier — no separate version strings, tags, or `VERSION` files.
- **How it's displayed:**
  - Where an app renders the [standard header block](#standard-header-block),
    the version line shows the SHA prefixed with the local build
    timestamp: `YYYY.MM.DD_HHMM · <7-char-SHA>` — build time, a ` · `
    separator, then the 7-char SHA. It turns amber when the running
    build is behind the repo.
  - A **footer** version line may stay SHA-only.
  - Rendered small and un-emphasised either way.
- Where an app records deploy history (e.g. `srvhome`), a "version" in
  that history is the same 7-char SHA, shown with the deploy timestamp,
  commit title and commit description.

## Standard header block

Every web app on the fleet renders the same header: a big circular B&W
logo on the left, then a stacked block of app name + version (+ an
optional deploy-status line). This is the `LV-G` variant — the seven
combined logo/name/version explorations that led to it live on the
**BdRWebGUIDev showcase → Templates → Logo & Version** (`#t2-logover`);
`LV-G` is the one Brad picked. The **BdRDev dashboard** header
(`app/templates/index.html`, `.site-header`) is the reference
implementation of the degraded (two-line) form; **`srvhome`**
(`srvhome/srvhome.py`, `render_site_header`, in the sibling
`BdRPiSrvAMI` repo — checked out at `~/projects/BdRPiSrvAMI/` on `DEV`)
is the reference for the full three-line form. The canonical markup +
CSS live below either way.

Nothing is shared as code between projects (see [`Standards.md`](Standards.md)):
each app ports the markup + CSS below against its own palette vars, its
own logo asset and its own `version` wiring. When the header needs to
change fleet-wide, edit this section and re-run a rollout.

### The three lines

1. **App name** — the app's short / nick name, UPPERCASED, letter-spaced,
   bold ~28px. The **first word** is in `--text` (white); the rest is
   muted blue-grey `#7f97b8`. E.g. `BDR WEB GUI DEV`, `BDR AI GUI`.
2. **Version line** — monospace ~14px, `#c7d0dc` (white-grey), format
   `YYYY.MM.DD_HHMM · <7-char-SHA>` (local build timestamp · 7-char
   short commit SHA). Turns amber (`--pending`) when the running build
   is behind the repo.
3. **Deploy-status line** (indented under the version) — **only where the
   app has a running-vs-origin version check** (see graceful degradation
   below). A pill (`up to date` green / `behind by N` amber) that *is*
   the "re-check GitHub" button, followed by two mono chips `HEAD <sha>`
   and `built <sha>` — green when the two SHAs match, amber when they
   don't.

### Reference markup

```html
<div class="site-header" id="siteHeader">
  <img class="sh-logo" src="/static/rat-logo.png" alt="">
  <div class="sh-stack">
    <span class="sh-name"><b>BDR</b> AI GUI</span>
    <span class="sh-ver">2026.09.07_0923 · 0ab1809</span>
    <!-- status line: omit this div entirely if the app has no version check -->
    <div class="sh-status">
      <button class="sh-pill" id="shPill" title="Re-check GitHub">up&nbsp;to&nbsp;date</button>
      <span class="sh-chip">HEAD <b>0ab1809</b></span>
      <span class="sh-chip">built <b>0ab1809</b></span>
    </div>
  </div>
</div>
```

### Reference CSS

Palette vars are already fleet-standard (`--text`, `--text-dim`,
`--card-border`, plus `--good`/`--pending` — map to whatever the app
calls its green/amber, e.g. the BdRDev dashboard's
`--processing`/`--waiting`). SPA apps may use their utility classes
instead of this CSS verbatim — record that deviation in the app's own
docs, don't fork it back here.

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

### Status-pill behaviour

Clicking `.sh-pill` re-runs the app's own "compare running SHA to
origin" check, then: add / remove `.behind` on `.site-header`, set the
pill text to `up to date` / `behind by N`, and update the `HEAD` chip's
SHA. While the check is in flight give the pill `.busy` and text
`checking…`. `srvhome` (`srvhome/srvhome.py` in the `BdRPiSrvAMI` repo)
already does this comparison server-side (`check_one()` / `app_state()`)
— reuse that pattern rather than inventing a new endpoint.

### Graceful degradation

The deploy-status line couples the header to srvhome-style
version-checking, which not every app has. So:

- Apps **with** a running-vs-origin check (`srvhome`; any app that adds
  one): render all three lines.
- Apps **without** one (BdRDev dashboard, BdRWebGUIDev, BdRAMAssist
  today): render **logo + name + version only** — drop the `.sh-status`
  div entirely. The version line still goes amber if the app has any
  other way to know it's behind; otherwise it stays white-grey.

Building the check into an app that lacks one is a per-app follow-up,
not part of adopting the header.

## Editing tables — the standard pattern

Any table whose cells are user-editable follows this, exactly:

1. **Read-only by default.** On load the table is not editable — no
   `contenteditable`, no click-to-toggle, nothing changes on stray
   clicks. A single **`Edit`** button sits below (or above) the table.
2. **Enter edit mode** by pressing `Edit`. Now:
   - cells become editable in place (text cells `contenteditable`,
     boolean cells click-to-toggle),
   - the `Edit` button is **replaced by** a **`Save`** button and a
     **`Cancel`** button,
   - an "unsaved changes" hint may appear once something is changed.
3. **`Save`** persists the changes, then returns the table to read-only
   (Save/Cancel go away, `Edit` comes back). Show a brief confirmation
   ("Saved", and to where).
4. **`Cancel`** discards all in-mode edits (re-render from the last
   loaded data), then returns to read-only.

Notes:
- Derived / computed columns stay non-editable in both modes.
- Don't auto-save on blur and don't save per-cell — one explicit `Save`.
- **Confirm destructive saves.** A plain `Save` (edited values, added
  rows) persists straight away. But if the pending save would **delete
  rows, clear populated fields, or overwrite existing data on import**,
  `Save` first shows an "Are you sure?" confirmation naming what will be
  lost ("This removes 3 rows and clears 'notes' on 2 more — save?").
  Confirm proceeds; cancel returns to edit mode with the changes intact.
  Non-destructive saves never prompt.
- The same three words — **Edit / Save / Cancel** — everywhere. Not
  "Edit cells" / "Save changes" / "Revert".
- The `Edit` button goes **top-right of the table**, on the same row as
  the table's heading.
- **Multiple grids on one page that save together** share a single edit
  session: one `Edit` (on the first grid) puts every grid into edit mode
  at once, `Save` / `Cancel` are mirrored on each grid's header while
  editing, and one `Save` persists all grids in a single request.

Reference implementation: the **Ecosystem** tab in the BdRDev dashboard
(`app/templates/index.html`, `ecoEnterEdit` / `ecoCancelEdit` /
`ecoSave` / `ecoRenderActions`) — two grids (Servers, Projects), one
shared edit session, persisted to Supabase via `POST /api/ecosystem`
with a `state/ecosystem.json` fallback.

## Import / export

Any tab or view that offers a data download ("Export") or upload
("Import") follows this:

- **Export filename:**
  `<App>_<Tab or dataset name>_<YYMMDD>_<HHmm>.<ext>`
  - `<App>` — the app's short name (`BdRDev`, `PlanBdRad`, …).
  - `<Tab or dataset name>` — what's being exported (`Ecosystem`,
    `Servers`, `Projects`, …). Keep it to one token; no spaces.
  - `<YYMMDD>_<HHmm>` — local time the file was generated, 24-hour, zero
    padded. E.g. `260906_1430` for 2026-09-06 14:30. This ordering sorts
    chronologically by filename.
  - `<ext>` — `xlsx` for tabular data by default; use the extension that
    matches the actual format (`json`, `csv`, …) when it isn't a
    spreadsheet.
  - Example: `BdRDev_Ecosystem_260906_1430.xlsx`.
- **Import** accepts a file in the same shape the matching Export
  produces. Don't require the timestamped name on the way in (the user
  may have renamed it), but do validate the contents.
- Import is a **destructive save** — it runs through the "Are you sure?"
  confirmation above before it replaces or merges existing data.

## Baseline look & feel

- Dark theme, the palette already in the BdRDev dashboard
  (`--bg`, `--text`, `--text-dim`, `--processing` for "on/yes",
  `--waiting` for "dirty/pending", `#f87171` for errors).
- Monospace for identifiers (SHAs, addresses, paths, code).
- Tables: collapsed borders, small (~13px) body text, uppercase muted
  column headers, wide content scrolls inside its own
  `overflow-x: auto` wrapper rather than stretching the page.
- Primary action = filled button; secondary/destructive-cancel =
  outlined ("secondary") button.
- **Colour-code status.** Anywhere the UI shows the state of something
  (a service, a deploy, a check), use colour, not just a word: green =
  good / running / current, red = bad / down / error, amber = unknown /
  pending / not-tracked, muted grey = n/a or historical. Carry the same
  colour onto the container (a tile's left border, a row background) so
  state is scannable without reading each label. Always pair colour with
  text -- never colour alone. Reference: `srvhome/srvhome.py` in the
  `BdRPiSrvAMI` repo (`is-running` / `is-stopped` / `is-unknown` tiles
  and the "live here" deploy-history row highlight).

Extend this section as shared patterns get settled (forms, modals,
status lines, empty states).
