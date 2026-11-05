# Comms — one session per project, and how sessions talk

Two Claude sessions working the same project at once overwrite each
other's files. That happened on 2026-11-06: the scheduler's BdRapps
session and Brad's interactive one both built `/filament_dryer/`, and
each overwrote the other's files.
`_Comms.md` stops that, and gives sessions a place to leave each other
notes.

## The file

`<project>/_Comms.md`, at the project root. Add `_Comms.md` to the
project's `.gitignore` the first time you see it. It's live
coordination, not history, and claim churn would clutter every commit.

```markdown
CLAIMED by interactive (Brad) · 2026-11-06 07:23 · rFilamentDryer

# Comms

Line 1 is the claim. One session works this project at a time. See
BdRDev/_Instructions/Comms.md.

## Log
- [2026-11-06 07:40 scheduler → interactive] model.js has the PI with anti-windup; reuse it.
- [2026-11-06 07:42 interactive → scheduler] Thanks, taking it. Stand down.
```

### Line 1: the claim

Exactly one of these:

- `FREE` (or no file at all): nobody is working here.
- `CLAIMED by <who> · <YYYY-MM-DD HH:MM> · <what>`, using local Pi time.
  - `<who>` is one word: `scheduler` for a session the scheduler started,
    or `interactive` for one Brad is driving. Anything after it in
    brackets is a note for humans.
  - `<what>` is the request or task you're on.

A claim older than **2 hours** is abandoned. Anyone can take it over;
say so in the log when you do. While you work, re-stamp the time on your
claim whenever you post to the log, or at least every hour, so it stays
fresh.

### The log

One line per message, appended at the bottom, never edited:
`- [YYYY-MM-DD HH:MM <from> → <to>] text`. Keep each line to what the
other session needs: which file is whose, what you changed, what to
leave alone.

## Rules for every session

1. **Before editing anything, read `_Comms.md`.**
   - If it's `FREE`, missing, or stale: write your claim, then start.
   - If it's yours: carry on. A scheduler-started session finds
     `CLAIMED by scheduler` already written for it. That one is yours.
   - If someone else holds a live claim: **don't edit project files.**
     Append a log line saying what you were asked to do. Then:
     - unattended: end your turn;
     - interactive: tell Brad who holds the claim and ask whether to
       take over.
2. **Taking over** (only with Brad's say-so, or when the claim is stale):
   rewrite line 1 with your claim and log it, e.g. `interactive →
   scheduler: taking over, stop editing`. If the other session is still
   running on this box, message it directly as well (below).
3. **Re-read the log** before any big write: a new file, a rewrite, or a
   commit. If someone else's claim has replaced yours, stop editing. Log
   what you'd done and what's uncommitted, then end your turn.
4. **When you finish**, set line 1 back to `FREE`. Leave the log alone.

## Talking live

Claude Code sessions on the same box can message each other directly.
`ListAgents` shows the sessions running here, and `SendMessage` delivers
straight into one, even mid-task. Use it when both sessions are up, and
**also** log the message in `_Comms.md`, because the file is the record a
fresh session will read. A session that has ended can only be reached
through the file.

## What the scheduler does (`app/scheduler.py`)

- It **won't start a session** in a project that someone other than
  `scheduler` has a live claim on. It logs `claimed_elsewhere` and moves
  on to the next project.
- When it starts a session, it writes `CLAIMED by scheduler · … · <request
  titles>` first. It re-stamps the claim every 10 minutes while the
  session works, and sets it back to `FREE` when it hibernates the
  session. It only frees its own claim.
- If someone else claims a project while the scheduler's session is
  running, the scheduler stops typing into that session. The session
  stands down itself, per rule 3.
- It only ever rewrites line 1. The log is never touched.
