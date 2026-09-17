# HTTPS / certificates (fleet-wide)

Generic HTTPS/TLS rules for **every** box and app on the fleet (DEV,
`BdRPiSrvAMI`, `BdRPiSrvDungeon`, `BdRBirdDetector`, and everything each
one hosts). Top layer — see [`Standards.md`](Standards.md) for the
two-layer doc system; a project only documents where it *deviates*.

## Why this exists

As of 2026-09-17 the fleet had **four different, mutually incompatible
TLS mechanisms** running at once: DEV terminated TLS itself with an
SNI split between a local root CA and a separate `tailscale cert`;
`BdRPiSrvAMI` and `BdRPiSrvDungeon` each generated their **own**
independent root CA, both confusingly named `fleetCA` as if there were
one; and `BdRatsNest` ran its own TLS inside the Python process while
the nginx in front of it proxied to it as if it spoke plain HTTP — a
combination that doesn't work. DEV's nginx was actually down for a full
day (2026-09-16 06:30 onward) because two of these designs were
installed on top of each other. None of this was written down anywhere
as "the" standard, so every project re-derived its own answer. This
doc is that standard.

## The rule: two front doors, two jobs, never blurred

**An app never terminates its own TLS.** Every app is a plain-HTTP
backend bound to `127.0.0.1` (or its own loopback). TLS is terminated
in exactly two places, for two different networks:

### 1. Tailnet access (`*.tail0ed3f6.ts.net`) — owned entirely by `tailscale serve`

This is the primary way these apps get reached day to day. `tailscale
serve` gets a **real, trusted, auto-renewing Let's Encrypt cert** for
the box's `*.ts.net` name with zero scripting — MagicDNS + "HTTPS
Certificates" enabled once in the tailnet admin console
(https://login.tailscale.com/admin/dns) is the only setup step, ever.

- `tailscale serve` proxies **straight to the app's own plain-HTTP
  port** — it does not go through nginx at all for the tailnet path.
  One tailnet port per app (`:443` for the box's main page, `:8443`,
  `:8444`, … for others) rather than distinct hostnames, since MagicDNS
  gives each box exactly one tailnet name:
  ```bash
  tailscale serve --bg --https=443  http://127.0.0.1:<main-app-port>
  tailscale serve --bg --https=8443 http://127.0.0.1:<other-app-port>
  ```
- Nginx must **not** bind the box's Tailscale IP on 443 — that address
  belongs to `tailscale serve`. If nginx currently binds `0.0.0.0:443`
  (all interfaces), scope its `listen` directives to the LAN IP +
  `127.0.0.1` only. If the LAN IP isn't up yet at boot, allow the bind
  anyway with:
  ```
  net.ipv4.ip_nonlocal_bind = 1   # /etc/sysctl.d/99-nonlocal-bind.conf
  ```
- **No manual Let's Encrypt cert scripts, no renewal cron jobs.**
  `tailscale serve` handles issuance and renewal internally — retire
  any `gen-ts-cert.sh`-style script and its crontab entry once adopted.
- **Static SPA builds** served by their own loopback nginx vhost
  (`server_name _`, no TLS) are fine to proxy to directly the same way
  — they were never doing their own TLS to begin with.

### 2. LAN / mDNS access (`*.local`) — nginx, one standalone self-signed cert, no fleet CA

Secondary path, for when the tailnet isn't reachable. Nginx terminates
TLS here with **one standalone self-signed cert per box** — not signed
by any CA, fleet-wide or otherwise.

- **No fleet CA.** Don't generate a root CA, don't distribute one,
  don't ask anyone to install one on a device. Browsers show a one-time
  "not trusted" warning on first visit to a `.local` name; click through
  it and move on. This is the trade Brad is making in exchange for
  never having to think about CA distribution or a 3-boxes-3-CAs mess
  again.
- Cut the leaf long enough that renewal is a rare, deliberate event —
  the CA-distribution problem doesn't exist here, so there's no
  security reason to force short-lived leafs. Regenerate it when the
  SAN list needs a new hostname alias, or the box's LAN IP changes.
- One cert (SAN covering every local hostname alias the box answers to
  — `<name>.local`, the bare mDNS short name, `localhost`, the LAN IP)
  is enough for every vhost nginx serves on that box; no need for a
  cert per app.

### What to retire wherever found

- Any **fleet/root CA** (`fleetCA.*`, `bdr-fleet-ca.*`) and the
  "install this on every device" step that comes with it.
- Any app that opens its **own TLS listener** in-process (`ssl_context=`,
  `openssl` calls inside app code) — switch it to plain HTTP and let
  nginx/`tailscale serve` do TLS instead.
- The **`https+insecure://`** double-hop pattern (`tailscale serve`
  proxying to nginx's self-signed HTTPS listener, ignoring the cert
  error) — proxy straight to the app's plain-HTTP port instead. One
  fewer hop, one fewer cert in the chain to keep in sync.
- Manual `tailscale cert` / Let's Encrypt renewal scripts + their cron
  jobs — `tailscale serve` supersedes them.

## Reference implementation

`BdRVSrvDev/scripts/tailnet-frontdoor.sh` (DEV) is the reference for
the tailnet side — idempotent, proxies straight to each app's port,
scopes nginx off the tailnet IP via the `ip_nonlocal_bind` trick. A
plain single self-signed cert (no CA) for nginx's LAN side is still
being retrofitted on DEV (see `BdRDev/_Requests/rHTTPSStandardDEV.md`).
Nothing is shared as code between projects (`Standards.md`): each box
ports its own version of the script against its own app ports and
hostname.

## Adoption status (update as boxes migrate)

| Box | Tailnet path | LAN path | Status |
| --- | --- | --- | --- |
| DEV (`bdrpisrvdev`) | ✅ `tailscale serve` → app ports directly | ❌ still SNI-split w/ local CA (`BdRDev/tls/`) | mid-migration — nginx was down 2026-09-16→17 from the two designs colliding; LAN side retrofit tracked in `rHTTPSStandardDEV.md` |
| `BdRPiSrvAMI` | ⚠️ `https+insecure` double-hop via nginx | ❌ own `fleetCA` | fan-out: `BdRPiSrvAMI/_Requests/rHTTPSStandardAdopt.md` |
| `BdRPiSrvDungeon` | ⚠️ `https+insecure` double-hop via nginx | ❌ own `fleetCA` | fan-out: `BdRPiSrvDungeon/_Requests/rHTTPSStandardAdopt.md` |
| `BdRatsNest` (on Dungeon) | ❌ app does its own TLS; nginx proxies to it as if plain HTTP (broken as configured) | ❌ same | fan-out: `BdRatsNest/_Requests/rHTTPSStandardAdopt.md` |
| `BdRBirdDetector` | not yet surveyed | not yet surveyed | — |
