"""Application configuration module.

This module provides environment-based configuration for the Flask application.
Set FLASK_ENV environment variable to control which configuration is used:
- development: Debug mode enabled, verbose logging
- production: Debug mode disabled, minimal logging
- testing: Testing configuration with debug enabled
"""

import os
from pathlib import Path


class Config:
    """Base configuration class."""
    
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Application settings
    DEBUG = False
    TESTING = False
    
    # Logging
    LOG_LEVEL = 'INFO'
    
    @staticmethod
    def init_app(app):
        """Initialize application with this configuration."""
        pass


class DevelopmentConfig(Config):
    """Development configuration."""
    
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    
    @staticmethod
    def init_app(app):
        """Initialize development-specific settings."""
        print("🚀 Running in DEVELOPMENT mode")
        print("   - Debug mode: ON")
        print("   - Console logging: ENABLED")


class ProductionConfig(Config):
    """Production configuration."""
    
    DEBUG = False
    LOG_LEVEL = 'WARNING'
    
    @staticmethod
    def init_app(app):
        """Initialize production-specific settings."""
        # Use proper logging instead of print in production
        import logging
        logging.basicConfig(level=logging.WARNING)
        logger = logging.getLogger(__name__)
        logger.info("Running in PRODUCTION mode")


class TestingConfig(Config):
    """Testing configuration."""
    
    DEBUG = True
    TESTING = True
    LOG_LEVEL = 'DEBUG'
    
    @staticmethod
    def init_app(app):
        """Initialize testing-specific settings."""
        print("🧪 Running in TESTING mode")


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get the appropriate configuration based on FLASK_ENV."""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])


def is_development():
    """Check if running in development mode."""
    env = os.environ.get('FLASK_ENV', 'development')
    return env == 'development'


def is_production():
    """Check if running in production mode."""
    env = os.environ.get('FLASK_ENV', 'development')
    return env == 'production'


def is_testing():
    """Check if running in testing mode."""
    env = os.environ.get('FLASK_ENV', 'development')
    return env == 'testing'