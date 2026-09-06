# Batch: AMI web layout / Ecosystem BdRWebGUIDev links / Tailscale SSH headless access

Processed 2026-09-06 12:57 in one unattended pass. Three requests were
sitting in `_Requests/`; two were flagged "just archive" by Brad, one
needed a data update.

---

## 1. rAMI web layout — archived, no action taken here

Brad's note at the top of the file: *"Just Archive This. I am using
Claude Web UI so this will be archived."*

The request is the full BdRPiSrvAMI web-front-door reshuffle (srvhome at
`/`, Supabase on its own `:8000` via `tailscale serve`, PlanBdRad /
BdRAMAssist Supabase-URL cutover). All the repo-side prep it describes
was already committed (see `fleet/srvhome/DEPLOY-STATUS.md` 2026-09-05
entry); everything left is `sudo` / live-restart / cross-box SSH work
that Brad is driving from a Claude Web UI session instead. Nothing to do
in this repo — archived as instructed. The Action block in the original
(below) is the checklist Brad is working from.

## 2. rEcosystem BdRWebGUIDev links — done

Updated the **BdRWebGUIDev** project row in the fleet ecosystem data:

| field | was | now |
|---|---|---|
| `ts_url` | *(empty)* | `http://bdrpisrvdev.tail0ed3f6.ts.net:8430` |
| `status` | `deployed` | `live` |

`local_url`, `runs_on`, `roles`, `database`, `exists` unchanged, per the
request.

Chose `live` (the request left it to discretion) — it matches BdRDev's
own row on this same host: installed + `enabled` systemd unit, actively
serving.

How it was applied (the dashboard Edit/Save UI isn't reachable from an
unattended session): edited `state/ecosystem.json`, then ran
`fleet_db.push_ecosystem()` with the service key from
`state/fleet_db.env` + `SUPABASE_URL=http://127.0.0.1:8000`. Push
returned `True`; a follow-up `fetch_ecosystem()` round-trip confirmed
Supabase now returns `ts_url=http://bdrpisrvdev.tail0ed3f6.ts.net:8430`,
`status=live` for the row, and re-synced `state/ecosystem.json` from the
DB. `state/ecosystem.json` is gitignored, so Supabase + this archive
file are the durable record. No dashboard restart needed — `/api/ecosystem`
reads Supabase live on each request.

## 3. rTailscale SSH headless access — archived, no action taken here

Brad's note at the top: *"Its working now. Can archive."*

The fix (flip the tailnet SSH policy rule from `"action": "check"` to
`"action": "accept"` in the Tailscale admin console) is Brad-only and
has already been applied — Tailscale SSH between fleet boxes now
connects headless. Docs were already updated in the 2026-09-06 pass
(`_Instructions/SSH.md` "Tailscale SSH vs. key-based SSH" section).
Nothing to do here — archived.

---

## Original requests (verbatim)

### rAMI web layout.md

