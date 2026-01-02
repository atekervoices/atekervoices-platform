# Flask-Login Authentication for Ateker Voices

This document describes the Flask-Login authentication system implemented for the Ateker Voices platform.

## Overview

The authentication system has been converted from Firebase authentication to Flask-Login with Flask-SQLAlchemy for better integration with the Flask backend.

## Key Components

### 1. User Model (`models.py`)
- **User** class with Flask-Login `UserMixin`
- Fields: `id`, `username`, `email`, `password_hash`, `is_admin`, `is_active`, `created_at`, `last_login`
- Password hashing using Werkzeug's `generate_password_hash()` and `check_password_hash()`
- Relationships with `Recording` and `DatasetExport` models

### 2. Flask-Login Configuration (`extensions.py`)
- LoginManager initialized with login view set to `'main.login'`
- User loader function `load_user()` for Flask-Login session management

### 3. Authentication Routes (`routes.py`)
- **Login**: `/login` - GET/POST route for user authentication
- **Register**: `/register` - GET/POST route for user registration
- **Logout**: `/logout` - POST route for user logout (requires login)
- **Record**: `/record` - Protected route for audio recording (requires login)
- **Admin**: `/admin` - Protected admin routes (requires admin privileges)

### 4. Authentication Decorators
- `@login_required`: Protects routes requiring authentication
- `@admin_required`: Custom decorator for admin-only access

### 5. Templates
- **Login**: `login.html` - User login form with remember me option
- **Register**: `register.html` - User registration form with validation
- **Header**: `components/header.html` - Navigation with authentication state

## Features

### User Authentication
- Username/password authentication
- Session management with Flask-Login
- "Remember me" functionality
- Automatic redirects for protected routes

### Role-Based Access Control
- **Admin users**: Full access to admin panel and all features
- **Regular users**: Access to recording features only
- Admin protection for sensitive routes

### Security Features
- Password hashing with Werkzeug
- CSRF protection ready (Flask-WTF installed)
- Session security with Flask-Login
- Input validation and sanitization

## Default Admin Account

A default admin account is automatically created:
- **Username**: `admin`
- **Password**: `AtekerAdmin2025!`
- **Email**: `admin@atekervoices.org`

## Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Database
```bash
python start_flask.py
```
The startup script will automatically:
- Create database tables
- Create default admin user if it doesn't exist
- Start the Flask application

### 3. Access the Application
- **URL**: http://localhost:5000
- **Admin Login**: admin / AtekerAdmin2025!
- **Register**: Create new user accounts via the registration form

## File Structure

```
ateker_voices/
├── __init__.py          # Flask app factory
├── extensions.py        # Flask-Login and SQLAlchemy setup
├── models.py           # User model with Flask-Login integration
├── routes.py           # Authentication and protected routes
├── utils.py            # Helper functions for prompts and validation
├── commands.py         # CLI commands for admin management
├── app.py             # Flask application runner
├── templates/
│   ├── login.html     # Login form
│   ├── register.html  # Registration form
│   └── components/
│       └── header.html # Navigation with auth state
└── start_flask.py     # Startup script with DB initialization
```

## Route Protection

### Protected Routes (require login):
- `/record` - Audio recording interface
- `/submit` - Audio submission
- `/logout` - User logout

### Admin Routes (require admin):
- `/admin` - Admin dashboard
- `/admin/validation` - Data validation interface
- `/admin/validate_recording` - Recording validation

## Migration from Firebase

The authentication system has been migrated from Firebase to Flask-Login:

### Changes Made:
1. **Backend**: Converted from Quart (async) to Flask (sync)
2. **Authentication**: Firebase Auth → Flask-Login + SQLAlchemy
3. **User Management**: JSON file → Database with User model
4. **Session Management**: Firebase sessions → Flask-Login sessions
5. **Templates**: Updated to show authentication state

### Benefits:
- Better integration with Flask backend
- Full control over user data
- No external dependencies for authentication
- Improved security with password hashing
- Role-based access control

## Usage Examples

### Checking Authentication in Templates:
```html
{% if current_user.is_authenticated %}
    <p>Welcome, {{ current_user.username }}!</p>
    {% if current_user.is_admin %}
        <a href="/admin">Admin Panel</a>
    {% endif %}
{% else %}
    <a href="/login">Login</a>
    <a href="/register">Register</a>
{% endif %}
```

### Protecting Routes:
```python
from flask_login import login_required

@app.route('/protected')
@login_required
def protected_route():
    return "This page requires authentication"
```

### Admin-Only Routes:
```python
@admin_required
def admin_only_route():
    return "This page requires admin access"
```

## Security Considerations

1. **Password Security**: All passwords are hashed using Werkzeug's secure defaults
2. **Session Security**: Flask-Login handles secure session management
3. **Input Validation**: Form inputs are validated and sanitized
4. **CSRF Protection**: Flask-WTF is installed and ready for CSRF token implementation
5. **Admin Protection**: Sensitive routes require admin privileges

## Future Enhancements

1. **Email Verification**: Add email verification for new registrations
2. **Password Reset**: Implement password reset functionality
3. **Two-Factor Authentication**: Add 2FA for enhanced security
4. **OAuth Integration**: Add social login options
5. **Rate Limiting**: Implement rate limiting for login attempts
6. **Audit Logging**: Add comprehensive audit logging

## Troubleshooting

### Common Issues:

1. **Import Errors**: Ensure all required packages are installed
2. **Database Issues**: Run the startup script to initialize the database
3. **Login Issues**: Check that the admin user exists in the database
4. **Template Errors**: Ensure all template paths are correct

### Debug Mode:
The application runs in debug mode by default. Set `FLASK_DEBUG=False` for production.

## Production Deployment

For production deployment:
1. Set a secure `SECRET_KEY`
2. Use a production database (PostgreSQL, MySQL)
3. Set `FLASK_DEBUG=False`
4. Configure proper session security
5. Set up HTTPS
6. Use a production WSGI server (Gunicorn, uWSGI)
