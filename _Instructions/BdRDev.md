# Orchestration context for this project

This project runs inside a scheduler that manages multiple projects on
this Pi. Read this before you start working — it explains things about
your environment that aren't otherwise obvious from inside the session.

## Fleet-wide standards

This project is part of a fleet with shared conventions — request
handling, project layout, web look & feel, versioning (the version is
the deployed **7-char commit SHA**), the **Edit / Save / Cancel**
pattern for editable tables, SSH key naming, and more. The canonical
copies live in **`BdRDev/_Instructions/`** on the dev box (start at
`Standards.md`); they are *not* copied into each project. Follow them
unless this project's own `CLAUDE.md` / `_Instructions/` explicitly
say otherwise.

## The setup, in short

- You (this Claude Code session) are running inside a tmux session named
  `proj-<this-project-name>`.
- A separate always-on script, `scheduler.py`, decides when your session
  gets started and when it gets killed. You are not the only project it
  manages — there may be others in rotation that you have no visibility
  into.
- A web dashboard (`dashboard.py`) shows a person which project is
  currently active and lets them add/remove projects from the rotation.
  Neither of these processes are "another Claude" — they're plain Python,
  no LLM involved. Don't expect either one to interpret natural language;
  they only read files and send fixed strings into tmux.

## How you get woken up and put to sleep

1. The scheduler notices files in this project's `requests/` folder.
2. It starts (or reuses) your tmux session and sends you this exact
   message: **"Check the requests folder for new or updated files and
   process them now."** That's your cue to look in `requests/` and act.
3. After you respond, the scheduler waits a few seconds and checks the
   `requests/` folder again — purely by counting files, it does not read
   your output. **If files are still sitting there, it will send you the
   same prompt again.** So: once you've handled a request, remove it,
   move it, or rename it (whatever convention this project already uses
   for "done") — otherwise the scheduler will think there's still
   unfinished work and keep nudging you about the same file.
4. If `requests/` is empty, the scheduler gives you one 30-second grace
   period, checks again, and if it's still empty, **it kills this tmux
   session outright.** This is not a signal you can intercept or a
   `SIGTERM` you can handle gracefully — the process just ends.

## If you need Brad's input (or hit an auto-mode block)

Nobody is watching this session's terminal in real time — it runs
unattended between scheduler wake-ups. Don't rely on an interactive
confirmation dialog (a permission prompt, or the `AskUserQuestion` tool)
to get an answer out of Brad: the scheduler has no visibility into that
dialog either, it only counts files in `_Requests/`, so sitting at an
open prompt just burns your rotation slot indefinitely with no way for
anyone to know you're stuck.

If you hit something only Brad can decide — including auto-mode's
safety classifier blocking a risky action (a live-service restart,
`kill -9`, etc.) — don't leave that dialog open waiting for a reply:

1. Decline/cancel the interactive prompt (choose "No" / don't proceed)
   rather than leaving it hanging.
2. Set the relevant request file's first line to `WAITING RESPONSE` and
   write the leftover work into the body using the **Action block** /
   **Question block** formats in `_Instructions/Requests.md` ("How to
   write actions and questions back into a request file") -- exact
   commands with a description per command for anything Brad must run,
   numbered options for anything he must decide.
3. **Say what you need in your own last chat message too, not just in
   the file.** Brad mostly checks in via CloudCLI (a session/transcript
   viewer, not this dashboard), so your plain-English final message —
   "I need X, see the Action block in `rFoo.md`" — is what he's likely
   to actually read; don't make the file the only place the question
   exists. Keep it short: state what's blocked and point at the file,
   don't repeat the whole Action/Question block verbatim in the chat.
4. End your turn. Once nothing in `_Requests/` is `READY`, the scheduler
   hibernates you automatically after its grace period — no need to
   stay alive waiting for an answer. The dashboard also flashes a
   "Waiting Input" button whenever a request is `WAITING RESPONSE`
   (2026-09-17: confirmed this is a pure file-marker scrape, decoupled
   from any live session — don't assume it, or its absence, means
   anything about whether your last chat message got through). Brad
   answers in the file and flips it back to `READY` to wake a fresh
   session — remember that's a **brand-new** process with no memory of
   this one, so the file has to be self-contained regardless of what
   you said in chat.

## What this means for how you should work

- **Don't leave work uncommitted.** Because your session can be killed
  the moment the requests folder looks empty, treat every request as
  "commit and push before you're done responding to it," not "I'll clean
  this up on my next turn." There may not be a next turn in this session.
- **Don't rely on in-memory state surviving between requests.** If the
  scheduler hibernates and later restarts you, you're a fresh process —
  no memory of earlier in this session. Anything that matters should be
  in the repo, in a status file, or in the request/response files
  themselves, not just "remembered."
- **A single request file should represent a complete unit of work.**
  Don't split one task across "I'll do part of it now and finish next
  time I'm woken" — you may not get woken again for a while if this
  project drops out of the rotation.
- **If a request is genuinely too large to finish in one go**, leave
  clear written state behind (e.g. a note in the repo, or leave the
  request file in place with a comment file alongside it) so a fresh
  session — possibly you, possibly not — can pick up the thread. Don't
  assume continuity.

## Optional: reporting status to the dashboard

If you want the dashboard to show a human-readable "current task" line
for this project (purely informational — the scheduler itself doesn't
read this), write to:

```
.claude-status/status.json
```

```json
{ "current_task": "Implementing user auth flow", "last_active": "2026-08-23T10:15:00Z" }
```

This is optional and has no effect on scheduling — it's just for the
person watching the dashboard.

## Optional: leaving SQL for a human to run

If your work produces SQL that needs to be run by hand somewhere the
dashboard can't reach (e.g. the Supabase SQL editor), write it to:

```
.claude-status/sql_output.txt
```

Plain text, the SQL statement(s) as-is. The dashboard shows a "SQL"
badge on this project's card whenever that file exists, with a
copy-to-clipboard window. It's on you (or a later session) to delete the
file once it's been run — the dashboard has a Clear button for this, but
if you regenerate the SQL, just overwrite the file rather than appending.

## Multi-project awareness

You cannot see other projects' folders, sessions, or requests from here,
and you shouldn't need to. If a request references work that belongs in
a different project, say so rather than reaching outside this project's
directory — the scheduler and dashboard are the only things with a
cross-project view, and they're not something you can query.

## If this project also runs live on a separate app server

If a change is ever made directly on that machine instead of here, it
should **not** get pushed to GitHub from there — see
`BdRDev/_Instructions/AppServerSync.md` for the drop-folder convention
(`_AppServerDrops/`) that funnels app-server-side edits back through
this dev server instead.