import os
from flask import Flask
from flask_migrate import Migrate
from .extensions import db, login_manager

def create_app(config_class=None):
    app = Flask(__name__)
    
    # Load default config and override with config_class if provided
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-key-change-this-in-production'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///ateker_voices.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=os.environ.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'output')),
        MAX_CONTENT_LENGTH=int(os.environ.get('MAX_CONTENT_LENGTH', 200 * 1024 * 1024))  # 200MB default
    )
    
    if config_class:
        app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    Migrate(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    
    # Register CLI commands
    from . import commands
    app.cli.add_command(commands.create_admin)
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Import and register blueprints
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)
    
    # Import models to ensure they are registered with SQLAlchemy
    from . import models
    
    # Create database tables (only if they don't exist)
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created/updated successfully.")
        except Exception as e:
            print(f"Database creation note: {e}")
            # Tables may already exist, continue
    
    return app