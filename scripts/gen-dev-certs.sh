#!/usr/bin/env bash
# Generate self-signed TLS certificates for local development/testing.
# NOT for production use — browsers will show a security warning.
set -euo pipefail

CERTS_DIR="$(dirname "$0")/../nginx/certs"
mkdir -p "$CERTS_DIR"

echo "Generating self-signed certificate in $CERTS_DIR ..."

openssl req -x509 -nodes -newkey rsa:4096 \
  -keyout "$CERTS_DIR/privkey.pem" \
  -out "$CERTS_DIR/fullchain.pem" \
  -days 365 \
  -subj "/C=US/ST=Ohio/L=Columbus/O=Buckeye Manufacturing Group/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

echo "Generating DH parameters (this takes ~30 seconds) ..."
openssl dhparam -out "$CERTS_DIR/dhparam.pem" 2048

echo ""
echo "Done. Files written to $CERTS_DIR:"
ls -lh "$CERTS_DIR/"*.pem
echo ""
echo "WARNING: These are self-signed certificates for development only."
echo "         Use Let's Encrypt or a real CA for production deployments."
