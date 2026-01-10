from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify, send_file
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.utils import secure_filename
import os
import json
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from . import db
from .models import User

bp = Blueprint('main', __name__)

def admin_required(f):
    """Decorator to ensure user is an admin."""
    from functools import wraps
    
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    
    # Give each decorated function a unique name
    decorated_function.__name__ = f"admin_{f.__name__}"
    return decorated_function

@bp.route('/')
def index():
    # Load prompts and languages
    from .utils import load_prompts
    
    prompts_dirs = [Path(current_app.config['UPLOAD_FOLDER']).parent / "prompts"]
    
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
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        
        flash('Invalid username or password')
    
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        age_group = request.form.get('age_group')
        gender = request.form.get('gender')
        
        # Validation
        if not username or not email or not password:
            flash('All fields are required')
            return render_template('register.html')
            
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('register.html')
            
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return render_template('register.html')
            
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return render_template('register.html')
        
        # Create new user
        user = User(username=username, email=email)
        user.age_group = age_group
        user.gender = gender
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.')
        return redirect(url_for('main.login'))
    
    return render_template('register.html')

@bp.route('/logout')
@login_required
def logout():
    """User logout route."""
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/record')
@login_required
def record():
    """Record audio for a text prompt"""
    language = request.args.get("language")
    if not language:
        flash('Language parameter is required')
        return redirect(url_for('main.index'))
    
    # Import recording functionality from utils
    from .utils import load_prompts, get_next_prompt
    from .contribution_rules import ContributionRules
    
    prompts_dirs = [Path(current_app.config['UPLOAD_FOLDER']).parent / "prompts"]
    prompts, languages = load_prompts(prompts_dirs)
    
    # Get user progress and session info
    user_progress = ContributionRules.get_user_progress(current_user.id, language)
    
    # Get available prompts based on contribution rules
    if language in prompts:
        available_prompts = ContributionRules.get_available_prompts(
            current_user.id, language, prompts[language]
        )
        
        if not available_prompts:
            return render_template("done.html", 
                                 message="No available sentences remaining. Thank you for your contributions!")
        
        # Get the least saturated prompt
        next_prompt_data = available_prompts[0]
        next_prompt = next_prompt_data['prompt']
        
        # Get or create session
        session = ContributionRules.get_or_create_session(current_user.id, language)
        
        return render_template(
            "record.html",
            language=language,
            prompt_group=next_prompt.group,
            prompt_id=next_prompt.id,
            text=next_prompt.text,
            user_progress=user_progress,
            sentence_stats=next_prompt_data,
            session_id=session.id,
            user_id=current_user.id,
        )
    else:
        flash('Language not found')
        return redirect(url_for('main.index'))

@bp.route('/submit', methods=['POST'])
@login_required
def submit():
    """Submit audio for a text prompt - Optimized version"""
    from .models import Recording
    from .contribution_rules import ContributionRules
    
    language = request.form.get('language')
    prompt_group = request.form.get('promptGroup')
    prompt_id = request.form.get('promptId')
    prompt_text = request.form.get('text')
    audio_format = request.form.get('format')
    duration = request.form.get('duration', 'unknown')
    session_id = request.form.get('sessionId')
    
    # Quick validation before file processing
    can_record, reason = ContributionRules.can_user_record_sentence(
        current_user.id, language, prompt_group, prompt_id
    )
    
    if not can_record:
        return jsonify({'error': reason}), 400
    
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({'error': 'No audio file selected'}), 400
    
    # Determine file extension
    suffix = '.webm'
    if 'wav' in audio_format:
        suffix = '.wav'
    
    # Create user-specific directory structure
    output_dir = Path(current_app.config['UPLOAD_FOLDER'])
    user_audio_dir = output_dir / f"user_{current_user.id}" / language / prompt_group
    user_audio_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    filename = f"{prompt_id}{suffix}"
    audio_path = user_audio_dir / filename
    
    # Save files in parallel with database operation
    text_path = user_audio_dir / f"{prompt_id}.txt"
    
    # Batch file operations
    audio_file.save(audio_path)
    text_path.write_text(prompt_text, encoding='utf-8')
    
    # Save recording to database with session ID
    recording = Recording(
        user_id=current_user.id,
        language=language,
        prompt_group=prompt_group,
        prompt_id=prompt_id,
        prompt_text=prompt_text,
        filename=filename,
        audio_format=audio_format,
        duration=duration,
        file_size=audio_path.stat().st_size if audio_path.exists() else 0,
        session_id=session_id
    )
    
    db.session.add(recording)
    ContributionRules.update_session_progress(session_id)
    db.session.commit()  # Single commit for both operations
    
    # Get next available prompt (already optimized)
    from .utils import load_prompts
    prompts_dirs = [Path(current_app.config['UPLOAD_FOLDER']).parent / "prompts"]
    prompts, languages = load_prompts(prompts_dirs)
    
    available_prompts = ContributionRules.get_available_prompts(
        current_user.id, language, prompts[language] if language in prompts else []
    )
    
    if not available_prompts:
        return jsonify({'done': True, 'message': 'Session completed! No more sentences available.'})
    
    # Check if current session is complete
    user_progress = ContributionRules.get_user_progress(current_user.id, language)
    session_complete = (
        user_progress['active_session'] and 
        user_progress['active_session']['recordings_in_session'] >= 5
    )
    
    if session_complete:
        return jsonify({
            'done': True, 
            'message': f'Session complete! You recorded {user_progress["active_session"]["recordings_in_session"]} sentences. Start a new session to continue.'
        })
    
    # Get next prompt
    next_prompt_data = available_prompts[0]
    next_prompt = next_prompt_data['prompt']
    
    return jsonify({
        'done': False,
        'promptGroup': next_prompt.group,
        'promptId': next_prompt.id,
        'promptText': next_prompt.text,
        'user_progress': user_progress,
        'sentence_stats': next_prompt_data,
    })

