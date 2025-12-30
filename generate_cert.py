#!/usr/bin/env python3
"""Generate self-signed SSL certificate for HTTPS development."""

import subprocess
import sys
from pathlib import Path

def generate_cert():
    """Generate self-signed certificate using OpenSSL."""
    cert_dir = Path("certs")
    cert_dir.mkdir(exist_ok=True)
    
    cert_file = cert_dir / "server.crt"
    key_file = cert_dir / "server.key"
    
    if cert_file.exists() and key_file.exists():
        print("Certificate already exists")
        return str(cert_file), str(key_file)
    
    try:
        # Generate self-signed certificate
        cmd = [
            "openssl", "req", "-x509", "-newkey", "rsa:4096",
            "-keyout", str(key_file),
            "-out", str(cert_file),
            "-days", "365",
            "-nodes",
            "-subj", "/C=UG/ST=Kampala/L=Kampala/O=Crest AI/OU=Development/CN=localhost"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"Certificate generated: {cert_file}")
        print(f"Private key generated: {key_file}")
        return str(cert_file), str(key_file)
        
    except subprocess.CalledProcessError as e:
        print(f"Error generating certificate: {e}")
        print("Make sure OpenSSL is installed")
        return None, None
    except FileNotFoundError:
        print("OpenSSL not found. Please install OpenSSL.")
        return None, None

if __name__ == "__main__":
    cert, key = generate_cert()
    if cert and key:
        print(f"\nTo use with docker-compose:")
        print(f"  - Mount certs directory: - ./certs:/app/certs")
        print(f"  - Update command: python -m ateker_voices --ssl --cert-file /app/certs/server.crt --key-file /app/certs/server.key")
