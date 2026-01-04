@echo off
REM Ateker Voices Docker Setup Script for Windows

echo 🚀 Setting up Ateker Voices with Docker...

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is not installed. Please install Docker Compose first.
    pause
    exit /b 1
)

REM Create necessary directories
echo 📁 Creating directories...
if not exist "data" mkdir data
if not exist "certs" mkdir certs

REM Generate self-signed SSL certificate if it doesn't exist
if not exist "certs\server.crt" (
    echo 🔐 Generating SSL certificate...
    openssl req -x509 -newkey rsa:4096 -keyout certs\server.key -out certs\server.crt -days 365 -nodes -subj "/C=UG/ST=Kotido/L=Kotido/O=Ateker Voices/CN=localhost"
)

REM Build and start the Docker container
echo 🏗️  Building and starting Docker container...
docker-compose up --build -d

echo ✅ Setup complete!
echo.
echo 🌐 Access the application at:
echo    HTTP:  http://localhost:80
echo    HTTPS: https://localhost:443
echo.
echo 👤 Default admin credentials:
echo    Username: admin
echo    Email: admin@atekervoices.com
echo    Password: AtekerAdmin2026!
echo.
echo 📋 To view logs: docker-compose logs -f
echo 🛑 To stop: docker-compose down
pause
