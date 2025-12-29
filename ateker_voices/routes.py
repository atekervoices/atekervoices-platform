from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.utils import secure_filename
import os
from . import db
from .models import User

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    # Load prompts and languages
    from . import load_prompts, load_validation_data
    from pathlib import Path
    
    prompts_dirs = [Path(current_app.config['UPLOAD_FOLDER']) / 'prompts']
    
    try:
        prompts, languages = load_prompts(prompts_dirs)
    except Exception as e:
        current_app.logger.error(f"Error loading prompts: {e}")
        prompts, languages = {}, {}
    
    return render_template('index.html', languages=sorted(languages.items()))

@bp.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({
        'status': 'ok',
        'message': 'Ateker Voices is running',
        'version': '1.0.0'
    }), 200

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.index'))
        
        flash('Invalid username or password')
    
    return 'Login form will be here'

@bp.route('/logout')
@login_required
def logout():
    """User logout route."""
    logout_user()
    return redirect(url_for('main.index'))

# Add more routes as needed
