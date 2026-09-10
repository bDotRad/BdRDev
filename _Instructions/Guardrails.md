# Guardrails — what an unattended session must never do on its own

Fleet-wide layer (see [`Standards.md`](Standards.md)). Written 2026-09-08.
Companion to [`SessionScope.md`](SessionScope.md) (how sessions run) and
[`Requests.md`](Requests.md) (the Action/Question block formats).

Most fleet sessions run **unattended** — woken by the scheduler or spun
up by CloudCLI, with nobody watching the terminal. Auto-mode's safety
classifier catches some dangerous actions, but not all, and the
`srvhome` teardown on 2026-09-08 went straight through it. These are hard
rules, not judgement calls.

## Stay in your lane

- **Only touch your own project's directory.** Never `rm`, `mv`, or edit
  anything under `~/projects/<other-project>/` or `~/projects/` itself.
- If a request needs work in another project, **say so and stop** — write
  which project it belongs in. The scheduler/dashboard have the
  cross-project view; you don't.
- Don't `git push` from any box except `DEV`. App-host edits funnel back
  through `DEV` — see [`AppServerSync.md`](AppServerSync.md).

## Never do these autonomously — Action block to Brad instead

Decline the interactive prompt, set the request to `WAITING RESPONSE`,
write an Action block ([`Requests.md`](Requests.md)), end the turn.

1. **Anything served at `/`.** Changing, disabling, or repointing the
   nginx root on any box. `/` is that box's status/control page
   (`DEV` → BdRDev dashboard, `AMI` → `srvhome`), never an app. See
   [`Naming.md`](Naming.md).
2. **Tearing down or disabling a running service** — `systemctl
   stop/disable`, removing a unit, killing a keepalive crontab, deleting
   a deployed checkout.
3. **`sudo` anything.**
4. **Restarting a live service** — including on this box. `sudo systemctl
   restart bdrdev-*` etc. go to Brad.
5. **Remote daemon control** — starting/restarting anything over SSH on
   another box.
6. **Destructive git** — `reset --hard`, `push --force`, `clean -fdx`,
   branch deletion on a shared remote.
7. **Schema DDL against a live database** — `sql-developer` writes
   migrations; Brad runs them (see each project's `SQL_RUN.md`).
8. **Rotating / relocating secrets or keys**, editing `~/.ssh/config`.

## When a request seems to ask for one of these

Don't just refuse silently and archive it. Write a **Question block**
confirming the intent and offering the safe framing, e.g.:

> The request says "make AMAssist the main page". On `AMI`, `/` is
> `srvhome` (the box status page), not an app — see `Naming.md`. Did you
> mean (1) add a link to AMAssist from srvhome, (2) actually replace
> srvhome at `/` [needs nginx + sudo, Action block], or (3) something
> else?

A wrong guess here is expensive to undo. A round-trip question is not.

## What you *can* do unattended

- Read anything, anywhere on the box (and read-only over SSH).
- Edit, build, and test within your own project.
- `git commit` and `git push` **from `DEV`** for your own project.
- Copy files to another box over SSH (not execute).
- Write Action/Question blocks and `.claude-status/*` files.
