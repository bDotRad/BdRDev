#!/usr/bin/env bash
# gen-selfsigned.sh -- issue this box's standalone LAN/mDNS cert, per the
# fleet HTTPS standard (../_Instructions/HTTPS.md): no fleet CA, one
# standalone self-signed leaf per box. Re-run whenever the SAN list needs
# a new hostname alias, or the box's LAN IP changes (DHCP renewal).
#
# Supersedes gen-cert.sh (CA-signed) and the old bdr-fleet-ca -- that CA
# is deprecated, see ca/_deprecated/.
#
# After running:  sudo systemctl restart nginx
# No sudo needed to run this.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRT="$DIR/bdrpisrvdev.local.crt"
KEY="$DIR/bdrpisrvdev.local.key"
STAMP="$(date +%Y%m%d%H%M%S)"

LANIP="$(ip -4 -o addr show wlan0 2>/dev/null | awk '{print $4}' | cut -d/ -f1)"
SAN="DNS:bdrpisrvdev.local,DNS:bdrpisrvdev,DNS:bdrdev.local,DNS:BdRDev,DNS:localhost,IP:127.0.0.1"
[[ -n "$LANIP" ]] && SAN="$SAN,IP:$LANIP"

[[ -f "$CRT" ]] && cp -p "$CRT" "$CRT.bak-$STAMP"
[[ -f "$KEY" ]] && cp -p "$KEY" "$KEY.bak-$STAMP"

openssl genrsa -out "$KEY" 2048
chmod 600 "$KEY"

openssl req -new -key "$KEY" -subj "/CN=bdrpisrvdev.local" \
  | openssl x509 -req -signkey "$KEY" -days 1825 -sha256 \
      -extfile <(printf 'subjectAltName=%s\nbasicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n' "$SAN") \
      -out "$CRT"
chmod 644 "$CRT"

echo
echo "Issued (standalone, no CA -- browsers show a one-time warning on first visit):"
openssl x509 -in "$CRT" -noout -subject -ext subjectAltName -dates
echo
echo "LAN IP baked into this cert: ${LANIP:-<none found>} -- rerun this script if it changes."
echo "Now:  sudo systemctl restart nginx"
