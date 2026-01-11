#!/usr/bin/env python3
"""
Management script for Ateker Voices.
"""
import os
import click
from flask_migrate import Migrate, upgrade, migrate, init, stamp
from flask.cli import FlaskGroup, with_appcontext

from ateker_voices import create_app, db
from ateker_voices.models import User, Recording

def create_app_info():
    """Create application factory for CLI commands."""
    app = create_app()
    migrate = Migrate(app, db)
    return app, db, migrate

app, db, migrate = create_app_info()
cli = FlaskGroup(create_app=create_app)

@cli.command("create-admin")
@click.option('--username', prompt=True, help='Admin username')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Admin password')
@click.option('--email', prompt=True, default='admin@example.com', help='Admin email')
@with_appcontext
def create_admin(username, password, email):
    """Create an admin user."""
    if User.query.filter_by(username=username).first():
        click.echo(f"User '{username}' already exists.")
        return
    
    admin = User(
        username=username,
        email=email,
        is_admin=True
    )
    admin.set_password(password)
    
    db.session.add(admin)
    db.session.commit()
    
    click.echo(f"Admin user '{username}' created successfully.")

@cli.command("init-db")
@with_appcontext
def init_db():
    """Initialize the database."""
    db.create_all()
    click.echo("Database initialized.")

@cli.command("migrate-db")
@with_appcontext
def migrate_db():
    """Run database migrations."""
    migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
    if not os.path.exists(migrations_dir):
        init()
        click.echo("Created migrations directory.")
    
    migrate(message='Database migration')
    upgrade()
    click.echo("Database migrated to latest version.")

@cli.command("delete-recordings")
@click.option('--user-id', type=int, help='Delete recordings for specific user ID')
@click.option('--language', help='Delete recordings for specific language')
@click.option('--all', is_flag=True, help='Delete all recordings')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted without actually deleting')
@with_appcontext
def delete_recordings(user_id, language, all, dry_run):
    """Delete recordings from database."""
    
    query = Recording.query
    
    # Build query based on filters
    if user_id:
        query = query.filter(Recording.user_id == user_id)
        print(f"Filtering by user ID: {user_id}")
    
    if language:
        query = query.filter(Recording.language == language)
        print(f"Filtering by language: {language}")
    
    if all:
        query = query
        print("Deleting ALL recordings")
    
    # Count what would be deleted
    count = query.count()
    
    if dry_run:
        print(f"🔍 DRY RUN: Would delete {count} recordings")
        if count > 0:
            recordings = query.limit(10).all()
            print("Sample recordings to be deleted:")
            for rec in recordings:
                user = User.query.get(rec.user_id)
                print(f"  - {rec.id}: {rec.prompt_text[:50]}... (User: {user.username if user else 'Unknown'}, Lang: {rec.language})")
        return
    
    if count == 0:
        print("❌ No recordings found matching criteria")
        return
    
    # Confirm deletion
    if not click.confirm(f'Are you sure you want to delete {count} recordings?'):
        print("❌ Deletion cancelled")
        return
    
    # Get details before deletion
    recordings = query.all()
    print(f"🗑️ Deleting {count} recordings...")
    
    # Delete recordings
    for rec in recordings:
        user = User.query.get(rec.user_id)
        print(f"  Deleting: {rec.id} (User: {user.username if user else 'Unknown'}, Lang: {rec.language})")
        db.session.delete(rec)
    
    db.session.commit()
    print(f"✅ Successfully deleted {count} recordings")

if __name__ == '__main__':
    cli()
