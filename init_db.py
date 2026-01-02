#!/usr/bin/env python3
"""
Initialize database and create default admin user
"""

from ateker_voices import create_app
from ateker_voices.models import User
from ateker_voices.extensions import db

def init_database():
    """Initialize the database and create default admin user."""
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully.")
        
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
        
        # Show all users
        users = User.query.all()
        print(f"\nTotal users in database: {len(users)}")
        for user in users:
            status = "Admin" if user.is_admin else "User"
            print(f"  - {user.username} ({user.email}) - {status}")

if __name__ == '__main__':
    init_database()
