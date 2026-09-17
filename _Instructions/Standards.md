# The two-layer standards system

Requested 2026-08-28 (`rDocumentationrequirements`). How fleet-wide
conventions and project-specific instructions fit together, so every
project gets the same overall look, feel and process **unless it says
otherwise**.

## The two layers

**Layer 1 — generic / fleet-wide (this folder,
`BdRDev/_Instructions/`).**
The canonical copy of every cross-project convention lives here and
*only* here. Other projects do **not** copy these files; a session
working in any project should just know they exist and apply.

| doc | covers |
|---|---|
| [`Standards.md`](Standards.md) | this two-layer model |
| [`Naming.md`](Naming.md) | the one canonical name + short handle for every box and project; aliases never to use |
| [`FLEET.md`](FLEET.md) | the fleet map — boxes, what runs where, the SSH matrix |
| [`Guardrails.md`](Guardrails.md) | what an unattended session must never do on its own (destructive / infra actions → Action block) |
| [`SessionScope.md`](SessionScope.md) | how to size and run a session; context as working memory |
| [`WebUI.md`](WebUI.md) | web look & feel, versioning (7-char SHA), the table-editing Edit/Save/Cancel pattern |
| [`ProjectSetup.md`](ProjectSetup.md) | the standard project folder shape; "Setup Project" |
| [`Requests.md`](Requests.md) | the `_Requests/` intake + archive convention; the fleet-map-update step |
| [`BdRDev.md`](BdRDev.md) | scheduler wake/kill orchestration (copied into other projects' CLAUDE.md context) |
| [`SSH.md`](SSH.md) | fleet SSH key naming; Tailscale-SSH vs LAN-key |
| [`AppServerSync.md`](AppServerSync.md) | funnelling app-server edits back through the dev box |
| server provisioning | worked example: `~/projects/BdRPiAMI-PROVISION.md` |

Each fleet box also carries a generated `~/projects/CLAUDE.md` (one level
above the repos) stating that box's identity, what it serves at `/`, its
SSH reach, and the guardrails — so every session inherits it from cwd.
Canonical content is derived from `Naming.md` + `FLEET.md`; the AMI box's
tracked copy is `BdRPiSrvAMI/projects-root-CLAUDE.md`.

**Layer 2 — project-specific (each project's own
`CLAUDE.md` + `_Instructions/` + `Description.md`).**
A project documents only what is *particular to it* — its domain, its
deploy specifics, its gotchas — and any **deliberate deviation** from a
Layer-1 standard, stated explicitly with the reason.

## Precedence

1. A project's own docs win **where they explicitly override** a
   Layer-1 rule ("Tables here save per-cell because …").
2. Silence = inherit. If the project says nothing about tables, forms,
   versioning, colours, request handling, etc., the Layer-1 doc is the
   spec.
3. Don't fork a Layer-1 doc into a project. If a rule needs changing
   for everyone, change it here; if only for one project, override it in
   that project with a one-line pointer back to this folder.

## Adding a new standard

Put it in the right Layer-1 doc here (or add a new one and list it in
the table above), phrased as a rule that applies fleet-wide. Then, if an
existing project already violates it, either fix the project or record
the deviation in that project's docs.
