import click
from flask import current_app
from flask.cli import with_appcontext
from .extensions import db
from .models import User

@click.command('create-admin')
@click.option('--username', prompt=True, help='Admin username')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Admin password')
@click.option('--email', prompt=True, help='Admin email')
@with_appcontext
def create_admin(username, password, email):
    """Create an admin user."""
    # Check if user already exists
    if User.query.filter_by(username=username).first():
        click.echo('User already exists. Updating password...')
        user = User.query.filter_by(username=username).first()
        user.set_password(password)
        user.email = email
        user.is_admin = True
    else:
        # Create new admin user
        user = User(
            username=username,
            email=email,
            is_admin=True
        )
        user.set_password(password)
        db.session.add(user)
    
    db.session.commit()
    click.echo(f'Admin user {username} created/updated successfully.')
