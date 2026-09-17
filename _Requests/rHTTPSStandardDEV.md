WAITING RESPONSE

# nginx down on DEV + adopt the new fleet HTTPS standard

## The urgent part: nginx has been down since 2026-09-16 06:30

`/etc/nginx/sites-enabled/` has **both** `bdrdev` (old, from
`BdRDev/nginx/bdrdev.conf`) and `bdrpisrvdev` (newer, from
`BdRVSrvDev/scripts/tailnet-frontdoor.sh`) enabled at once. The second
one's `ssl_certificate` pointed at
`/home/bdr/projects/BdRDev/tls/bdrpisrvdev.local.crt`, which had never
been generated — `nginx -t` fails outright
(`BIO_new_file() ... No such file or directory`) and the whole service
has been in `failed` state ever since. Right now the dashboard is only
reachable via `tailscale serve` bypassing nginx entirely — LAN/`.local`
HTTPS is completely broken. This is almost certainly what you're
hitting.

## Why this happened, and the actual fix

Two different TLS designs got installed on top of each other on this
box (old SNI-split-with-a-local-CA in `bdrdev.conf`, newer
LAN-only-nginx-plus-`tailscale-serve` in `tailnet-frontdoor.sh`), and
neither was ever fully retired. Rather than patch around it, I've
written up the actual fleet-wide standard this exposed the fleet never
had — see **`BdRDev/_Instructions/HTTPS.md`**: `tailscale serve` owns
100% of tailnet HTTPS (real, auto-renewing certs, zero maintenance);
nginx only handles LAN/`.local` access, with one standalone self-signed
cert per box — **no fleet CA** (the old scheme had three boxes each
generating their own CA, confusingly all named `fleetCA`, none of which
actually trusted each other).

I've already done everything that doesn't need sudo:

- Generated `BdRDev/tls/bdrpisrvdev.local.crt`/`.key` — a standalone
  self-signed cert (no CA), 5-year, SAN covers
  `bdrpisrvdev.local`/`bdrpisrvdev`/`bdrdev.local`/`BdRDev`/`localhost`/
  `127.0.0.1`/the current LAN IP. This is the exact file
  `tailnet-frontdoor.sh`'s `bdrpisrvdev` nginx site already expects.
- Added `BdRDev/tls/gen-selfsigned.sh` to reissue it later (LAN IP
  change, new hostname alias) — no sudo needed to run it, just a
  `systemctl restart nginx` after.
- Moved the old root CA to `BdRDev/tls/ca/_deprecated/` (not deleted —
  see the note in that folder) and rewrote `BdRDev/tls/README.md` to
  match the new approach.
- `tailnet-frontdoor.sh` itself needs no changes — it's already the
  reference implementation for the tailnet side (confirmed via
  `tailscale serve status`: it's already correctly proxying the tailnet
  hostname straight to each app's port, bypassing nginx for that path
  entirely).

What's left needs your `sudo`:

@@@ --- Action --- @@@

1. Retire the old site, keep only the LAN-only one

"Remove the old bdrdev site (superseded by bdrpisrvdev)"
sudo rm -f /etc/nginx/sites-enabled/bdrdev /etc/nginx/sites-available/bdrdev

2. Regenerate the LAN-only site fresh (picks up the current LAN IP,
   writes it to sites-available + sites-enabled, restarts nginx, and
   re-asserts the tailscale serve mappings — safe to re-run any time)

"Re-run the tailnet front-door script"
sudo bash /home/bdr/projects/BdRVSrvDev/scripts/tailnet-frontdoor.sh

3. Verify both paths work

"LAN, over the new standalone self-signed cert (expect a self-signed warning first time — that's expected now, no CA to install)"
curl -sk -o /dev/null -w '%{http_code}\n' https://bdrpisrvdev.local/

"Tailnet, over the real Tailscale cert"
curl -s -o /dev/null -w '%{http_code}\n' https://bdrpisrvdev.tail0ed3f6.ts.net/

@@@ ------------- @@@

Once both curls come back 200, flip this to `READY` (or just archive
it) — I'll update `HTTPS.md`'s adoption table for DEV and clean up the
legacy `bdrdev.local.*` / `gen-cert.sh` / `gen-ts-cert.sh` files in a
follow-up pass. Fan-out requests for the same standard are already
sitting in `BdRPiSrvAMI/_Requests/rHTTPSStandardAdopt.md`,
`BdRPiSrvDungeon/_Requests/rHTTPSStandardAdopt.md`, and
`BdRatsNest/_Requests/rHTTPSStandardAdopt.md`.
