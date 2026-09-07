#!/usr/bin/env bash
# Regenerate the TLS material nginx uses for the BdRDev dashboard.
#
# Two-part trust story (see tls/README.md):
#
#   1. LAN / mDNS / IP names  -> a leaf cert signed by a local root CA
#      created + kept in tls/ca/.  Install that CA once per device and
#      every *.local / LAN-IP hit is trusted, online or off.
#
#   2. Tailscale front door    -> a real Let's Encrypt cert from
#      `tailscale cert`, trusted everywhere with zero device setup.
#      That one is handled by gen-ts-cert.sh, not this script.
#
# This script (re)creates the local CA if it is missing, then issues a
# fresh leaf from it.  Existing files are backed up with a timestamp.
#
# After running:  sudo systemctl reload nginx
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CA_DIR="$DIR/ca"
CA_CRT="$CA_DIR/bdr-fleet-ca.crt"
CA_KEY="$CA_DIR/bdr-fleet-ca.key"
CRT="$DIR/bdrdev.local.crt"
KEY="$DIR/bdrdev.local.key"
STAMP="$(date +%Y%m%d%H%M%S)"

# Names + IPs the box answers on for LAN / mDNS / loopback / Tailscale.
# The Tailscale *DNS* name (bdrpisrvdev.tail0ed3f6.ts.net) is deliberately
# NOT here -- that one is served by the Let's Encrypt cert instead.
SAN="\
DNS:bdrpisrvdev.local,DNS:bdrpisrvdev,\
DNS:bdrdev.local,DNS:BdRDev,DNS:bdrsrvdev.local,DNS:BdRSrvDev,\
DNS:localhost,\
IP:10.10.8.11,IP:100.116.147.74,IP:127.0.0.1,IP:::1,\
IP:fd7a:115c:a1e0::9137:934b"

mkdir -p "$CA_DIR"
chmod 700 "$CA_DIR"

# --- 1. local root CA (10y) -------------------------------------------------
if [[ ! -f "$CA_CRT" || ! -f "$CA_KEY" ]]; then
  echo "No local CA found -- creating one at $CA_DIR"
  openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout "$CA_KEY" -out "$CA_CRT" \
    -days 3650 -sha256 \
    -subj "/O=BdR Fleet/CN=BdR Fleet Local Root CA" \
    -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
    -addext "keyUsage=critical,keyCertSign,cRLSign"
  chmod 600 "$CA_KEY"
  chmod 644 "$CA_CRT"
  echo "  -> install $CA_CRT on every device (see tls/README.md)"
else
  echo "Reusing existing CA at $CA_CRT"
fi

# --- 2. leaf cert, signed by the CA (2y) ----------------------------------
[[ -f "$CRT" ]] && cp -p "$CRT" "$CRT.bak-$STAMP"
[[ -f "$KEY" ]] && cp -p "$KEY" "$KEY.bak-$STAMP"

CSR="$(mktemp)"; EXT="$(mktemp)"
trap 'rm -f "$CSR" "$EXT"' EXIT

cat > "$EXT" <<EOF
subjectAltName=$SAN
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
EOF

openssl req -newkey rsa:2048 -nodes -keyout "$KEY" -out "$CSR" \
  -subj "/CN=bdrpisrvdev.local"

openssl x509 -req -in "$CSR" \
  -CA "$CA_CRT" -CAkey "$CA_KEY" -CAcreateserial \
  -out "$CRT" -days 730 -sha256 \
  -extfile "$EXT"

chmod 600 "$KEY"
chmod 644 "$CRT"

echo
echo "Regenerated leaf:"
openssl x509 -in "$CRT" -noout -subject -issuer -ext subjectAltName -dates
echo
echo "CA SHA-256 fingerprint (verify this when trusting on a device):"
openssl x509 -in "$CA_CRT" -noout -fingerprint -sha256
echo
echo "Now run:  sudo systemctl reload nginx"