@bp.route('/admin')
@admin_required
def admin():
    """Admin interface"""
    from .utils import load_prompts
    from .models import Recording, User, DatasetExport
    from datetime import datetime
    
    # Get basic statistics
    stats = {
        'total_users': User.query.count(),
        'total_recordings': Recording.query.count(),
        'approved_recordings': Recording.query.filter_by(status='approved').count(),
        'rejected_recordings': Recording.query.filter_by(status='rejected').count(),
        'pending_recordings': Recording.query.filter_by(status='pending').count(),
    }
    
    # Get language statistics
    language_stats = db.session.query(
        Recording.language,
        db.func.count(Recording.id).label('count')
    ).group_by(Recording.language).all()
    stats['languages'] = {lang: count for lang, count in language_stats}
    
    # Get recent activity
    recent_recordings = Recording.query.order_by(Recording.submitted_date.desc()).limit(5).all()
    recent_exports = DatasetExport.query.order_by(DatasetExport.export_date.desc()).limit(5).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    # Get validation statistics
    validation_stats = {
        'total_validated': Recording.query.filter(Recording.status.in_(['approved', 'rejected'])).count(),
        'approval_rate': 0,
        'rejection_rate': 0
    }
    
    if validation_stats['total_validated'] > 0:
        validation_stats['approval_rate'] = round(
            (stats['approved_recordings'] / validation_stats['total_validated']) * 100, 1
        )
        validation_stats['rejection_rate'] = round(
            (stats['rejected_recordings'] / validation_stats['total_validated']) * 100, 1
        )
    
    # Define only Ateker languages
    ateker_languages = {
        'Ngakarimojong': 'kdj',
        'Ateso': 'teo', 
        'Soo (Tepes)': 'teu',
        'Ik (Icétot)': 'ikx'
    }
    
    prompts_dirs = [Path(current_app.config['UPLOAD_FOLDER']).parent / "prompts"]
    prompts, languages = load_prompts(prompts_dirs)
    filtered_languages = {name: code for name, code in languages.items() if name in ateker_languages}
    
    return render_template(
        "admin.html",
        stats=stats,
        validation_stats=validation_stats,
        recent_recordings=recent_recordings,
        recent_exports=recent_exports,
        recent_users=recent_users,
        languages=sorted(filtered_languages.items()),
    )

@bp.route('/admin/validation')
@admin_required
def admin_validation():
    """Data validation interface"""
    from .models import Recording, User
    
    # Define only Ateker languages
    ateker_languages = {
        'Ngakarimojong': 'kdj',
        'Ateso': 'teo', 
        'Soo (Tepes)': 'teu',
        'Ik (Icétot)': 'ikx'
    }
    
    # Get recordings from database for Ateker languages
    recordings = Recording.query.filter(
        Recording.language.in_(list(ateker_languages.values()))
    ).order_by(Recording.submitted_date.desc()).all()
    
    # Format validation data for template
    validation_data = []
    for recording in recordings:
        user = User.query.get(recording.user_id)
        validation_data.append({
            'id': recording.id,
            'recording_id': f"{recording.language}_{recording.prompt_group}_{recording.prompt_id}",
            'language': recording.language,
            'language_name': next((name for name, code in ateker_languages.items() if code == recording.language), recording.language.upper()),
            'user_id': recording.user_id,
            'username': user.username if user else 'Unknown',
            'prompt': recording.prompt_text,
            'audio_format': recording.audio_format,
            'filename': recording.filename,
            'duration': recording.duration,
            'submitted_date': recording.submitted_date.isoformat(),
            'status': recording.status,
            'validation_notes': recording.validation_notes or '',
            'validated_by': recording.validated_by,
            'validated_date': recording.validated_date.isoformat() if recording.validated_date else '',
            'audio_path': f"user_{recording.user_id}/{recording.language}/{recording.prompt_group}/{recording.filename}"
        })
    
    return render_template(
        "admin_validation.html",
        languages=sorted(ateker_languages.items()),
        validation_data=validation_data,
    )