```
READY

Just Archive This. I am using Claude Web UI so this will be archived



# BdRPiSrvAMI web layout — srvhome at `/`, Supabase on its own port

Decisions made 2026-09-05 (answers filled in below): tailscale-serve
Supabase to `:8000`, no auth on srvhome at `/`, this request owns the
PlanBdRad/BdRAMAssist config cutover end-to-end. Repo-side prep is done
(`fleet/srvhome/nginx-snippet.conf` rewritten, `apps.json` URLs fixed,
`README.md`/`DEPLOY-STATUS.md` updated — see
`fleet/srvhome/DEPLOY-STATUS.md`'s 2026-09-05 entry). Everything left
needs `sudo`/a live restart on boxes this session can't touch — see the
Action block below. Also folds in the already-coded (but not yet
redeployed) flashing-Pull-button srvhome UI from the 2026-09-04
DEPLOY-STATUS entry, since step 3 below is the same "copy + kill" visit
either way.

@@@ --- Action --- @@@

1. Give Supabase its own Tailscale-served port

"On the AMI Pi — mirrors how the dev box exposes its dashboard"
tailscale serve --bg --https=8000 http://127.0.0.1:8000

2. Swap the AMI box's `/` from Supabase to srvhome, drop `/status/`

"On the AMI Pi — find the site file (likely
/etc/nginx/sites-available/bdrpiami, or wherever the consolidated
config in ~/projects/BdRPiAMI/nginx/ installs it); inside its
`listen 443 ssl` server block, replace the existing `location /`
(Supabase, proxy_pass to 127.0.0.1:8000) and the existing
`location /status/` block with the single block below, copied from
BdRDev/fleet/srvhome/nginx-snippet.conf. If that block inherits an
auth_basic from the surrounding server block, add `auth_basic off;`
inside it too — the answer below is no auth on srvhome at /."
location / {
    proxy_pass http://127.0.0.1:8610/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

"Apply it"
sudo nginx -t && sudo systemctl reload nginx

3. Redeploy srvhome (picks up the routing-compatible code + the
   2026-09-04 flashing Pull button / status-box UI, already committed
   in BdRDev, not yet live on the Pi)

"On this dev box, or wherever has both repos checked out"
scp -i ~/.ssh/bdrdev_to_bdrpiamiserver \
  fleet/srvhome/srvhome.py fleet/srvhome/apps.json \
  bdr@10.10.10.20:~/projects/BdRPiAMI/srvhome/

"On the AMI Pi — kill the running process; the per-minute cron run.sh
restarts it with the new code"
pkill -f 'srvhome.py'

4. Verify srvhome owns `/` and Supabase is on `:8000`

"From any machine on the tailnet"
curl -s -o /dev/null -w '%{http_code}\n' https://bdrpisrvami.tail0ed3f6.ts.net/
curl -s -o /dev/null -w '%{http_code}\n' https://bdrpisrvami.tail0ed3f6.ts.net:8000/

5. Point PlanBdRad + BdRAMAssist at the new Supabase URL and rebuild

"On the AMI Pi — same anon key, just the URL/port changes; both apps
share this Supabase instance"
# edit ~/projects/PlanBdRad/app/.env:
#   VITE_SUPABASE_URL=https://bdrpisrvami.tail0ed3f6.ts.net:8000
# edit ~/projects/BdRAMAssist/app/.env the same way
cd ~/projects/PlanBdRad && ./build.sh
cd ~/projects/BdRAMAssist && ./build.sh

"Verify each app still loads and logs in after the rebuild"
curl -k -H 'Host: planbdrad.local' https://127.0.0.1/ | head
curl -k -H 'Host: bdramassist.local' https://127.0.0.1/ | head

@@@ ------------- @@@


## Ask

Reshuffle what the AMI box (`BdRPiSrvAMI`, tailnet `bdrpisrvami`, LAN
`bdrpiami` / `10.10.10.20`) serves on its web front door so it matches
the dev box's layout:

- **`/` (`:443`) → srvhome** — the per-server dashboard, the same role
  BdRDev's dashboard plays at `/` on BdRPiSrvDev.
- **Supabase → its own HTTPS port** (mirror the dev box, which puts it on
  `:8000` via `tailscale serve`). Studio + the `/rest/v1` `/auth/v1`
  `/storage/v1` API paths all move together behind that port.
- **Apps stay on their own ports** — `:8443` PlanBdRad, `:8444`
  BdRAMAssist (already done, no change).

End state, both boxes consistent:

| | BdRPiSrvDev (today) | BdRPiSrvAMI (target) |
|---|---|---|
| `/` (`:443`) | BdRDev dashboard | **srvhome** |
| Supabase | `:8000` | **`:8000`** (own port) |
| apps | own ports | `:8443` / `:8444` (unchanged) |

## Why

`/` = Supabase on the AMI box is a historical artifact, not a decision:
that box was set up as a Supabase host first (the self-hosted compose
stack wires its Kong/nginx gateway to `location /`), and PlanBdRad /
BdRAMAssist were bolted on later as separate vhosts/ports. Consequences
today:

- The box has **no useful landing page** — hitting
  `https://bdrpisrvami.tail0ed3f6.ts.net/` just dumps you at Supabase
  Studio's basic-auth login.
- **srvhome is buried at `/status/`** inside the same `listen 443` server
  block as Supabase, so it inherits that block's `auth_basic` and
  prompts for a password too (realm "BdRPiSrvAMI dashboard"). It was put
  there as a path route, not its own port, purely to keep the sudo /
  nginx footprint minimal on first deploy (see
  `fleet/srvhome/nginx-snippet.conf`).
- The fleet ecosystem `ts_url` for the AMI **server** row currently has
  no good value — `rEcosystem web-access columns` set it to
  `https://bdrpisrvami.tail0ed3f6.ts.net`, which is the Supabase login.
  After this change it becomes srvhome, a real front door.

## What moves / what breaks

