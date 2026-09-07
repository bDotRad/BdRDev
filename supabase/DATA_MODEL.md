# Fleet data model — server, project, app

Status: **proposal** (2026-08-29). Not yet implemented. Reviewed against
`migrations/20260828120000_fleet_schema.sql`, `app/common.py`
(`DEFAULT_ECOSYSTEM`), `app/fleet_db.py`, `README.md`, and the live
`/api/ecosystem` payload.

## Recommendation

**Two entities, not three. Fold `app` into `project`.**

For this fleet a project deploys exactly one app, so "app" is not its own
thing — it is the *deployment facet* of a project: which server it runs
on, its URL, its database. That leaves one relationship worth modelling:
**a project runs on a server** — one nullable foreign key.

## What the model has today

Three separate tables:

- `servers` — one row per machine.
- `projects` — one row per repo, plus child `project_agents` (free-text
  agent names).
- `apps` — one row per deployed/planned app, with a `server_id` FK.

The gap: **there is no link between a project and its app.** `apps` has
no `project_id`. They are tied together only by sharing a name — a string
match nothing enforces, and which already breaks (`BdRDev` the project
vs. `BdRDev dashboard + scheduler` the app).

```
   projects  ┄┄┄ name only, unenforced ┄┄►  apps  ──server_id──►  servers
      │                                                              │
      ▼ 1:N                                                          ▼ M:N
  project_agents                                                  software
  (free-text names)                                               (catalogue)

  "what runs where?"  →  project.name ≈ app.name (guess)  →  app.server_id → server
```

## Proposed

Merge `apps` into `projects`. A project carries its own deployment.
`runs_on = NULL` means "not deployed" — covering every "planned" /
"doesn't exist yet" row without a separate flag.

```
   ┌──────────────────────┐                       ┌──────────────────────┐
   │ project              │      runs_on          │ server               │
   │ ──────────────────── │   (nullable FK)       │ ──────────────────── │
   │ name · exists        │ ────────────────────► │ name · tag           │
   │ runs_on →            │                       │ address · tailscale  │
   │ local_url · ts_url   │ ◄┄┄ hosts ┄┄┄┄┄┄┄┄┄┄  │ local_url · ts_url   │
   │ database · status    │   (derived, read-only)│ host·os·ram·disk     │
   │ roles[ ]             │                       │ software[ ]·provisd  │
   └──────────────────────┘                       └──────────────────────┘

  "what runs where?"  →  project.runs_on  — one hop, enforced by the database
```

The per-server "apps running here" list becomes a **derived view**, not a
table anyone edits.

## Fields

### server

Largely unchanged from today's `servers`. The redundant free-text
software string (`software_freetext`) is dropped; web access is two
fields, not one.

| Field | Type | Note |
|---|---|---|
| `name` | text, unique | identity — `BdRPiSrvDev`, `BdRPiSrvAMI`, … |
| `nickname` | text | free-text display label for the web pages (spaces / punctuation OK). Blank → falls back to `name`. |
| `tag` | text | short parenthetical shown by the name |
| `address` | text | primary LAN IP / hostname |
| `tailscale_ip` | text | tailnet IP, blank if not on the tailnet |
| `local_url` | text | LAN / mDNS `*.local` address, rendered as a link. Was `web_url`. |
| `ts_url` | text | Tailscale front-door URL (`https://<node>.tail0ed3f6.ts.net[:port]`), blank where the box isn't on the tailnet or `tailscale serve` isn't set up. Per-app tailnet ports aren't modelled. |
| `host` / `os` / `ram` / `disk` | text | hardware, dropdown-assisted |
| `software[ ]` | M:N catalogue | Claude Code / Nginx / Supabase / SQLite — Y/N, keep as-is |
| `provisioned` | bool | machine actually exists and is set up |
| `is_dev_host` | bool | at most one true — the source-of-truth box |
| `git_notes` | text | push/pull notes |

`software_freetext` removed 2026-09-04 (`supabase/DRAFT_ecosystem_web_columns.sql`):
the four `software[ ]` booleans already cover "what runs here" and the
free-text column had drifted. `web_url` → `local_url` + new `ts_url` in
the same migration.

### project

Today's `projects` table, plus the useful columns from `apps`, plus a
fixed role matrix in place of free-text agent names.

| Field | Type | Note |
|---|---|---|
| `name` | text, unique | identity — the repo directory name |
| `nickname` | text | free-text display label for the web pages (spaces / punctuation OK). Blank → falls back to `name`. |
| `exists` | bool | repo is on disk (`BdRIS` is false) |
| `runs_on` | FK → server, nullable | **from `apps.server_id`** — null = not deployed |
| `local_url` | text | deployed app URL on the LAN / mDNS, rendered as a link. Was `web_url` (from `apps.web_address`). |
| `ts_url` | text | Tailscale front-door URL for the app (`https://<node>.tail0ed3f6.ts.net[:port]`), blank where it isn't exposed on the tailnet. |
| `database` | enum | **from `apps.db`** — `none` / `SQLite` / `Supabase` / `shares:<project>` |
| `status` | enum | **replaces `apps.planned`** — `planned` / `building` / `deployed` / `live` |
| `roles[ ]` | M:N catalogue | PM / Web / DB / Elec Ctrl / Elec LV-HV / Doco — Y/N, mirrors `software` |
| `notes` | text | e.g. "ESP32 edge nodes", "feeds PlanBdRad's DB" |

Dropped from `apps`: `name` (same as the project), `tag` (folds into
`notes` / `status`), and the separate row itself.

`servers.nickname` + `projects.nickname` added 2026-09-07
(`supabase/DRAFT_ecosystem_nickname.sql`) — a display label for the web
pages so a name can carry spaces; blank falls back to `name`.

`projects.web_url` → `local_url` + new `ts_url` on 2026-09-04
(`supabase/DRAFT_ecosystem_web_columns.sql`, same migration as the servers
change) — the Ecosystem "Projects" grid shows both as separate link columns.

## When a separate `app` table earns its place

Add it back — as a **child of `project`**, not a sibling — only when one
of these becomes true:

- a single project deploys **two or more separately-addressable apps**
  (different URLs, different lifecycles);
- a single app is **built from more than one project**;
- you want to track **individual running services** (systemd units,
  containers) rather than "the deployment" as a whole.

None hold today. `BdRDev`'s "dashboard + scheduler" is two processes of
one deployment — a `notes` line, not a second entity.

## UI consequence

One **Ecosystem** page. Two editable grids on it:

- **Servers** — the machines.
- **Projects** — repo + deployment + roles. "Runs on" is a dropdown of
  servers; "Hosts" on a server row is derived from it.

Retires the **Fleet** tab (form editor — the grids replace it) and the
old **Ecosystem** tab (ASCII tree — if still wanted, it renders *from*
these two tables). Matches the open requests `rUpdate Fleet…`,
`rFlet update`, `rFix all of the web pages` — close them, open one that
says exactly this.

## Not decided here

- Migration path: how to move existing `apps` rows onto `projects`
  without losing the notes currently living in `apps.db` free-text
  (e.g. `"Supabase (Postgres) — schema not applied to Pi yet"`).
- Whether `fleet_meta.notes` stays a page-level blob or moves onto rows.
- Whether `roles` is a real catalogue+M:N (like `software`) or just
  fixed boolean columns on `project`.