@bp.route('/admin/validate_recording', methods=['POST'])
@admin_required
def validate_recording():
    """Update validation status for a recording"""
    from .models import Recording
    
    recording_id = request.form.get("recording_id")
    status = request.form.get("status")
    notes = request.form.get("notes", "")
    
    if status not in ["approved", "rejected"]:
        return jsonify({"error": "Invalid status"}), 400
    
    # Find recording by ID
    recording = Recording.query.get(recording_id)
    if not recording:
        return jsonify({"error": "Recording not found"}), 404
    
    # Update recording status
    recording.status = status
    recording.validation_notes = notes
    recording.validated_by = current_user.id
    recording.validated_date = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({"success": True})

@bp.route('/admin/prompts')
@admin_required
def admin_prompts():
    """Prompt management interface"""
    from .utils import load_prompts
    from pathlib import Path
    from collections import defaultdict
    
    # Get selected language from query parameter
    selected_language = request.args.get('language')
    
    prompts_dirs = [Path(current_app.config['UPLOAD_FOLDER']).parent / "prompts"]
    
    try:
        prompts, languages = load_prompts(prompts_dirs)
        
        # Organize prompts by groups for the selected language
        prompt_groups = None
        if selected_language and selected_language in prompts:
            prompt_groups = defaultdict(list)
            for prompt in prompts[selected_language]:
                prompt_groups[prompt.group].append(prompt)
                
    except Exception as e:
        current_app.logger.error(f"Error loading prompts: {e}")
        prompts, languages = {}, {}
        prompt_groups = {}
    
    return render_template('admin_prompts.html', 
        prompts=prompts, 
        languages=sorted(languages.items()),
        language=selected_language,
        prompt_groups=prompt_groups
    )

