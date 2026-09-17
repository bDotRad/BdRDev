# _Requests

Drop-box for bug reports / change requests / screenshots, for Claude Code
to process on request. Not part of the app itself -- just a working
folder between Brad and Claude.

This follows Brad's general "Claude Pi Workflow" request-intake
convention (not specific to this repo -- other projects on the same Pi
keep their own copy of the source doc in their own archive), adapted to
how it's actually used here.

## How to add something

- A file or folder named `r<Title>.md` (or `r<Title>/` if it needs
  supporting files alongside it -- screenshots, logs, etc.), where
  `<Title>` is a short human-readable description of the ask, e.g.
  `rLogo resize.md`. The web UI's "+ Request" form asks for a title and
  builds the filename from it automatically; if you're dropping a file in
  by hand instead, just name it yourself the same way -- the title is
  whatever's left after stripping the leading `r`. Title doesn't need to
  be unique forever (once a request is archived, its title can be
  reused), just unique among what's currently sitting in `_Requests/`.
- **First line of `r<Title>.md` must be exactly `READY`, `NOT READY`, or
  `WAITING RESPONSE`**, nothing else on that line. That first line is
  the *only* thing that gates the whole file -- `READY`/`NOT
  READY`-looking text anywhere else in the body is just prose, not a
  marker, and doesn't get parsed as one. If a document genuinely covers
  multiple things with different readiness (e.g. "part A is decided,
  part B is still a draft"), split it into separate files (`rTitle A.md`,
  `rTitle B.md`) rather than marking a section mid-document -- there's no
  per-section marker syntax, and there isn't going to be one; simpler
  to just use separate files.
  Only `READY` requests get processed on a passive "scan requests" --
  drop a request in as `NOT READY` and flip it once it's actually
  ready. Naming a specific one directly ("scan rLogo resize") processes
  it regardless of its marker (or a missing/malformed one) -- an
  explicit ask from Brad is its own trigger.
  `WAITING RESPONSE` means Claude tried to process it and got stuck on
  something only Brad can resolve -- see "When a request can't be
  finished" below. It's a signal Claude sets, not one Brad writes when
  dropping a request.
- Prefix a file/folder name with `x` (e.g. `xrLogo resize.md`) to make
  Claude ignore it entirely, without deleting it.
- No required format for the body, but `Issue / When / Solution` (what's
  wrong, when it happens, any workaround already found) is a good
  default for bug reports.

## How to trigger processing

- **"scan requests"** -- process every `READY` item directly in
  `_Requests/` (not `_Archive/`).
- **"scan rLogo resize"** (or just "scan Logo resize") -- process just
  that one, regardless of what else is sitting in the folder.

## What happens after

Once a request's been read and either fixed or otherwise resolved, write
**one** file to `_Archive/` -- don't also carry the original `r<Title>.md`
over separately; the archived file *is* the complete record, so a bare
copy of the request text next to a summary is just clutter (and, worse,
a name collision waiting to happen -- see the note below).

- **Name:** `YYMMDD_HHMM_<short-name>.md` -- date and time processed (24h,
  local time, from when the archive file is written) + a short
  descriptive slug (not necessarily the original title verbatim;
  something someone browsing the archive later can recognize at a
  glance, e.g. `260822_1535_rLogoOverlap.md`). The time component exists
  so that same-day archive entries still sort chronologically by
  filename -- see the note below. If a batch of requests was handled
  together in one pass, one file covering all of them is fine -- pick a
  name for the batch, or chain the slugs.
- **Content, top half:** what was done -- what was asked, what was
  found, what changed, and the outcome (fixed and deployed / investigated,
  no code change needed / needs a restart or `sudo` step Brad has to run
  / etc).
- **Content, bottom half:** the original request, verbatim (marker line
  included) -- so the archived file is self-contained and the raw ask is
  never lost, without needing a second file to hold it.
- Delete the original `r<Title>.md`/`r<Title>/` from `_Requests/` once
  its content has been folded into the archive file this way, so
  `_Requests/` only shows what's still outstanding. A folder request
  (`r<Title>/`) with real attachments (screenshots, logs) can instead be
  moved into `_Archive/` wholesale, dated (`YYMMDD_rf <name>/`), if the
  attachments themselves are worth keeping around -- just don't *also*
  leave a bare, un-summarized copy of the request text sitting next to
  it.
