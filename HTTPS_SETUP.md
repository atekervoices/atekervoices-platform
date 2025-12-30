# HTTPS Setup for Microphone Access

This application requires HTTPS to access the microphone in modern browsers. Here's how to set it up:

## Quick Setup

1. **Generate SSL Certificate:**
   ```bash
   python generate_cert.py
   ```

2. **Deploy with HTTPS:**
   ```bash
   docker-compose up --build
   ```

3. **Access the Application:**
   - Open browser to: `https://your-vm-ip`
   - Accept the self-signed certificate warning
   - Microphone should now work

## Manual SSL Certificate Generation

If the script doesn't work, generate certificates manually:

```bash
# Create certs directory
mkdir certs

# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 \
  -keyout certs/server.key \
  -out certs/server.crt \
  -days 365 \
  -nodes \
  -subj "/C=UG/ST=Kampala/L=Kampala/O=Crest AI/OU=Development/CN=localhost"
```

## Troubleshooting

### "getUserMedia is not implemented" Error

This error occurs when:
1. **Not using HTTPS** - Modern browsers require HTTPS for microphone access
2. **Using unsupported browser** - Use Chrome, Firefox, or Edge
3. **Headless environment** - Ensure you're accessing from a GUI browser

### Certificate Warnings

- Self-signed certificates will show security warnings
- Click "Advanced" → "Proceed to website" (Chrome)
- Click "Advanced" → "Accept Risk and Continue" (Firefox)

### VM Network Setup

Ensure your VM allows HTTPS traffic:
```bash
# Allow HTTPS port
sudo ufw allow 443

# Or disable firewall temporarily for testing
sudo ufw disable
```

## Development Mode

For local development without HTTPS:
```bash
# Run on localhost (browsers allow getUserMedia on localhost)
python -m ateker_voices --host 127.0.0.1 --port 8080
```

Then access: `http://localhost:8080`

## Production Deployment

For production, use proper SSL certificates:
- Let's Encrypt (free)
- Cloudflare SSL
- AWS Certificate Manager
- Or purchase from certificate authority

Update docker-compose.yml with your certificate paths.
