# TLS for the BdRDev dashboard (DEV)

Follows the fleet-wide standard: `BdRDev/_Instructions/HTTPS.md`. Two
front doors, two jobs:

| URL | TLS owned by | Trust needed |
| --- | --- | --- |
| `https://bdrpisrvdev.tail0ed3f6.ts.net` (Tailscale) | `tailscale serve` — real Let's Encrypt cert, auto-renewing | none — trusted everywhere already |
| `https://bdrpisrvdev.local` / `https://bdrdev.local` / LAN IP | nginx, standalone self-signed leaf (`bdrpisrvdev.local.crt`) | none — click through the one-time browser warning |

**No fleet CA.** `ca/_deprecated/` holds the old per-box root CA this
box used to sign its LAN leaf with — retired, see the note in that
folder. The current LAN cert is a standalone self-signed leaf, not
signed by anything.

## Files

| File | Tracked? | What |
| --- | --- | --- |
| `bdrpisrvdev.local.crt` / `.key` | crt only | standalone self-signed LAN/mDNS leaf (5-year) |
| `gen-selfsigned.sh` | yes | (re)issue the LAN leaf — run whenever the SAN list needs a new alias, or the LAN IP changes |
| `ca/_deprecated/` | yes (crt only) | old root CA, no longer used — do not resurrect |
| `bdrdev.local.crt` / `.key`, `gen-cert.sh` | legacy | superseded by `bdrpisrvdev.local.*` / `gen-selfsigned.sh`; safe to remove once nothing references them |
| `bdrpisrvdev.tail0ed3f6.ts.net.crt` / `.key`, `gen-ts-cert.sh` | legacy | no longer needed — `tailscale serve` issues/renews its own cert internally now |

## Regenerating the LAN cert

```bash
cd /home/bdr/projects/BdRDev/tls
./gen-selfsigned.sh
sudo systemctl restart nginx   # Brad — no sudo in Claude sessions
```

Rerun after: the LAN IP changes (DHCP renewal — this box has moved
before, `10.10.8.11` → `10.10.8.20`), or a new hostname alias needs
adding to the SAN list.

## Tailnet cert

Nothing to do here — `tailscale serve` (see
`BdRVSrvDev/scripts/tailnet-frontdoor.sh`) issues and renews the
`*.ts.net` cert on its own. The old `gen-ts-cert.sh` + cron-renewal
approach is retired; no crontab entry for it was ever actually
installed (checked 2026-09-17), so there's nothing to remove.
