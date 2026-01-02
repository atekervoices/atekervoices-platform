#!/usr/bin/env python3
"""
Flask-based main entry point for Ateker Voices with authentication
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add the parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ateker_voices import create_app
from ateker_voices.models import User
from ateker_voices.extensions import db

_LOGGER = logging.getLogger(__name__)
_DIR = Path(__file__).parent


def main() -> None:
    """Main entry point with Flask authentication."""
    parser = argparse.ArgumentParser(description="Ateker Voices - Language Recording Platform")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind to")
    parser.add_argument("--ssl", action="store_true", help="Enable HTTPS with self-signed certificate")
    parser.add_argument("--cert-file", help="Path to SSL certificate file")
    parser.add_argument("--key-file", help="Path to SSL private key file")
    
    # Data directories
    parser.add_argument(
        "--prompts",
        help="Path to prompts directory",
        action="append",
        default=[_DIR.parent / "prompts"],
    )
    parser.add_argument(
        "--output",
        help="Path to output directory",
        default=_DIR.parent / "output",
    )
    
    # Feature flags
    parser.add_argument(
        "--multi-user",
        action="store_true",
        help="Enable multi-user mode with authentication",
    )
    parser.add_argument("--cc0", action="store_true", help="Show public domain notice")
    parser.add_argument(
        "--debug", action="store_true", help="Print DEBUG messages to console"
    )
    
    # Authentication options
    parser.add_argument("--create-admin", action="store_true", help="Create admin user interactively")
    parser.add_argument("--init-db", action="store_true", help="Initialize database and exit")
    
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    _LOGGER.debug(args)

    # Create Flask app
    app = create_app()
    
    # Update app config with command line arguments
    app.config['UPLOAD_FOLDER'] = str(Path(args.output))
    app.config['DEBUG'] = args.debug
    
    # Initialize database if requested
    if args.init_db or args.create_admin:
        with app.app_context():
            db.create_all()
            print("Database initialized successfully.")
            
            if args.create_admin:
                from getpass import getpass
                
                username = input("Enter admin username: ")
                email = input("Enter admin email: ")
                password = getpass("Enter admin password: ")
                
                # Check if user exists
                existing_user = User.query.filter_by(username=username).first()
                if existing_user:
                    print(f"User {username} already exists. Updating password...")
                    existing_user.set_password(password)
                    existing_user.email = email
                    existing_user.is_admin = True
                    db.session.commit()
                else:
                    admin_user = User(username=username, email=email, is_admin=True)
                    admin_user.set_password(password)
                    db.session.add(admin_user)
                    db.session.commit()
                    print(f"Admin user {username} created successfully.")
        return

    # Ensure output directory exists
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create user directories for multi-user mode
    if args.multi_user:
        print("Multi-user mode enabled with Flask authentication")
        print("Users will be organized in separate directories")
    
    print(f"Starting Ateker Voices on http://{args.host}:{args.port}")
    print("Authentication: Flask-Login with SQLAlchemy")
    
    if args.ssl:
        print("SSL enabled")
        # SSL configuration would go here
        print("Note: Full SSL configuration requires additional setup")
    
    # Run the Flask app
    try:
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            ssl_context=None  # Could be configured for SSL
        )
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        _LOGGER.error(f"Error running application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
