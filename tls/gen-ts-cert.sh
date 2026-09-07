#!/usr/bin/env bash
# Issue / renew the Tailscale (Let's Encrypt) cert for the dashboard's
# Tailscale front door:  https://bdrpisrvdev.tail0ed3f6.ts.net
#
# This cert chains to Let's Encrypt, so every device trusts it with zero
# setup -- no CA to install. It is only valid for the .ts.net name and
# only reachable over the tailnet. LAN / *.local names use the local-CA
# leaf from gen-cert.sh instead.
#
# Let's Encrypt certs last 90 days. Run this from cron (see the crontab
# line in tls/README.md); `tailscale cert` is a no-op until the cert is
# within --min-validity of expiry, so it is cheap to run daily.
#
# Requirements (one-time, in the tailnet admin console):
#   - MagicDNS enabled
#   - HTTPS Certificates enabled  (Settings -> Features)
#
# After a renewal that actually rewrites the files:  reload nginx.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOMAIN="bdrpisrvdev.tail0ed3f6.ts.net"
CRT="$DIR/$DOMAIN.crt"
KEY="$DIR/$DOMAIN.key"

before=""
[[ -f "$CRT" ]] && before="$(openssl x509 -in "$CRT" -noout -fingerprint -sha256 2>/dev/null || true)"

# Keep at least 30 days of validity in hand.
tailscale cert --min-validity 720h \
  --cert-file "$CRT" --key-file "$KEY" \
  "$DOMAIN"

chmod 644 "$CRT"
chmod 600 "$KEY"

after="$(openssl x509 -in "$CRT" -noout -fingerprint -sha256 2>/dev/null || true)"

openssl x509 -in "$CRT" -noout -subject -issuer -dates

if [[ "$before" != "$after" ]]; then
  echo "CERT CHANGED -- reload nginx:  sudo systemctl reload nginx"
  # If bdr has a NOPASSWD sudoers line for it (see tls/README.md), do it:
  if sudo -n systemctl reload nginx 2>/dev/null; then
    echo "nginx reloaded."
  fi
else
  echo "Cert unchanged -- no reload needed."
fi
