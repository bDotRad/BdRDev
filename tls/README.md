# TLS for the BdRDev dashboard

Goal: reach the dashboard over HTTPS **without a browser warning**, from
every device Brad uses.

There are two front doors and two certs:

| URL | Cert | Trust needed |
| --- | --- | --- |
| `https://bdrpisrvdev.tail0ed3f6.ts.net` (Tailscale) | Let's Encrypt, via `tailscale cert` | none — trusted everywhere already |
| `https://bdrpisrvdev.local` / `https://bdrdev.local` / LAN IP | leaf signed by **BdR Fleet Local Root CA** (`ca/bdr-fleet-ca.crt`) | install the CA once per device |

nginx (`../nginx/bdrdev.conf`) serves the right cert per SNI; the local-CA
vhost is also the default, so hitting the box by raw IP uses it too.

## Files

| File | Tracked? | What |
| --- | --- | --- |
| `ca/bdr-fleet-ca.crt` | yes | local root CA — public, safe to share, install on devices |
| `ca/bdr-fleet-ca.key` | **no** | local root CA private key — never commit, never leaves the box |
| `bdrdev.local.crt` / `.key` | crt only | LAN/mDNS leaf, signed by the CA (2-year) |
| `bdrpisrvdev.tail0ed3f6.ts.net.crt` / `.key` | no | Tailscale Let's Encrypt cert (90-day) |
| `gen-cert.sh` | yes | (re)create the CA + issue the LAN leaf |
| `gen-ts-cert.sh` | yes | issue / renew the Tailscale cert |

## First-time setup

```bash
cd /home/bdr/projects/BdRDev/tls

# 1. local CA + LAN leaf
./gen-cert.sh

# 2. Tailscale cert  (needs MagicDNS + "HTTPS Certificates" enabled in the
#    tailnet admin console: https://login.tailscale.com/admin/dns )
./gen-ts-cert.sh

# 3. nginx  (Brad — no sudo in the Claude sessions)
sudo cp /home/bdr/projects/BdRDev/nginx/bdrdev.conf /etc/nginx/sites-available/bdrdev
sudo ln -sf /etc/nginx/sites-available/bdrdev /etc/nginx/sites-enabled/bdrdev
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

## Trusting the local CA on each device

Only needed for the `*.local` / LAN-IP URLs. Copy `ca/bdr-fleet-ca.crt`
to the device first. Verify the fingerprint matches:

```bash
openssl x509 -in ca/bdr-fleet-ca.crt -noout -fingerprint -sha256
```

- **Debian/Ubuntu (this box, other Pis):**
  ```bash
  sudo cp bdr-fleet-ca.crt /usr/local/share/ca-certificates/bdr-fleet-ca.crt
  sudo update-ca-certificates
  ```
- **Firefox:** Settings → Privacy & Security → Certificates → View
  Certificates → Authorities → Import → tick "trust to identify websites".
- **macOS:** double-click the .crt → Keychain Access → System → set
  "When using this certificate: Always Trust".
- **Windows:** `certutil -addstore -f Root bdr-fleet-ca.crt` (admin), or
  MMC → Certificates (Local Computer) → Trusted Root Certification
  Authorities.
- **Android:** Settings → Security → Encryption & credentials → Install a
  certificate → CA certificate. (Chrome on Android also honours the
  Tailscale URL with no install — prefer that on the phone.)
- **iOS:** AirDrop/email the .crt → install profile → Settings → General →
  About → Certificate Trust Settings → enable full trust.

## Renewal

- **LAN leaf** — 2-year. `./gen-cert.sh` again before it expires (the CA
  is reused, so no device re-trust needed). Also rerun it if the box's
  **LAN IP changes** — the SAN pins `10.10.8.11`; a DHCP move breaks
  IP-based access until reissued (name-based access is unaffected).
- **Tailscale cert** — 90-day, so automate it. Add to `crontab -e` for
  user `bdr`:
  ```cron
  17 4 * * * /home/bdr/projects/BdRDev/tls/gen-ts-cert.sh >> /home/bdr/projects/BdRDev/tls/renew.log 2>&1
  ```
  `tailscale cert` is a no-op until the cert is within 30 days of expiry.

### Letting the cron reload nginx without a password

`gen-ts-cert.sh` tries `sudo -n systemctl reload nginx` after a renewal
that changed the cert. To let that succeed, Brad adds one sudoers line:

```
sudo visudo -f /etc/sudoers.d/bdr-nginx-reload
# contents:
bdr ALL=(root) NOPASSWD: /usr/bin/systemctl reload nginx
```

Without it, watch `renew.log` and reload by hand when it says
`CERT CHANGED`.