- **Supabase clients must follow the URL.** That box's Supabase is the
  backend for **PlanBdRad** and **BdRAMAssist**. Their `SUPABASE_URL` /
  build config and Supabase's own auth redirect/site URLs have to change
  to the new `:8000` route. Verify each app still connects + logs in
  after the cutover. (The BdRDev dashboard is **not** affected — its
  fleet data lives in the dev box's Supabase, not this one.)
- **nginx site config** for `bdrpiami` needs its `location /` swapped
  from the Supabase proxy to the srvhome proxy (`127.0.0.1:8610`), the
  `/status/` location dropped, and a new `:8000 ssl` server block (or
  `tailscale serve --https 8000`) added for Supabase. Needs sudo — Brad.
- **srvhome** currently assumes it may be served under `/status/` *or* at
  `/` (its docstring already says so) — confirm relative links / asset
  paths are clean when it owns `/`. `srvhome.conf.json` unchanged (still
  binds `127.0.0.1:8610`).
- **`fleet/srvhome/nginx-snippet.conf`** — rewrite from "add a
  `/status/` sub-path" to "srvhome owns `/`, Supabase gets its own
  port". Update `fleet/srvhome/README.md` + `DEPLOY-STATUS.md` and
  `apps.json` (stale `url` / `url_label` fields).
- **`app/common.py` + the ecosystem data** — AMI server `ts_url` stays
  `https://bdrpisrvami.tail0ed3f6.ts.net` but now points at srvhome;
  add a Supabase entry if we start tracking it. Fold into
  `DRAFT_ecosystem_web_columns.sql` if that hasn't shipped yet, else a
  follow-up data update.
- **The `/status/` regression** noted in
  `fleet/srvhome/DEPLOY-STATUS.md` (401 on all `/status/` paths) is
  mooted by this — don't fix it separately, it goes away.

## Open decisions

??? --- Question --- ???

How does Supabase get its own port on the AMI box?

Options:
1. `tailscale serve --https 8000 http://127.0.0.1:8000` — mirrors the
   dev box exactly (valid `*.ts.net` cert, tailnet-only). (recommended)
2. A dedicated nginx `listen 8000 ssl` server block with the existing
   cert — reachable on the LAN too, not just the tailnet.
3. Keep Supabase reachable at `/supabase/` as a path prefix instead of a
   port — avoids a new port but Supabase Studio / auth don't love
   running under a sub-path.

Answer: 1 — tailscale serve --https 8000, mirrors the dev box.

??? --------------- ???

??? --- Question --- ???

Does srvhome at `/` on the AMI box need auth, or is tailnet-only access
enough? (The dev box's dashboard at `/` is unauthenticated — tailnet +
LAN-bound nginx is the boundary.)

Options:
1. No auth — same trust model as the dev box dashboard. (recommended)
2. Keep an `auth_basic` on it (needs an htpasswd file on the box).

Answer: 1 — no auth, same trust model as the dev box dashboard.

??? --------------- ???

??? --- Question --- ???

Scope of the app-config follow-up — do PlanBdRad and BdRAMAssist get
their `SUPABASE_URL` updated as part of *this* request, or is that
split into their own requests in those repos?

Options:
1. Do it here — this request owns the whole cutover, cross-repo.
2. This request does the AMI box + BdRDev docs; PlanBdRad / BdRAMAssist
   each get a one-line request in their own `_Requests/`.

Answer: 1 — owned end-to-end here; the app-config step is in the
Action block above (step 5).

??? --------------- ???

## Where this touches

- **AMI box nginx** (`/etc/nginx/sites-*/bdrpiami`) — sudo, Brad.
- **AMI box `tailscale serve`** config — Brad.
- `fleet/srvhome/nginx-snippet.conf`, `README.md`, `DEPLOY-STATUS.md`,
  `apps.json`
- `app/common.py` `DEFAULT_ECOSYSTEM` + ecosystem `ts_url` data
- `supabase/DRAFT_ecosystem_web_columns.sql` (if still unshipped) or a
  follow-up
- `README.md` ecosystem section, `supabase/DATA_MODEL.md` if server
  `ts_url` semantics get a note
- PlanBdRad / BdRAMAssist Supabase client config (see Q3)

## Not in scope

- Renaming the AMI box's on-box hostname / Tailscale node
  (`bdrpiami` → `bdrpisrvami`) — tracked separately in
  `~/projects/CLAUDE.md`.
- Moving the dev box's Supabase (already on its own port).
```

### rEcosystem BdRWebGUIDev links.md

```
READY

Update the **BdRWebGUIDev** project row in the Ecosystem table (dashboard
Ecosystem tab → Edit / Save, which pushes to Supabase + mirrors
`state/ecosystem.json`).

## What changed

BdRWebGUIDev is now fully stood up on BdRPiSrvDev:

- `systemd/bdrwebguidev.service` is installed, `enabled`, and running
  (curl `127.0.0.1:8430/` → 200).
- The deploy key + SSH remote swap are done; `origin` is
  `git@github.com-bdrwebguidev:bDotRad/BdRWebGUIDev.git`.
- It serves on the tailnet now — confirmed
  `http://100.116.147.74:8430/` → 200. Plain HTTP on :8430, no nginx /
  no TLS (direct, same as the request that set it up intended).

## Entries to set

Current row:

| field | current | set to |
|---|---|---|
| `local_url` | `http://bdrpisrvdev.local:8430` | *(unchanged — LAN mDNS, direct on :8430)* |
| `ts_url` | *(empty)* | `http://bdrpisrvdev.tail0ed3f6.ts.net:8430` |
| `status` | `deployed` | `live` — installed + enabled service, actively serving (matches BdRDev's own row on this host). Leave as `deployed` if you'd rather reserve `live` for something else. |

`runs_on` (BdRPiSrvDev), `roles` (pm/web/db/doco), `database` (none),
`exists` (true) all stay as they are.

## Note (no action needed here)

The `BdRPiSrvDev` **server** row already has the right `ts_url`
(`https://bdrpisrvdev.tail0ed3f6.ts.net`) — only the BdRWebGUIDev
project row is missing its tailnet link.
```

### rTailscale SSH headless access.md

```
READY

Its working now.
Can archive


# Tailscale SSH between fleet boxes needs re-auth — blocks headless SSH

## Issue

SSH *over Tailscale* to a fleet box now stops at an interactive check:

```
# Tailscale SSH requires an additional check.
# To authenticate, visit: https://login.tailscale.com/a/<token>
```

Seen 2026-09-06 from this box (`bdrpisrvdev`) to the AMI Pi:
`ssh bdr@100.86.25.88` (also the `*.tail0ed3f6.ts.net` name). A human can
click the URL; an **unattended scheduler session hangs on it forever**.

## When

Only the Tailscale SSH path. **Key-based SSH over the LAN is fine** —
`ssh BdRPiAMI` (→ `bdr@10.10.10.20`, key `bdrdev_to_bdrpiamiserver`)
connects headless, no prompt. Deploy scripts and unattended sessions
should keep using LAN IPs / `~/.ssh/config` aliases, not `*.ts.net`
names, regardless of this fix.

## Cause

Not a key, expiry, or connectivity problem — node keys are valid to 2027
and both Pis show `Online: true`. `tailscale debug netmap` on this box
shows the effective SSH policy: a rule with
`action.holdAndDelegate` (= check mode) matching every fleet node IP
(`100.116.147.74` this box, `100.86.25.88` AMI, the laptop, the phone),
plus an already-**expired** temporary `accept` rule
(`ruleExpires: 2026-09-05...`) — the leftover of the last successful
check. Check approvals only last one `checkPeriod` (default 12h), then
every new connection re-prompts. Headless boxes can never complete the
browser check at all, so they re-prompt on *every* connection.

This is the default rule Tailscale's admin console adds when you enable
Tailscale SSH — `"action": "check"`, not `"accept"`. Nobody chose it
deliberately.

## Solution — needs the tailnet admin console (Brad)

@@@ --- Action --- @@@

1. Open the tailnet policy editor

"In a browser"
https://login.tailscale.com/admin/acls/file

2. In the `"ssh"` array, find the rule with `"action": "check"` (its
   `dst` is probably `["autogroup:self"]`, `src` `["autogroup:member"]`).
   Change just that one word:

"was"
"action": "check",

"make it"
"action": "accept",

"(Optional, if you want to keep tap-to-approve for laptops/phones but
not server-to-server: instead of the edit above, add a second rule
BEFORE it with action accept and src/dst set to the servers' tag, and
leave the check rule for everything else.)"

3. Save (Tailscale validates the policy on save).

4. Verify from this dev box — should print `BdRPiSrvAMI` with no prompt

"On bdrpisrvdev"
ssh -o BatchMode=yes bdr@100.86.25.88 hostname

@@@ ------------- @@@

## Notes

- If there is **no** `ssh` rule matching at all and the message was
  actually "access denied", that's a different fix (add a rule) — but
  the observed text was the "additional check" one, which only appears
  when a `check`-action rule matches.
- Docs already updated to reflect this: `_Instructions/SSH.md` has a new
  "Tailscale SSH vs. key-based SSH" section and a refreshed inventory
  (2026-09-06 pass).
```
