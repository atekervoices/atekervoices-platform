# Ateker Voices

A comprehensive tool for recording and managing voice datasets for training Ateker Voices, featuring user management and dataset export capabilities.

![Screen shot](etc/screenshot.jpg)

[![Sponsored by Nabu Casa](etc/nabu_casa_sponsored.png)](https://nabucasa.com)

## Features

- 🎤 Record high-quality voice samples
- 👥 Multi-user support with role-based access control
- 👩‍💻 Admin dashboard for user and dataset management
- 📦 Multiple export formats (ZIP, CSV, JSON)
- 🐳 Docker support with automated setup
- 🔄 Automatic database migrations
- 🔒 Secure authentication and authorization

## Prerequisites

- Docker and Docker Compose (for containerized deployment)
- Python 3.9+ (for local development)
- FFmpeg (for audio processing)

## Quick Start with Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/ateker-voices.git
   cd ateker-voices
   ```

2. Create a `.env` file with your configuration:
   ```env
   # Database settings
   DATABASE_URL=sqlite:////data/ateker_voices.db
   
   # Admin credentials (change these!)
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=change_this_password
   ADMIN_EMAIL=admin@example.com
   
   # Application settings
   SECRET_KEY=your-secret-key-change-this
   UPLOAD_FOLDER=/app/output
   MAX_CONTENT_LENGTH=200 * 1024 * 1024  # 200MB
   ```

3. Start the application:
   ```bash
   docker-compose up -d
   ```

4. Access the application:
   - Main application: http://localhost:80
   - Admin panel: http://localhost:80/admin
   - Default admin credentials: admin / change_this_password

## Manual Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/ateker-voices.git
   cd ateker-voices
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up the database:
   ```bash
   flask db upgrade
   ```

5. Create an admin user:
   ```bash
   flask create-admin --username admin --password yourpassword --email admin@example.com
   ```

6. Run the application:
   ```bash
   python -m crest_ai_studio
   ```

## Using the Admin Panel

The admin panel provides tools for managing users, recordings, and dataset exports:

1. **Dashboard**: View system statistics and recent activity
2. **Users**: Manage user accounts and permissions
3. **Recordings**: Browse, validate, and manage voice recordings
4. **Exports**: Generate and download dataset exports in multiple formats

## Exporting Datasets

Datasets can be exported directly from the web interface or using the command line:

### Web Interface
1. Navigate to the Admin Panel > Exports
2. Select the language and export format (ZIP, CSV, or JSON)
3. Click "Export Dataset" to generate and download the export

### Command Line
```bash
# Export to ZIP (audio + metadata)
python -m export_utils --language en --format zip --output /path/to/export.zip

# Export to CSV (metadata only)
python -m export_utils --language en --format csv --output /path/to/metadata.csv

# Export to JSON (metadata only)
python -m export_utils --language en --format json --output /path/to/metadata.json
```

## Multi-User Mode

By default, the application runs in multi-user mode with authentication. To disable authentication (development only):

```bash
python -m ateker_voices --no-auth
```

## Configuration

Configuration can be provided via environment variables or a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///ateker_voices.db` | Database connection URL |
| `SECRET_KEY` | Randomly generated | Secret key for session management |
| `UPLOAD_FOLDER` | `./output` | Directory to store recordings |
| `ADMIN_USERNAME` | `admin` | Initial admin username |
| `ADMIN_PASSWORD` | Randomly generated | Initial admin password |
| `ADMIN_EMAIL` | `admin@example.com` | Admin email address |
| `MAX_CONTENT_LENGTH` | `200 * 1024 * 1024` | Maximum file upload size (200MB) |

## Development

### Running Tests
```bash
pytest tests/
```

### Database Migrations
When making changes to the database models:

1. Generate a new migration:
   ```bash
   flask db migrate -m "description of changes"
   ```

2. Apply the migration:
   ```bash
   flask db upgrade
   ```

### Building the Docker Image
```bash
docker build -t ateker-voices .
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Rhasspy](https://rhasspy.ai/) for the original Ateker Voices
- [Nabu Casa](https://nabucasa.com/) for their support
- All contributors and users of the project

Now a "login code" will be required to record. A directory `output/user_<code>/<language>` must exist for each user and language.