@bp.route('/admin/add_prompt', methods=['POST'])
@admin_required
def add_prompt():
    """Add a new prompt"""
    language = request.form.get('language')
    category = request.form.get('category')
    text = request.form.get('text')
    
    if not all([language, category, text]):
        return jsonify({'success': False, 'error': 'Missing required fields'})
    
    try:
        # Create the prompt file path
        prompts_dir = Path(current_app.config['UPLOAD_FOLDER']).parent / "prompts"
        language_dir = prompts_dir / f"{language}_{language}"  # This might need adjustment based on actual directory structure
        
        # Find the actual language directory name
        actual_lang_dir = None
        for item in prompts_dir.iterdir():
            if item.is_dir() and item.name.endswith(f"_{language}"):
                actual_lang_dir = item
                break
        
        if not actual_lang_dir:
            return jsonify({'success': False, 'error': 'Language directory not found'})
        
        # Create category file if it doesn't exist
        category_file = actual_lang_dir / f"{category}.txt"
        
        # Read existing prompts to get the next ID
        existing_prompts = []
        if category_file.exists():
            with open(category_file, 'r', encoding='utf-8') as f:
                existing_prompts = f.read().strip().split('\n') if f.read().strip() else []
        
        # Append new prompt
        with open(category_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{text}")
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Error adding prompt: {e}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/admin/delete_prompt', methods=['POST'])
@admin_required
def delete_prompt():
    """Delete a prompt"""
    language = request.form.get('language')
    category = request.form.get('category')
    prompt_id = request.form.get('id')
    
    if not all([language, category, prompt_id]):
        return jsonify({'success': False, 'error': 'Missing required fields'})
    
    try:
        # Similar logic to add_prompt but for deletion
        prompts_dir = Path(current_app.config['UPLOAD_FOLDER']).parent / "prompts"
        
        # Find the actual language directory name
        actual_lang_dir = None
        for item in prompts_dir.iterdir():
            if item.is_dir() and item.name.endswith(f"_{language}"):
                actual_lang_dir = item
                break
        
        if not actual_lang_dir:
            return jsonify({'success': False, 'error': 'Language directory not found'})
        
        category_file = actual_lang_dir / f"{category}.txt"
        
        if not category_file.exists():
            return jsonify({'success': False, 'error': 'Category file not found'})
        
        # Read all prompts and remove the one with matching ID
        with open(category_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Remove the prompt (this is simplified - might need ID-based logic)
        if len(lines) > int(prompt_id):
            del lines[int(prompt_id)]
            
            with open(category_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Error deleting prompt: {e}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/admin/delete_all_prompts', methods=['POST'])
@admin_required
def delete_all_prompts():
    """Delete all default prompts"""
    language = request.form.get('language')
    
    if not language:
        return jsonify({'success': False, 'error': 'Language is required'})
    
    try:
        prompts_dir = Path(current_app.config['UPLOAD_FOLDER']).parent / "prompts"
        
        # Find the actual language directory
        actual_lang_dir = None
        for item in prompts_dir.iterdir():
            if item.is_dir() and item.name.endswith(f"_{language}"):
                actual_lang_dir = item
                break
        
        if not actual_lang_dir:
            return jsonify({'success': False, 'error': 'Language directory not found'})
        
        # Delete all .txt files in the language directory
        deleted_files = []
        for txt_file in actual_lang_dir.glob("*.txt"):
            txt_file.unlink()
            deleted_files.append(txt_file.name)
        
        return jsonify({
            'success': True, 
            'message': f'Deleted {len(deleted_files)} prompt files from {language}',
            'deleted_files': deleted_files
        })
        
    except Exception as e:
        current_app.logger.error(f"Error deleting all prompts: {e}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/audio/<path:filepath>')
@login_required
def serve_audio(filepath):
    """Serve audio files for playback"""
    from flask import send_from_directory
    
    # Security check - ensure filepath is safe
    if '..' in filepath or filepath.startswith('/'):
        return jsonify({'error': 'Invalid file path'}), 400
    
    output_dir = Path(current_app.config['UPLOAD_FOLDER'])
    audio_path = output_dir / filepath
    
    if not audio_path.exists() or not audio_path.is_file():
        return jsonify({'error': 'Audio file not found'}), 404
    
    return send_from_directory(str(output_dir), filepath)

@bp.route('/templates/import_template.csv')
@login_required
def download_csv_template():
    """Download CSV template for bulk prompt import"""
    from flask import send_from_directory
    
    template_dir = os.path.join(current_app.root_path, 'templates')
    return send_from_directory(template_dir, 'import_template.csv', as_attachment=True, download_name='import_template.csv')

@bp.route('/admin/export', methods=['POST'])
@admin_required
def export_dataset():
    """Export dataset using existing export_dataset module"""
    try:
        # Get export parameters
        user_filter = request.form.get('user_filter', 'all')
        language_filter = request.form.get('language_filter', 'all')
        
        # Get base paths
        output_dir = Path(current_app.config['UPLOAD_FOLDER'])
        export_dir = output_dir.parent / "exports"
        export_dir.mkdir(exist_ok=True)
        
        # Create export directory with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_path = export_dir / f"export_{timestamp}"
        export_path.mkdir(exist_ok=True)
        
        # Determine input directory based on filters
        if user_filter == 'all':
            input_dir = output_dir
        else:
            input_dir = output_dir / f"user_{user_filter}"
        
        # Run the export dataset command
        cmd = [
            'python', '-m', 'export_dataset',
            str(input_dir),
            str(export_path),
            '--threshold', '0.5'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(output_dir.parent))
        
        if result.returncode != 0:
            current_app.logger.error(f"Export failed: {result.stderr}")
            return jsonify({'success': False, 'error': 'Export process failed'}), 500
        
        # Create ZIP file for download
        zip_path = export_dir / f"ateker_voices_export_{timestamp}.zip"
        current_app.logger.info(f"Creating ZIP file at: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            file_count = 0
            for file_path in export_path.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(export_path)
                    zipf.write(file_path, arcname)
                    file_count += 1
            current_app.logger.info(f"Added {file_count} files to ZIP")
        
        # Check ZIP file size
        zip_size = zip_path.stat().st_size
        current_app.logger.info(f"ZIP file created with size: {zip_size} bytes")
        
        # Clean up export directory
        import shutil
        shutil.rmtree(export_path, ignore_errors=True)
        current_app.logger.info("Cleaned up temporary export directory")
        
        return jsonify({
            'success': True,
            'download_url': f'/admin/download_export/{zip_path.name}',
            'message': 'Export completed successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Export error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/admin/download_export/<filename>')
@admin_required
def download_export(filename):
    """Download exported dataset"""
    try:
        output_dir = Path(current_app.config['UPLOAD_FOLDER'])
        export_dir = output_dir.parent / "exports"
        file_path = export_dir / filename
        
        current_app.logger.info(f"Download request for: {file_path}")
        
        if not file_path.exists():
            current_app.logger.error(f"Export file not found: {file_path}")
            return jsonify({'error': 'Export file not found'}), 404
        
        file_size = file_path.stat().st_size
        current_app.logger.info(f"Serving file with size: {file_size} bytes")
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/zip'
        )
        
    except Exception as e:
        current_app.logger.error(f"Download error: {e}")
        return jsonify({'error': 'Download failed'}), 500
