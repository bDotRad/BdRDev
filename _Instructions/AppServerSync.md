# App Server Sync

Convention for projects that also run live on a separate "app server"
machine (e.g. PlanBdRad and BdRAMAssist on the AMI Pi `BdRPiSrvAMI`,
LAN `10.10.10.20` — formerly the retired `BdRSrvAMI` VM at
`192.168.100.20`) when a change needs to be made directly on that
machine -- a live-troubleshooting tweak, a quick config fix, whatever.
Historically that meant pushing straight from the app server's own git
checkout back to GitHub. **This convention replaces that: app servers
should be pull-only.** Every real change to a project's tracked source
still originates on the dev server (`BdRDev`, this host) and gets
pushed from here, the same as any other Claude Code work under
`~/projects/<name>/`.

## Why

A push-capable credential sitting on a live app server means a change
made there under time pressure can land in the repo without going
through this Pi's usual Claude Code / request-intake workflow -- no
review, and it can just as easily get overwritten by the next `git
pull` if dev-side work happened to diverge in the meantime. Brad would
rather funnel any app-server-side edit through the dev server instead:
the app server *drops* the raw changed file here, a Claude session on
BdRDev folds it into the tracked source and pushes it properly, and
the app server *pulls* the result back down afterward. Expected to be
rare ("it shouldn't happen often") -- this is a manual, on-request
convention, not an automated watcher/daemon.

## The convention

### 1. Drop folder

Each project that's also deployed to an app server gets an
`_AppServerDrops/` folder at the root of its dev-side directory
(`~/projects/<name>/_AppServerDrops/` on BdRDev), parallel to
`_Requests/`. Create it the first time it's actually needed for that
project, not scaffolded into every project by default.

- The app server places the changed file(s) here, named to mirror
  their path inside the repo -- e.g. a change to `app/scheduler.py`
  gets dropped as `_AppServerDrops/app/scheduler.py` -- so it's
  unambiguous which tracked file each drop corresponds to, even if
  several come over at once.
- Add `_AppServerDrops/` to the project's `.gitignore`. These are raw,
  not-yet-reviewed drops, not real commits -- only the edit once it's
  folded into the actual tracked source file should ever be committed,
  never the raw drop itself.
- Alongside the file(s), also create a normal
  `_Requests/rAppServerChange <short name>.md` request, `READY`-marked,
  per the existing `_Requests/` convention (see `Requests.md`) -- e.g.
  "PlanBdRad app server: fixed a typo in app/scheduler.py directly on
  BdRPiSrvAMI, see _AppServerDrops/app/scheduler.py for the new version,
  please fold it in and push." That request is what actually gets
  picked up -- the scheduler already wakes a session whenever a
  project has a `READY` request, so this reuses that existing trigger
  rather than needing a new watcher/daemon.

### 2. Dev-side handling (manual, on-request)

Handled like any other `_Requests/` item, under the project-manager
convention already in place:

1. Read the note in `_Requests/rAppServerChange ....md` and diff the
   dropped file in `_AppServerDrops/` against the real tracked file it
   corresponds to.
2. Fold the change into the real, tracked source file -- by hand for
   something trivial, or hand off to `web-dev-expert` /
   `supabase-sql-expert` if it's non-trivial application code or SQL.
   The drop itself is just raw text off a live box, not a vetted
   patch -- review it before folding it in.
3. Commit and push through the normal flow (`git_commit_and_push` /
   the GitHub tab, or the CLI directly).
4. Delete the file from `_AppServerDrops/` once it's been folded in --
   same "don't leave it sitting there implying unfinished work" logic
   as `_Requests/`.
5. Archive the request per `Requests.md` as usual.

### 3. App-server-side, afterward

Once the dev-side push lands, the app server does a plain `git pull`
(or equivalent) in its own checkout to sync back down -- no different
from any other deploy.

**Deploy-key direction matters here and isn't fully in place yet** --
this pass only documents the convention; none of the following has been
re-verified on the current app server (the AMI Pi `BdRPiSrvAMI`,
`10.10.10.20` — the notes below predate the `BdRSrvAMI` VM's retirement
and refer to that old box):

- **Pull (app server <- GitHub), required for step 3 to work at all:**
  on the retired `BdRSrvAMI` VM this was `id_ed25519_bdramassist`
  (read-only, installed 2026-08-26). Whatever `BdRPiSrvAMI` uses now is
  configured on that box under `~/projects/BdRPiAMI/` and hasn't been
  re-confirmed from this repo. Same for PlanBdRad's app-server-side pull
  key (was `id_ed25519_planbdrad` on the VM). Worth Brad (or a session
  with access to `BdRPiSrvAMI` via `ssh BdRPiAMI`) confirming both are
  read-only before relying on this convention.
- **Push (app server -> GitHub), meant to go away under this
  convention:** if a push-capable key or credential still exists on an
  app server for a project's repo, it should be revoked or downgraded
  to read-only once this convention is adopted for that project. Not
  done as part of this pass.
- **Drop transport (app server -> BdRDev, for placing files into
  `_AppServerDrops/` in step 1, e.g. via `scp`/`rsync`):** no key for
  this direction is documented in `SSH.md` yet -- this is the actual
  gap standing between "convention documented" and "convention usable"
  today. `SSH.md` does flag one existing open item that might already
  be exactly this: `~/.ssh/authorized_keys` on BdRDev trusts a key
  with comment `PlanBdRad` that doesn't match any known private key on
  this host -- possibly a leftover attempt at this same direction, but
  unconfirmed. Setting up (or confirming/repurposing) an
  app-server -> BdRDev key is a prerequisite for actually using this
  convention day to day, and is flagged here as follow-up work, not
  resolved in this pass.

## Scope

This applies to any project with a live app-server deployment, not
just PlanBdRad/BdRAMAssist -- set up `_AppServerDrops/` the same way
for any future project that ends up in a similar situation.
