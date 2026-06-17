# TLS Certificates

Place your TLS certificate files here before running the production stack.

## Required files

| File | Description |
|---|---|
| `fullchain.pem` | Certificate + intermediate chain (from Let's Encrypt or CA) |
| `privkey.pem` | Private key — keep this secret, never commit |
| `dhparam.pem` | Diffie-Hellman parameters (generate once, reuse) |

## Let's Encrypt (recommended for internet-facing deployments)

```bash
# Install certbot
apt-get install certbot

# Obtain a certificate (replace with your domain)
certbot certonly --standalone -d cyberops.yourdomain.com

# Copy the files
cp /etc/letsencrypt/live/cyberops.yourdomain.com/fullchain.pem nginx/certs/
cp /etc/letsencrypt/live/cyberops.yourdomain.com/privkey.pem nginx/certs/

# Generate DH params (do this once — takes a minute)
openssl dhparam -out nginx/certs/dhparam.pem 2048
```

## Self-signed certificate (dev/testing only)

Run from the repo root:

```bash
bash scripts/gen-dev-certs.sh
```

This creates a self-signed cert valid for 365 days. Browsers will show a warning — accept it or add an exception.

## Auto-renewal with Let's Encrypt

Add to crontab:
```
0 3 * * * certbot renew --quiet && docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```
