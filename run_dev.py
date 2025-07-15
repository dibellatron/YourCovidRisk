#!/usr/bin/env python3
"""
Development server runner with proper environment setup.

This script ensures the app runs in development mode with all debug features enabled.
"""

import os
import sys

# Set development environment
os.environ['FLASK_ENV'] = 'development'

# Import and run the app
from app import app

if __name__ == '__main__':
    print("🚀 Starting development server...")
    print("   Environment: DEVELOPMENT")
    print("   Debug mode: ON")
    print("   Console logging: ENABLED")
    print("   Browser auto-open: ENABLED")
    print()
    
    app.run(
        debug=True,
        host='127.0.0.1',
        port=5000
    )