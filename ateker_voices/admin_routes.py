from quart import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
from pathlib import Path

from .models import User, Recording, DatasetExport, db
from .export_utils import DatasetExporter
from .auth import user_manager

# Create admin blueprint
bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to ensure user is an admin."""
    @login_required
    async def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('index'))
        return await f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@admin_required
async def dashboard():
    """Admin dashboard."""
    # Get statistics
    stats = {
        'total_users': User.query.count(),
        'total_recordings': Recording.query.count(),
        'validated_recordings': Recording.query.filter_by(is_validated=True).count(),
        'pending_recordings': Recording.query.filter_by(is_validated=False).count(),
    }
    
    # Get recent exports
    recent_exports = DatasetExport.query.order_by(DatasetExport.created_at.desc()).limit(5).all()
    
    # Get recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    return await render_template(
        'admin/dashboard.html',
        stats=stats,
        recent_exports=recent_exports,
        recent_users=recent_users
    )

@bp.route('/users')
@admin_required
async def user_management():
    """User management page."""
    users = User.query.order_by(User.username).all()
    return await render_template('admin/users.html', users=users)

@bp.route('/users/create', methods=['GET', 'POST'])
@admin_required
async def create_user():
    """Create a new user."""
    if request.method == 'POST':
        form = await request.form
        username = form.get('username')
        password = form.get('password')
        email = form.get('email')
        is_admin = 'is_admin' in form
        
        if not username or not password:
            flash('Username and password are required', 'danger')
            return await render_template('admin/user_form.html', title='Create User')
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return await render_template('admin/user_form.html', title='Create User')
        
        # Create user
        user = User(
            username=username,
            email=email,
            is_admin=is_admin
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('User created successfully', 'success')
        return redirect(url_for('admin.user_management'))
    
    return await render_template('admin/user_form.html', title='Create User')

@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
async def edit_user(user_id):
    """Edit a user."""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        form = await request.form
        user.username = form.get('username', user.username)
        user.email = form.get('email', user.email)
        user.is_admin = 'is_admin' in form
        
        # Update password if provided
        new_password = form.get('password')
        if new_password:
            user.set_password(new_password)
        
        db.session.commit()
        flash('User updated successfully', 'success')
        return redirect(url_for('admin.user_management'))
    
    return await render_template('admin/user_form.html', title='Edit User', user=user)

@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
async def delete_user(user_id):
    """Delete a user."""
    if user_id == current_user.id:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('admin.user_management'))
    
    user = User.query.get_or_404(user_id)
    
    # Delete user's recordings and exports
    Recording.query.filter_by(user_id=user_id).delete()
    DatasetExport.query.filter_by(user_id=user_id).delete()
    
    # Delete user
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully', 'success')
    return redirect(url_for('admin.user_management'))

@bp.route('/exports')
@admin_required
async def export_management():
    """Export management page."""
    # Get available datasets
    exporter = DatasetExporter(current_app.config['OUTPUT_DIR'])
    datasets = exporter.get_available_datasets()
    
    # Get export history
    exports = DatasetExport.query.order_by(DatasetExport.created_at.desc()).all()
    
    return await render_template(
        'admin/exports.html',
        datasets=datasets,
        exports=exports
    )

@bp.route('/exports/create', methods=['POST'])
@admin_required
async def create_export():
    """Create a new dataset export."""
    form = await request.form
    language = form.get('language')
    export_format = form.get('format', 'zip')
    include_metadata = 'include_metadata' in form
    
    if not language:
        flash('Language is required', 'danger')
        return redirect(url_for('admin.export_management'))
    
    try:
        exporter = DatasetExporter(current_app.config['OUTPUT_DIR'])
        export_data = exporter.export_dataset(language, export_format, include_metadata)
        
        # Generate filename
        filename = exporter.get_export_filename(language, export_format)
        
        # Save export record
        export = DatasetExport(
            export_format=export_format,
            language=language,
            file_path=filename,
            file_size=len(export_data.getvalue()),
            record_count=len(exporter.get_available_datasets()),
            user_id=current_user.id
        )
        db.session.add(export)
        db.session.commit()
        
        # Return the file for download
        export_data.seek(0)
        return await send_file(
            export_data,
            as_attachment=True,
            download_name=filename,
            mimetype=f'application/{export_format}'
        )
    
    except Exception as e:
        current_app.logger.error(f"Export failed: {e}")
        flash(f'Export failed: {str(e)}', 'danger')
        return redirect(url_for('admin.export_management'))

@bp.route('/exports/<int:export_id>/download')
@admin_required
async def download_export(export_id):
    """Download a previously generated export."""
    export = DatasetExport.query.get_or_404(export_id)
    
    if not export.file_path or not os.path.exists(export.file_path):
        flash('Export file not found', 'danger')
        return redirect(url_for('admin.export_management'))
    
    return await send_file(
        export.file_path,
        as_attachment=True,
        download_name=os.path.basename(export.file_path)
    )

@bp.route('/recordings')
@admin_required
async def recording_management():
    """Recording management page."""
    # Get filter parameters
    language = request.args.get('language')
    user_id = request.args.get('user_id', type=int)
    is_validated = request.args.get('is_validated')
    
    # Build query
    query = Recording.query
    
    if language:
        query = query.filter(Recording.language == language)
    if user_id:
        query = query.filter(Recording.user_id == user_id)
    if is_validated is not None:
        query = query.filter(Recording.is_validated == (is_validated.lower() == 'true'))
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get recordings with pagination
    recordings = query.order_by(Recording.created_at.desc()).paginate(page=page, per_page=per_page)
    
    # Get available languages for filter
    languages = db.session.query(Recording.language).distinct().all()
    languages = [lang[0] for lang in languages]
    
    # Get users for filter
    users = User.query.order_by(User.username).all()
    
    return await render_template(
        'admin/recordings.html',
        recordings=recordings,
        languages=languages,
        users=users,
        current_filters={
            'language': language,
            'user_id': user_id,
            'is_validated': is_validated
        }
    )

@bp.route('/recordings/<int:recording_id>/validate', methods=['POST'])
@admin_required
async def validate_recording(recording_id):
    """Validate or reject a recording."""
    recording = Recording.query.get_or_404(recording_id)
    data = await request.get_json()
    
    if 'is_valid' not in data:
        return jsonify({'error': 'Missing is_valid parameter'}), 400
    
    recording.is_validated = data['is_valid']
    recording.validation_notes = data.get('notes', '')
    recording.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'recording': recording.to_dict()
    })
