# Project scope standard — `Scope.md`

Fleet-wide layer (see [`Standards.md`](Standards.md)). Written
2026-10-10 when the `BdRESP32Radar` project was started and there was
no fleet convention for a scope document.

## What it is

`Scope.md` at a project's repo root is the agreed statement of **what
the project will build, what it will not, and how we'll know it's
done** — written *before* the code. It's the document a fresh session
reads to stop re-litigating the project's boundaries.

How it differs from the other standard files
([`ProjectSetup.md`](ProjectSetup.md)):

| file | audience | answers |
|---|---|---|
| `Description.md` | human, at a glance | what is this project, where's its repo |
| `CLAUDE.md` | the agent | how to operate here, gotchas |
| `Scope.md` | both | what's in / out, the milestones, the decisions, "done when" |
| `_Requests/r*.md` | the scheduler | one unit of work at a time |

A project doesn't *need* a `Scope.md` — small or self-explanatory
projects can live on `Description.md` alone. Write one when the project
is new and non-trivial, when it's a learning project with a defined
goal, or when Brad asks for one.

## Required sections, in this order

1. **Header** — title, then a short block:
   `Status:` (`DRAFT` / `AGREED` / `SUPERSEDED`), `Created:` (absolute
   date), `Owner:`, `Handle:` / canonical name (per
   [`Naming.md`](Naming.md)), `Runs on:`.
2. **Purpose** — one or two paragraphs: what and why. For a learning
   project, list the **learning objectives** here too.
3. **In scope** — bullets. Concrete, testable things.
4. **Out of scope** — bullets. Just as important as in-scope; list the
   things someone might reasonably assume are included.
5. **Platform & constraints** — hardware, stack, hosting, network,
   power, licensing / regulatory. Mark anything not yet verified as
   *unverified*.
6. **Architecture** — a short sketch (text or ASCII diagram) of the
   parts and how data flows between them.
7. **Milestones** — numbered `M0`, `M1`, …, each **sized so one session
   can finish it** ([`SessionScope.md`](SessionScope.md)), each with its
   own "done when". Each milestone becomes one `READY` request
   ([`Requests.md`](Requests.md)) when it's time to build it.
8. **Deviations from fleet standards** — any Layer-1 rule this project
   deliberately breaks, with the reason (e.g. a themed UI that doesn't
   use the [`WebUI.md`](WebUI.md) look & feel).
9. **Decisions** — two lists:
   - *Made* — the decision and a one-line why.
   - *Open questions* — front-loaded so Brad can answer them in one
     pass. Each states the recommended default, so a session can proceed
     on the default if no answer arrives.
10. **Risks** — what could go wrong and the mitigation.
11. **Acceptance criteria** — the overall project "done when".
12. **References** — links, and files in `References/`.
13. **Change log** — one dated line per material change to scope.

Sections that genuinely don't apply stay in with "None." rather than
being dropped — the point is that a reader can tell it was considered.

## Rules

- **Status gates building.** While a `Scope.md` is `DRAFT`, sessions
  may research and prototype but should not treat open questions as
  settled. Brad flips it to `AGREED`.
- **Change it in place**, don't fork it: edit the section and add a
  change-log line. A scope that's been replaced wholesale is marked
  `SUPERSEDED` with a pointer to the new one.
- **Use canonical names** from [`Naming.md`](Naming.md) throughout.
- If the scope establishes a deployment fact (a new app, port, box),
  the fleet-map step in [`Requests.md`](Requests.md) applies once that
  fact becomes real — not at scoping time.
