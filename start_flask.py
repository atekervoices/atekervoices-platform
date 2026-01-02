#!/usr/bin/env python3
"""
Startup script for Flask Ateker Voices application
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from ateker_voices import create_app
    from ateker_voices.models import User
    from ateker_voices.extensions import db
    
    # Create the Flask app
    app = create_app()
    
    # Initialize database and create admin user
    with app.app_context():
        db.create_all()
        print("Database initialized successfully.")
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        
        if not admin:
            # Create default admin user
            admin_user = User(
                username='admin',
                email='admin@atekervoices.org',
                is_admin=True
            )
            admin_user.set_password('AtekerAdmin2025!')
            
            db.session.add(admin_user)
            db.session.commit()
            
            print("Default admin user created:")
            print("  Username: admin")
            print("  Password: AtekerAdmin2025!")
            print("  Email: admin@atekervoices.org")
        else:
            print("Admin user already exists.")
    
    # Run the Flask app
    print("\nStarting Ateker Voices Flask application...")
    print("Access the application at: http://localhost:5000")
    print("Login with admin/AtekerAdmin2025! for admin access")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install required packages with:")
    print("pip install flask flask-sqlalchemy flask-login flask-wtf werkzeug")
    sys.exit(1)
except Exception as e:
    print(f"Error starting application: {e}")
    sys.exit(1)
