# Web UI standard (fleet-wide)

Generic look-and-feel and interaction rules for **every** web app on the
fleet (BdRDev dashboard, PlanBdRad, BdRAMAssist, BdRDungeon, …). This is
the **top layer** — see [`Standards.md`](Standards.md) for how the
two-layer doc system works. A project only documents where it
*deviates*; if its `CLAUDE.md` / `_Instructions/` say nothing, these
rules apply.

## Versioning

- Every app shows its **version** as the **7-character short commit SHA**
  of the deployed checkout, rendered small and un-emphasised directly
  **under the page title / in the footer**. No separate version strings,
  tags, or `VERSION` files — the SHA is the version.
- Where an app records deploy history (e.g. `srvhome`), a "version" in
  that history is the same 7-char SHA, shown with the deploy timestamp,
  commit title and commit description.

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
  text -- never colour alone. Reference: `fleet/srvhome/srvhome.py`
  (`is-running` / `is-stopped` / `is-unknown` tiles, the "live here"
  row highlight, and the footer legend).

Extend this section as shared patterns get settled (forms, modals,
status lines, empty states).
