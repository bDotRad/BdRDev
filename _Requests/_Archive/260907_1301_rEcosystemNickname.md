# Ecosystem: add a Nick Name column

**Processed:** 2026-09-07 13:01 — direct ask from Brad (not a `_Requests/` file).

## What was asked

> Add a Nick Name column to the ecosystem. This will be used for the web
> pages. It will allow me to put spaces etc

## Decisions (asked Brad)

- **Scope:** both Ecosystem grids — Servers *and* Projects.
- **Blank behaviour:** a blank nickname falls back to `name` at render
  time, so no row ever shows an empty label.

## What changed

App code (coupled — needs the SQL below + a dashboard restart to take effect):

- `app/common.py` — `nickname` added to the normalised server + project
  shape (blank-safe via `_eco_str`); `"nickname": ""` seeded on every
  `DEFAULT_ECOSYSTEM` row.
- `app/fleet_db.py` — `nickname` included in the `servers` / `projects`
  upsert payloads; docstring.
- `app/templates/index.html` — "Nick Name" column (header + editable
  cell) in `renderEcoServers` / `renderEcoProjects`; `+ Server` /
  `+ Project` seed rows; `ECO_CSV_COLUMNS` + CSV-import seeds.

Schema:

- `supabase/DRAFT_ecosystem_nickname.sql` — **new DRAFT** (not in
  `migrations/`, run by hand). Adds `nickname text not null default ''`
  to `public.servers` and `public.projects`, rebuilds
  `fleet_ecosystem_json` to emit `nickname` right after `name`,
  `notify pgrst`. Stacks on top of `DRAFT_ecosystem_web_columns.sql`;
  every statement guarded / idempotent.

Docs:

- `supabase/DATA_MODEL.md`, `supabase/README.md` — field tables +
  view-contract JSON updated.

This commit also carries the previously-uncommitted **projects-side**
web-URL split (`web_url` → `local_url` + `ts_url` on `projects`, matching
the servers-side split already landed in `f0497fa`) — it was sitting
finished-but-unstaged in the tree and is entangled with the same files.

## Verified

- `_normalize_ecosystem` round-trips; old `state/ecosystem.json` caches
  without the key upgrade cleanly (`nickname` → `""`).
- `python3 -m py_compile` clean on `common.py` / `fleet_db.py`.

## Still needs Brad (no sudo / no Supabase write in-session)

`fleet_db.env` is present, so the dashboard reads from Supabase — the SQL
must run **before** the restart, or the first grid Save POSTs to a
missing column and silently falls back to JSON.

```
@@@ --- Action --- @@@

1. Add the nickname column + rebuild the view

"In the Supabase SQL editor on this box (Studio), paste and run the whole file"
supabase/DRAFT_ecosystem_nickname.sql

2. Pick up the matching app code on the live dashboard

"Restart the dashboard (brief outage of the live single-user app)"
sudo systemctl restart bdrdev-dashboard

3. Verify

"Confirm the new column is served"
curl -s localhost:8420/api/ecosystem | python3 -m json.tool | grep -m2 nickname

@@@ ------------- @@@
```

Rendering `nickname` on web pages *outside* this repo (e.g. BdRWebGUIDev)
is a separate change in those repos — the field is now in the
`/api/ecosystem` payload and the DB view for them to consume.
