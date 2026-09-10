WAITING RESPONSE

<!-- 2026-09-09 diagnostic writeup; 2026-09-11 Brad said "build away".
     PROGRESS 2026-09-11:
       - Task 1 (final port): already done by 026abbd — the fork is
         current with canonical through ad12f18 (the last fleet/srvhome
         commit). Nothing to port.
       - Task 4 (page redesign): DONE in ~/projects/BdRPiSrvAMI working
         tree — header sub-line removed, two tabs (App status / Server &
         app info), chat box always-visible below. Compiles + renders +
         serves 200 locally. NOT yet committed/pushed (tool-permission
         prompts started timing out mid-session).
       - Task 2 (BdRDev cleanup): NOT started.
       - Task 3 (Brad Action block): still outstanding.
     Q1: going with option 1 (repoint WebUI.md refs to the dashboard's
     render_site_header) unless Brad says otherwise. -->

# Make `BdRPiSrvAMI` the canonical home of `srvhome` — finish the move, fix the docs

## Decision (Brad, 2026-09-09)

> "just make BdRPiSrvAMI the project and the page that runs"

`srvhome` (the per-box status page at `/` on `AMI`) is now **owned by the
`bDotRad/BdRPiSrvAMI` config repo**. `BdRDev/fleet/srvhome/` stops being
canonical and goes away. No `bDotRad/BdRDev` checkout on `AMI`.

## How we got here (for the archive)

Two sessions made opposite calls 36 min apart on 2026-09-08 and neither
reconciled the other's docs:

- **2026-09-07** `4f9e889` + `fleet/srvhome/DEPLOY-STATUS.md`: "deploy
  srvhome as a read-only `bDotRad/BdRDev` checkout at
  `~/projects/BdRPiAMI/BdRDev`, run from `fleet/srvhome/` inside it."
  Every BdRDev doc still describes this.
- **2026-09-08 12:07** `ad12f18`: canonical `fleet/srvhome/` still being
  actively developed on that assumption.
- **2026-09-08 12:43** `026abbd` (on `bDotRad/BdRPiSrvAMI`): a session
  reversed it — copied srvhome into the config repo as `srvhome/`,
  adapted `srvhome.py` (logo path → alongside the script, dropped the
  `<repo>/fleet/srvhome/` layout assumption, footer/self-panel repointed
  at `bDotRad/BdRPiSrvAMI`), bundled `rat-logo.png`. Commit message:
  *"so the AMI box stops running its / page from a BdRDev checkout.
  Next: cut the Pi over … and delete `~/projects/BdRPiAMI/BdRDev`."*

That cutover already happened. **Current live state on `AMI`:**
`~/projects/BdRPiAMI/BdRDev` is gone; srvhome runs from
`~/projects/BdRPiAMI/srvhome/` (a subdir of the `BdRPiSrvAMI` checkout,
branch `main` @ `026abbd`), per-minute `run.sh` cron keepalive, nginx
still proxies `127.0.0.1:8610` at `location /`. Process healthy.

So the screenshot's "srvhome · HEAD 026abbd · branch main · up to date"
pill is honest — it just tracks the config repo now. The problem is
purely that `BdRDev/fleet/srvhome/` is still nominally canonical and
every BdRDev doc points at the retired model. This request makes the
codebase stop lying and locks the config repo in as the single source.

## State check already done

- `BdRPiSrvAMI/srvhome/` is complete and self-consistent (has
  `rat-logo.png`, `LOGO_PATH` alongside, footer + self-panel repointed).
  Only file dropped vs `BdRDev/fleet/srvhome/` is `DEPLOY-STATUS.md`
  (BdRDev-specific — correctly gone).
- `srvhome/srvhome.py` in the config repo forked at 12:43; `ad12f18`
  ("surface an unreachable dashboard instead of showing stale data")
  landed at 12:07 the same day — **needs verifying** it was carried
  across, plus anything in `fleet/srvhome/` after `ad12f18`
  (`git -C ~/projects/BdRDev log --oneline ad12f18..HEAD -- fleet/srvhome/`).
- `store.py` / `record_deploy.py` are byte-identical between the two.

---

## Task 1 — `BdRPiSrvAMI` repo (work in `~/projects/BdRPiSrvAMI` on DEV)

Belongs to that project, not BdRDev — a session there should:

1. Diff `BdRPiSrvAMI/srvhome/srvhome.py` against
   `BdRDev` `HEAD:fleet/srvhome/srvhome.py` and port any missing
   behaviour changes (expected: `ad12f18` and any later `fleet/srvhome/`
   commits) — this is the **last** sync; after it the BdRDev copy is
   deleted.
2. Confirm `srvhome/README.md` fully owns it (no "canonical source:
   BdRDev" language left anywhere — footer string already fixed in
   `026abbd`, check the README prose too).
3. `srvhome/install.sh` self-track block: verify `SRVHOME_APP_PATH` /
   the `--path` filter point at `srvhome` (not `fleet/srvhome`) so the
   self deploy-history and post-merge hook are correct for this repo
   layout.
