#!/bin/bash

# Ateker Voices Docker Setup Script
echo "🚀 Setting up Ateker Voices with Docker..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data
mkdir -p certs

# Generate self-signed SSL certificate if it doesn't exist
if [ ! -f "certs/server.crt" ]; then
    echo "🔐 Generating SSL certificate..."
    openssl req -x509 -newkey rsa:4096 -keyout certs/server.key -out certs/server.crt -days 365 -nodes \
        -subj "/C=UG/ST=Kotido/L=Kotido/O=Ateker Voices/CN=localhost"
fi

# Build and start the Docker container
echo "🏗️  Building and starting Docker container..."
docker-compose up --build -d

echo "✅ Setup complete!"
echo ""
echo "🌐 Access the application at:"
echo "   HTTP:  http://localhost:80"
echo "   HTTPS: https://localhost:443"
echo ""
echo "👤 Default admin credentials:"
echo "   Username: admin"
echo "   Email: admin@atekervoices.com"
echo "   Password: AtekerAdmin2026!"
echo ""
echo "📋 To view logs: docker-compose logs -f"
echo "🛑 To stop: docker-compose down"
