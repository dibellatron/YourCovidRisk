#!/usr/bin/env python3
"""
Production server runner with proper environment setup.

This script ensures the app runs in production mode with debug features disabled.
Note: For actual production, use Gunicorn instead of this script.
"""

import os
import sys

# Set production environment
os.environ['FLASK_ENV'] = 'production'

# Import and run the app
from app import app

if __name__ == '__main__':
    print("🏭 Starting production server...")
    print("   Environment: PRODUCTION")
    print("   Debug mode: OFF")
    print("   Console logging: MINIMAL")
    print("   Browser auto-open: DISABLED")
    print()
    print("   Note: For actual production deployment, use:")
    print("   gunicorn app:app --bind 0.0.0.0:$PORT")
    print()
    
    app.run(
        debug=False,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000))
    )