4. Commit + push from DEV (never from AMI).

## Task 2 — `BdRDev` repo (this project)

Only after Task 1 is pushed:

1. `git rm -r fleet/srvhome/`. Leave `fleet/README.md` (or a short
   `fleet/SRVHOME-MOVED.md`) pointing at `bDotRad/BdRPiSrvAMI` →
   `srvhome/`.
2. Docs to rewrite so srvhome reads as "lives in `bDotRad/BdRPiSrvAMI`,
   not here":
   - `CLAUDE.md` — the "srvhome runs from a read-only BdRDev checkout"
     bullet in "Things that aren't obvious"; any `fleet/srvhome`
     pointer.
   - `_Instructions/FLEET.md` — AMI "what runs where" row (drop the
     `~/projects/BdRPiAMI/BdRDev` sentence, say it runs from the
     `BdRPiSrvAMI` checkout's `srvhome/`); "Projects → deploy target"
     table; remove `~/projects/BdRPiAMI/BdRDev` everywhere; bump "last
     verified".
   - `_Instructions/Naming.md` — lines 42, 48, 60-66: `srvhome`
     canonical source is now `bDotRad/BdRPiSrvAMI` `/srvhome/`; drop
     "source" from the `DEV`/`BdRDev` role blurb.
   - `_Instructions/Guardrails.md` — the srvhome examples still stand
     (it's still "the page at `/` on AMI, not an app"); just fix any
     "canonical source" path.
   - `_Instructions/WebUI.md` — lines 23, 36-37, 126, 132-135, 229:
     these point at `fleet/srvhome/srvhome.py` as the **reference
     implementation** of the standard header / degraded two-line form.
     Once the file leaves this repo a BdRDev session can't open it.
     Repoint to the dashboard's own `render_site_header`
     (`app/…`) as the in-repo reference and note the srvhome copy lives
     in `bDotRad/BdRPiSrvAMI`. **See Q1.**
   - `_Instructions/SSH.md` line 68 — the "restart srvhome on the Pi"
     example is fine, leave it.
   - `README.md` "Conventions this implements" / any `fleet/srvhome`
     mention.
   - `app/common.py` ~line 254 — the `BdRAMI` ecosystem seed row:
     `local_url` is `https://bdrpiami.local` (stale hostname → should be
     `bdrpisrvami.local`); keep `database: "SQLite — deploy history
     (srvhome.db)"`.
   - `_Requests/rFleetMap.md` — it's `NOT READY`; update its srvhome /
     `is_app` / `serves_root` references to match (srvhome source repo,
     not `BdRDev/fleet/srvhome`).
   - `_Notes/260829_independent_session_fleet_review.md` — historical
     note, leave as-is.
3. Fleet map / Supabase (per `Requests.md` § "Keeping the fleet map
   current"): update `servers.serves_root` for AMI and the srvhome /
   `BdRAMI` project row so the ecosystem data matches — srvhome's repo
   is `bDotRad/BdRPiSrvAMI`, it is not an app.
4. Commit + push.

## Task 3 — Action block for Brad (on `AMI`)

@@@ --- Action --- @@@

1. Apply the 7 pending OS updates (unrelated to srvhome; no reboot flag set)

"on AMI"
sudo apt update && sudo apt upgrade -y

2. Pull the last srvhome catch-up commit (after Task 1 is pushed) and restart

"on AMI — refresh the running copy"
cd ~/projects/BdRPiAMI && git pull --ff-only
pkill -f 'BdRPiAMI/srvhome/srvhome.py'   # per-minute run.sh cron restarts it

"on AMI — re-run the installer from the config-repo layout so the
post-merge hooks + deploy-history backfill match srvhome living at
~/projects/BdRPiAMI/srvhome/ (not a fleet/srvhome/ checkout)"
cd ~/projects/BdRPiAMI/srvhome && ./install.sh

"on AMI — verify"
curl -s http://127.0.0.1:8610/healthz
curl -sI https://bdrpisrvami.local/ | head -1

@@@ ------------- @@@

## Decisions

??? --- Question --- ???

Q1. `_Instructions/WebUI.md` points at `fleet/srvhome/srvhome.py` as the
reference implementation of the standard header block (esp. the degraded
two-line form and the running-vs-origin deploy-status line). Once
srvhome moves out, BdRDev sessions can't open that file. Repoint those
references to:

Options:
1. The dashboard's own `render_site_header` in `app/` as the in-repo
   reference, with a note that srvhome (`bDotRad/BdRPiSrvAMI /srvhome/`)
   is the other live example (recommended)
2. Keep pointing at srvhome by repo-qualified path
   (`bDotRad/BdRPiSrvAMI /srvhome/srvhome.py`) even though it's not
   checked out here
3. Vendor just `srvhome.py` back into BdRDev as a read-only reference
   copy (rejected the "one source" goal — probably not)

Answer:

??? --------------- ???
