#!/usr/bin/env python3
"""
Management script for Ateker Voices.
"""
import os
import click
from flask_migrate import Migrate, upgrade, migrate, init, stamp
from flask.cli import FlaskGroup, with_appcontext

from ateker_voices import create_app, db
from ateker_voices.models import User

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

@cli.command("create-user")
@click.option('--username', prompt=True, help='Username')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Password')
@click.option('--email', prompt=True, help='Email')
@click.option('--admin/--no-admin', default=False, help='Make user an admin')
@with_appcontext
def create_user(username, password, email, admin):
    """Create a new user."""
    if User.query.filter_by(username=username).first():
        click.echo(f"User '{username}' already exists.")
        return
    
    user = User(
        username=username,
        email=email,
        is_admin=admin
    )
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    user_type = "admin" if admin else "regular"
    click.echo(f"{user_type} user '{username}' created successfully.")

if __name__ == '__main__':
    cli()
