# Production SSL Setup Guide

## Option 1: Let's Encrypt (Free)
```bash
# Install Certbot in WSL
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Get certificate (replace your-domain.com)
sudo certbot --nginx -d your-domain.com

# Copy certificates to project
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./certs/server.crt
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./certs/server.key
```

## Option 2: Cloudflare SSL (Free)
1. Sign up for Cloudflare
2. Add your domain
3. Enable "Flexible SSL" or "Full SSL"
4. Update your DNS to point to your server

## Option 3: Purchase SSL Certificate
1. Buy from providers like Namecheap, GoDaddy, etc.
2. Generate CSR (Certificate Signing Request)
3. Complete domain verification
4. Install certificates

## After Installing Production Certificates:
1. Update docker-compose.yml to use new certificate paths
2. Restart containers: `docker-compose down && docker-compose up -d`
3. Your site will show as secure with green padlock
