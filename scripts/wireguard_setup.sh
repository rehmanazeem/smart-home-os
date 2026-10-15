#!/usr/bin/env bash
# Basic WireGuard server/client key generation helper (manual review required).
set -euo pipefail

OUT_DIR="$(cd "$(dirname "$0")/.." && pwd)/wireguard"
mkdir -p "$OUT_DIR"

echo "Generating server keys..."
wg genkey | tee "$OUT_DIR/server_private.key" | wg pubkey > "$OUT_DIR/server_public.key"
echo "Generating client keys..."
wg genkey | tee "$OUT_DIR/client_private.key" | wg pubkey > "$OUT_DIR/client_public.key"

cat > "$OUT_DIR/README.txt" <<EOF
WireGuard keys generated. You must manually create server and client configuration files based on your network.
Typical server config should bind to UDP 51820 and include the client public key.
Ensure the Raspberry Pi firewall only exposes UDP/51820; do not expose the HTTP API or MQTT publicly.
EOF

echo "WireGuard artifacts written to $OUT_DIR"
