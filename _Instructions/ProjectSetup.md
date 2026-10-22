# Project setup standard

The standard shape a project on this Pi should have, and what "Setup
Project" means as a trigger phrase. Like `BdRDev.md` and `SSH.md`,
the canonical copy of this doc lives here; other projects don't need
their own copy, but a session working in a new project should know
these conventions exist.

## The standard files/folders

- **`CLAUDE.md`** (repo root) — agent-facing operating notes: how the
  scheduler wakes/kills this session, project-specific gotchas,
  conventions. Written for the Claude Code session, not a human
  reader. The dashboard's project-file browser (`app/common.py`,
  `list_agent_files()`) shows this under "Claude agent files".
- **`Description.md`** (repo root) — a short, human-facing summary of
  what the project *is* and what it's for. Distinct from `CLAUDE.md` --
  see `_Requests/_Archive/260824_1712_CreateDescription.md` for why
  these were split apart. The dashboard's Description panel
  (`find_description_file()`) reads this file specifically. This is
  also where any human-side context belongs (who the project's for,
  who to contact, ownership notes) if a project ever needs it -- there's
  no separate "human agent" file mirroring `.claude/agents/`; see
  `_Requests/_Archive/260825_*_rDoco.md` for why.

  `Description.md` also carries a `## Git repository` section stating
  whether the project has a git repo at all and, if so, its remote
  URL(s) (`git remote -v`). If there's no repo, say so plainly ("No git
  repository -- not yet initialized") rather than omitting the section --
  the point is that a glance at `Description.md` answers the question
  without having to `cd` in and check. See
  `_Requests/_Archive/260825_*_rClean Up.md` for why this was added.
- **`.claude/agents/<agent-slug>/<agent-slug>.md`** — one folder per
  subagent, each holding a single Claude Code subagent-format `.md`
  (YAML frontmatter with `name`, `description`, `tools`, then the
  agent's instructions in the body). The dashboard picks these up via
  `list_agent_files()`, which globs `.claude/agents/**/*.md` -- the
  per-agent folder (rather than flat files directly in `agents/`)
  exists so an agent can keep reference material alongside its
  definition if it needs to. This shape was established on `PlanBdRad`
  (`project-manager`, `web-developer`, `sql-developer`,
  `asset-management-guru`) -- follow that as the worked example for a
  project with real domain-specific agents. `BdRDev`'s own
  `.claude/agents/` (`project-manager`, `web-dev-expert`,
  `supabase-sql-expert`, `doc-updater`) is written generically --
  no project name or domain baked in, just "this project" throughout
  -- specifically so it can be copied as-is into a new project's
  `.claude/agents/` as a starting set when nothing more specific has
  been asked for.
- **`References/`** (repo root) — a plain folder for site-specific or
  external documentation Brad drops in by hand (vendor docs, network
  details, anything that isn't Claude-authored). Not agent instructions
  and not parsed by the dashboard -- just a known, consistent place to
  put that material instead of it landing loose at the repo root or
  getting invented fresh per project.

A non-trivial new project may also carry a **`Scope.md`** (repo root)
-- what's in / out, milestones, decisions, done-when. Its required
shape is in [`ProjectScope.md`](ProjectScope.md).

None of this replaces a project's own free-form docs (`README.md`,
`DESIGN_NOTES.md`, `CHANGELOG.md`, etc, as seen on `PlanBdRad`) -- those
stay project-specific and aren't standardized here.

Everything in this folder (`BdRDev/_Instructions/`) is the **fleet-wide
top layer** of the two-layer standards system -- see
[`Standards.md`](Standards.md). A project inherits all of it (look &
feel and versioning from [`WebUI.md`](WebUI.md), request handling from
`Requests.md`, etc.) without copying anything; its own `CLAUDE.md` /
`_Instructions/` only need to record where it *deviates*.

## "Setup Project" as a trigger phrase

When Brad says **"Setup Project"** (in a request, or directly), it
means: scaffold whichever of the four items above the project is
missing, and populate `Description.md` from whatever context he gives
alongside the phrase (a one-line purpose is enough -- don't demand a
full spec). He doesn't want to have to spell out "create the folders,
populate the description" every time -- the phrase alone is the
instruction, same as "scan requests" is shorthand for the `_Requests/`
convention in `Requests.md`.

If he names specific agents in the same request, create one
`.claude/agents/<slug>/<slug>.md` per agent named, written the same way
the `PlanBdRad` agents are (a real, scoped subagent definition -- not a
placeholder). If he doesn't name any agents, it's fine to leave
`.claude/agents/` unpopulated until a later request adds one -- don't
invent agents nobody asked for.

`References/` is created empty (with a one-line `.md` placeholder
explaining what it's for, so it isn't a mysterious empty folder, and
so it survives being committed if the project uses git) unless Brad
hands over actual reference material to put in it.

This doc doesn't cover initializing git, systemd services, or a
project's actual tech stack -- "Setup Project" is scoped to the MD-file
layout above. Bootstrapping the rest of a new project is its own,
separate piece of work.
