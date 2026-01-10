from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


class User(UserMixin, db.Model):
    """User model for authentication."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime)
    
    # Demographic fields
    age_group = db.Column(db.String(20), nullable=True)  # 18-24, 25-34, 35-44, 45-54, 55+
    gender = db.Column(db.String(10), nullable=True)  # male, female, other, prefer_not_to_say
    
    # Relationships
    recordings = db.relationship('Recording', foreign_keys='Recording.user_id', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Recording(db.Model):
    """Recording model to track user audio submissions."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    language = db.Column(db.String(10), nullable=False)
    prompt_group = db.Column(db.String(50), nullable=False)
    prompt_id = db.Column(db.String(50), nullable=False)
    prompt_text = db.Column(db.Text, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    audio_format = db.Column(db.String(10), nullable=False)
    duration = db.Column(db.String(20))
    file_size = db.Column(db.Integer)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, approved, rejected
    validation_notes = db.Column(db.Text)
    validated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    validated_date = db.Column(db.DateTime)
    submitted_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    session_id = db.Column(db.String(36), nullable=False)  # UUID for session tracking
    
    # Add unique constraint to prevent duplicate recordings
    __table_args__ = (
        db.UniqueConstraint('user_id', 'language', 'prompt_group', 'prompt_id', name='unique_user_prompt'),
    )
    
    def __repr__(self):
        return f'<Recording {self.id}: {self.language}_{self.prompt_group}_{self.prompt_id}>'


class RecordingSession(db.Model):
    """Recording session model to track user recording sessions."""
    id = db.Column(db.String(36), primary_key=True)  # UUID
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    language = db.Column(db.String(10), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ended_at = db.Column(db.DateTime)
    recordings_count = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref='recording_sessions')
    
    def __repr__(self):
        return f'<RecordingSession {self.id}: User {self.user_id}, {self.recordings_count} recordings>'


class DatasetExport(db.Model):
    """Dataset export tracking model."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    language = db.Column(db.String(10), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)
    export_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(20), default='completed', nullable=False)
    
    def __repr__(self):
        return f'<DatasetExport {self.id}: {self.language}>'