- **Commit and push to GitHub.** Once the archive file is written (and
  any code change verified working -- restarted live if it touches
  `app/`), `git add` the changed/new files, commit with a message
  describing what changed, and `git push`. This applies whether a
  request was processed alone or as part of a batch -- one commit per
  pass is fine. Before 260823 this step was regularly skipped, which let
  real, already-verified work pile up uncommitted/unpushed for days;
  don't let that happen again -- a request isn't actually done until
  it's pushed, not just archived.

  *Why not just move the original file into `_Archive/` under its own
  name, the way it used to work:* a title can get reused once its file
  leaves `_Requests/` (the next new request may happen to get the same
  title, or the web UI form's auto-generated filename may collide). A
  later archive pass for that reused title, done the old way, would
  silently overwrite the earlier file already sitting in `_Archive/` --
  same filename, different content, no error. Since 260822 this
  convention avoids that entirely by never preserving the bare
  `r<Title>` name in `_Archive/` in the first place -- the archived file
  is always named for what it *was* (date-prefixed), not for the slot it
  happened to occupy in the inbox.

  *Why the name also carries `HHMM`, not just `YYMMDD`:* the archive
  browser (the dashboard's "Archive" button) lists files newest-first by
  doing a reverse alphabetical sort on filename, on the assumption that
  the date prefix makes that equivalent to reverse-chronological. On a
  day with several archived requests, a date-only prefix left every
  same-day file to sort by slug instead, so the list order didn't match
  actual processing order. Since 260822 (later same day) the time is
  included too so same-day entries stay in true order. This is
  minute-granularity, not second-granularity -- two requests archived
  within the same minute will still just sort by slug relative to each
  other, which is an accepted edge case.

## Keeping the fleet map current

Applies in **every** project, not just BdRDev. If a request changed a
**deployment fact** — a new app or project, a changed URL / port /
hostname, a project moved to a different box, a box provisioned, a
service that now exists or is now live — then before you archive the
request:

1. Update the fleet **ecosystem data** — the self-hosted Supabase on
   `DEV` (`servers`, `projects`, `project_roles`, `server_software`).
   Easiest path is the BdRDev dashboard's Ecosystem editor; if it needs
   a schema change, that's a `supabase-sql-expert` / migration job.
2. Update `BdRDev/_Instructions/FLEET.md` so the map matches (until the
   generator lands it's maintained by hand).
3. Do **not** touch `BdRDev/state/ecosystem.json` — it's a read cache
   Supabase overwrites.

Use the canonical name / handle from `BdRDev/_Instructions/Naming.md` for
every box and project — never an alias, never a `nickname` string.

This is the step that was being skipped, which is why the Ecosystem page
drifted. Treat "map updated" as part of "request done", the same as
"committed and pushed".

## When a request can't be finished

If a request genuinely can't be completed in one pass -- blocked on a
decision, credentials, or anything else only Brad can supply -- **leave
it in `_Requests/`** (don't move it to `_Archive/` half-done) and:

1. Set its first line to `WAITING RESPONSE`.
2. Add a short note in the body -- above or below the original text, but
   keep the original request text intact -- explaining what's blocking
   it and what's needed to unblock it.

It'll keep showing up in `_Requests/` (and won't get picked up by a
passive "scan requests", same as `NOT READY`) until Brad answers and
flips it back to `READY`.

**This is the right move even when the blocker is an interactive
prompt**, not just a written question -- e.g. auto-mode's safety
classifier declining a risky action (a live-service restart, `kill -9`,
etc.), or a tool asking a multiple-choice question. Running unattended,
nobody is watching the session's terminal in real time, so an open
confirmation dialog with no one there to answer it just sits forever,
burning the project's scheduler slot for no benefit -- decline/cancel
the prompt rather than leave it open, then use `WAITING RESPONSE` as
above and end the turn. The dashboard already flashes a "Waiting Input"
button whenever a request is `WAITING RESPONSE`, and the scheduler
hibernates the session on its own once nothing's left `READY` -- that's
the actual channel Brad monitors, not the live tmux pane.

## How to write actions and questions back into a request file

When a pass can't finish without Brad doing something (running a
command, making a decision), the leftover work goes **into the request
file body** in one of two fixed block formats, so it's unambiguous what
Brad has to do or answer. Use these verbatim -- same delimiter lines,
same headings -- in this project and every other project on the fleet.

### Action block -- "here is exactly what to run"

For anything Brad has to execute by hand: `sudo`, a live-service
restart, an interactive login (`gcloud auth login`), or **SSH commands
to run on another box** (the unattended session's auto-mode classifier
blocks starting/restarting daemons on remote hosts and all `sudo`).

```
@@@ --- Action --- @@@

1. What this step achieves (one line)

"Description of what these commands do"
command one
command two

"Description of the next thing"
command three

2. What the second step achieves

"Description"
command four

@@@ ------------- @@@
```

Rules:
- Every command (or contiguous group of commands that share a purpose)
  gets a **quoted plain-English description on the line above it**. A
  group that must be run together as a unit can share one description.
- Number the steps if there's more than one; keep them in run order.
- Say where each step runs if it isn't obvious -- `# on the Pi`,
  `# on this dev box`, `# in the Supabase SQL editor`.
- Put **only** copy-pasteable commands inside the block. Explanation,
  caveats, and "why" go in prose outside it.
- If a step needs `sudo`, still write the exact `sudo ...` line -- don't
  paraphrase it as "restart nginx".
- Leave the request's first line `WAITING RESPONSE` while an Action
  block is outstanding. Brad runs the steps, then flips it back to
  `READY` (with a note if anything failed) or archives it.

### Question block -- "I need a decision"

```
??? --- Question --- ???

The question, stated so it can be answered standalone.

Options:
1. First option -- what it implies
2. Second option -- what it implies
3. Third option

Answer:
<Brad writes here>

??? --------------- ???
```

Rules:
- One block per distinct decision -- don't bundle unrelated questions.
- Always offer numbered options when you can, even if one is "leave it
  for now". If it's genuinely open-ended, still give the block and note
  that.
- If you have a recommendation, mark it: `1. ... (recommended)`.
- Brad answers on the `Answer:` line(s) in place; don't require him to
  restructure the block.
- Same as above: first line stays `WAITING RESPONSE` until answered.

Both blocks can appear in the same file. Keep the original request text
intact underneath; these blocks go above it (newest at the top).

## Not yet built (per the convention doc, deferred until needed)

- Automated folder watcher -- purely manual/on-request for now.
- Sentinel-file READY marker instead of a first-line check.
- Email/SMS intake, or a small web UI once volume outgrows a visual scan.
