from datetime import datetime
from .extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    """User account model."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    recordings = db.relationship('Recording', backref='user', lazy='dynamic')
    
    def set_password(self, password: str):
        """Create hashed password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Check hashed password."""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Recording(db.Model):
    """Audio recording model."""
    __tablename__ = 'recordings'
    
    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(512), nullable=False)
    language = db.Column(db.String(32), nullable=False)
    text = db.Column(db.Text, nullable=True)
    duration = db.Column(db.Float, nullable=True)
    sample_rate = db.Column(db.Integer, nullable=True)
    channels = db.Column(db.Integer, default=1)
    bit_depth = db.Column(db.Integer, nullable=True)
    is_validated = db.Column(db.Boolean, default=False)
    validation_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'file_path': self.file_path,
            'language': self.language,
            'text': self.text,
            'duration': self.duration,
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'bit_depth': self.bit_depth,
            'is_validated': self.is_validated,
            'validation_notes': self.validation_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'user_id': self.user_id
        }
    
    def __repr__(self):
        return f'<Recording {self.id} - {self.language}>'

class DatasetExport(db.Model):
    """Dataset export history."""
    __tablename__ = 'dataset_exports'
    
    id = db.Column(db.Integer, primary_key=True)
    export_format = db.Column(db.String(32), nullable=False)  # 'zip', 'csv', 'json'
    language = db.Column(db.String(32), nullable=False)
    file_path = db.Column(db.String(512), nullable=True)  # Path to the exported file
    file_size = db.Column(db.BigInteger, nullable=True)  # Size in bytes
    record_count = db.Column(db.Integer, nullable=True)  # Number of recordings exported
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref='exports')
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'export_format': self.export_format,
            'language': self.language,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'record_count': self.record_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user_id': self.user_id,
            'user_username': self.user.username if self.user else None
        }
    
    def __repr__(self):
        return f'<DatasetExport {self.id} - {self.language}.{self.export_format}>'
