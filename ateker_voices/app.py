#!/usr/bin/env python3
"""
Flask application runner for Ateker Voices
"""

import os
from ateker_voices import create_app

# Create the Flask app
app = create_app()

if __name__ == '__main__':
    # Development configuration
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    print(f"Starting Ateker Voices on http://{host}:{port}")
    print(f"Debug mode: {debug_mode}")
    
    app.run(
        host=host,
        port=port,
        debug=debug_mode
    )
