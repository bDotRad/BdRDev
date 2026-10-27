# RatDev — how it works

Local copy of `G:\My Drive\000 RatDev\_Instructions.md`. Brad edits the
Drive copy; if the two disagree, Drive wins — re-sync this one.

Drop a brief in `G:\My Drive\000 RatDev`. A Pi picks it up, a Claude session works on it, and you and Claude talk through two files per project. When the project is finished the whole folder goes to `_Archived`.

## Folder layout

```
000 RatDev/
├─ _Instructions.md           this file
├─ _Archived/                 finished projects (whole folder moves here)
├─ 001 Processing/            one folder per project in progress
│   └─ YYMMDD Name/
│       ├─ YYMMDD Name.md     the brief
│       ├─ Requests.md        questions / requests for info
│       ├─ Actions.md         prompts to run / actions to do
│       └─ (extra files)
└─ YYMMDD Name.md             new briefs get dropped here
```

## File naming

`YYMMDD` + anything + `.md`. The six-digit date at the front is the only rule. The rest is free text and can include spaces.

Example: `261018 BdRFairy.md`

The Pi keys off the leading six digits. Files without them are ignored.

## The flow

1. **Drop.** Put the brief in the RatDev root. First line is `READY` or `NOT READY`. `NOT READY` files are left alone.
2. **Pickup.** The Pi sees a `READY` file starting with `YYMMDD`, creates `001 Processing/<file name without .md>/`, moves the brief into it, and creates empty `Requests.md` and `Actions.md`.
3. **Work.** A Claude session reads the project folder and starts on the brief.
4. **Talk through the files.**
   - Questions or requests for info go in `Requests.md`.
   - Prompts to run, or other actions to take, go in `Actions.md`.
   - Either of us can write in them. Answer inline under the item.
5. **Or talk in the CLI.** Claude can read the files in the CLI and you respond there instead. The files stay the record: Claude updates them either way.
6. **Clean up.** Done items move from `## Open` to `## Completed` (don't delete them). Claude does this as it goes, and you can too.
7. **Archive.** When the project is finished (the brief's "Done when" is met and nothing is left under `## Open` in either file), the entire project folder moves from `001 Processing/` to `_Archived/`.

## Who picks up and dispatches (DEV side)

*Not in the Drive copy; DEV-side detail.*

- **The BdRDev session on `DEV` does pickup and decides who works on
  each brief** (Brad, 2026-10-18). Brad doesn't assign it.
- Dispatch = pick the target project: an existing `~/projects/<X>`, or a
  new one scaffolded per [ProjectSetup.md](ProjectSetup.md). Then drop a
  `READY` `_Requests/r<Title>.md` there holding the decisions made plus
  the verbatim brief, and make sure the project is in
  `state/selected_projects.json`. After that the scheduler wakes it like
  any other request.
- Record the routing decision in `Requests.md` under `## Completed`, so
  Brad can see who got the brief and why.
- There's no automatic watcher yet. Pickup happens when a BdRDev session
  is asked to check the folder, using the claude.ai Google Drive
  connector. The connector only exists in interactive sessions.
- Dispatched so far: `261018 RatsNest Gear Inventory` → new project
  `BdRTech` (RATSNEST host); `261023 BdRBoostLab` → existing `BdRapps`
  (new page, Firebase `Apps`); `261027 BdRNotes` → new project
  `BdRNotes` (RATSNEST host, viewer in the `bdrapps` Firebase project).

## Requests.md and Actions.md format

Same layout for both.

```markdown
# Requests

## Open
- [ ] Which Pi should this run on?
  - Answer:

## Completed
- [x] What's the supply voltage? (24 V DC, answered 18 Oct)
```

- One checkbox line per item. Use a sub-bullet for the answer or result.
- `Actions.md`: a prompt to run goes in a fenced block under its item. After it's run, tick it and add a one-line result.
- Completed lines can carry a short date.

---

# RatDev app brief — the required format

The format for a new-app brief dropped into **`G:\My Drive\000 RatDev`**.
One brief = one `.md` file = one app. Copy the template below, fill it in,
drop it in the folder.

Fields marked **(required)** must be filled before a session will start
building. Anything else can be `?` and the session will ask or pick a
sensible default.

## Brief rules

- **File name:** `YYMMDD Name.md` (see File naming above). The app's real name goes in the **Name** field inside the brief.
- **Status line:** the first line of the file is `READY` or `NOT READY`.
  `NOT READY` files are left alone.
- **Plain answers.** A sentence or a short list per field is enough. Don't
  write a spec; write what you'd tell someone over coffee.
- **Extra files** (screenshots, sample data, sketches) go in a folder with
  the same name as the brief (without `.md`): `YYMMDD Name/`. It is merged into
  the project folder at pickup.

## Template

```markdown
READY

# <App name>

## Name (required)
The app's name. Follows Naming.md — usually `BdR<Something>`.

## Description (required)
One or two sentences: what it is.

## Problem it's solving (required)
What's annoying / slow / missing today, and who has that problem.

## Who uses it (required)
Just me / family / work / public.

## What it must do (required)
3–7 bullets. The minimum that makes it useful.

-
-
-

## Nice to have
Things that can wait for v2.

## Does it need GitHub? (required)
yes / no. If yes: private or public. Default = yes, private, under bDotRad.

## Where is it hosted? (required)
Pick one:
- `DEV` — BdRPiSrvDev (dev/sandbox only)
- `AMI` — BdRPiSrvAMI (work / asset-management stuff)
- `RATSNEST` — BdRPiSrvRatsNest (home / Dungeon / automation)
- `Apps` — Firebase static hosting (shared with other people, no server)
- local only — runs on my PC, nothing hosted
- not sure

## How is it reached?
LAN only / tailnet / public internet. Default = LAN + tailnet.

## Data
Does it store anything? yes / no. If yes: what, and does it go in
Supabase, a file, or nothing persistent.

## Login / security
None / just me / shared login / per-user accounts.

## Talks to anything else?
Other fleet apps, APIs, devices (ESP32, Shelly), Google Drive, email…

## Looks like
Web page / CLI / phone / no UI. Link or attach a sketch if you have one.
Web UIs follow WebUI.md unless stated here.

## Done when
How you'll know it's finished.

## Notes
Anything else.
```

## What happens next

The session that picks up the brief creates the project under
`~/projects/<AppName>` (the brief's Name field) per [ProjectSetup.md](ProjectSetup.md), copies the
brief's answers into `Description.md` (and `Scope.md` for anything
non-trivial — see [ProjectScope.md](ProjectScope.md)), and adds the app to
the fleet map ([FLEET.md](FLEET.md) / [Naming.md](Naming.md)).
