"""Flask application factory packaged for easy testing & deployment."""

from flask import Flask, request, jsonify, render_template, current_app
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import pathlib
import os
import logging

CSP = {
    "default-src": ["'self'", "data:", "https:"],
    "script-src": [
        "'self'",
        "'unsafe-inline'",
        "'unsafe-eval'",
        "https://www.googletagmanager.com",
        "https://www.google-analytics.com",
    ],
    "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https:"],
    "font-src": ["'self'", "data:", "https://fonts.gstatic.com", "https:"],
    "img-src": ["'self'", "data:", "https:"],
    "connect-src": ["'self'", "https://www.google-analytics.com"],
    "object-src": ["'none'"]
}


def create_app(config_name=None) -> Flask:  # pragma: no cover – trivial factory
    """Create Flask application with environment-based configuration."""
    # Import config here to avoid circular imports
    from config import get_config
    
    root_dir = pathlib.Path(__file__).resolve().parent.parent  # project root
    app = Flask(
        __name__,
        static_folder=str(root_dir / "static"),
        template_folder=str(root_dir / "templates"),
    )

    # Load configuration based on environment
    if config_name:
        from config import config
        config_class = config.get(config_name, config['default'])
    else:
        config_class = get_config()
    
    app.config.from_object(config_class)
    config_class.init_app(app)

    # Security headers - disable HTTPS enforcement in development/testing
    if app.config['TESTING'] or app.config['DEBUG']:
        Talisman(app, content_security_policy=CSP, force_https=False)
    else:
        Talisman(app, content_security_policy=CSP)

    # Rate limiting to prevent DoS attacks
    def rate_limit_key():
        """Custom key function for rate limiting that considers user agent for bot detection."""
        user_agent = request.headers.get('User-Agent', '').lower()
        # Stricter limits for suspicious user agents
        if any(bot in user_agent for bot in ['bot', 'crawler', 'spider', 'curl', 'wget', 'python-requests']):
            return f"bot:{get_remote_address()}"
        return get_remote_address()

    # Configure rate limiter with different limits for regular users vs bots
    limiter = Limiter(
        app=app,
        key_func=rate_limit_key,
        default_limits=["1000 per hour", "50 per minute"],  # General limits
        storage_uri="memory://",  # In-memory storage for simplicity
    )
    
    # Store limiter in app for use in blueprints
    app.limiter = limiter

    # Make environment info available to templates
    @app.context_processor
    def inject_config():
        return {
            'DEBUG': app.config['DEBUG'],
            'FLASK_ENV': os.environ.get('FLASK_ENV', 'development'),
            'is_development': app.config['DEBUG'],
            'is_production': not app.config['DEBUG']
        }

    # Blueprints
    from .blueprints.exposure import exposure_bp
    from .blueprints.main import main_bp
    from .blueprints.testcalc import test_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(test_bp)
    app.register_blueprint(exposure_bp)
    
    # Apply rate limiting to calculator endpoints specifically
    # These are the expensive computation endpoints that need protection
    calculator_endpoints = [
        "exposure.exposure_calculator",
        "exposure.calculate_time_varying_risk", 
        "testcalc.test_calculator"
    ]
    
    for endpoint in calculator_endpoints:
        if endpoint in app.view_functions:
            # 30 calculations per minute for regular users, stricter for bots
            limiter.limit("30 per minute", methods=["POST"])(app.view_functions[endpoint])
            print(f"DEBUG: Applied rate limit to {endpoint}")
        else:
            print(f"DEBUG: Endpoint {endpoint} not found in view_functions")
    
    # Debug: List all registered endpoints
    print(f"DEBUG: Available view_functions: {list(app.view_functions.keys())}")

    # Custom rate limit handler
    @app.errorhandler(429)
    def rate_limit_handler(e):
        user_agent = request.headers.get('User-Agent', 'Unknown')
        ip = get_remote_address()
        endpoint = request.endpoint
        app.logger.warning(f"Rate limit exceeded: IP={ip}, endpoint={endpoint}, user_agent={user_agent}")
        print(f"DEBUG: Rate limit handler called for {request.path}")
        
        # Return JSON for API endpoints, HTML for web pages
        if request.path.startswith('/api/') or request.headers.get('Content-Type') == 'application/json':
            response = jsonify({
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please wait and try again.",
                "retry_after": "60 seconds"
            })
            print(f"DEBUG: Returning JSON rate limit response")
            return response, 429
        else:
            print(f"DEBUG: Returning HTML rate limit response")
            return render_template('rate_limit.html'), 429

    # Add general request logging for monitoring
    @app.before_request
    def log_requests():
        # Debug: Log all POST requests to see what's happening
        if request.method == 'POST':
            user_agent = request.headers.get('User-Agent', 'Unknown')
            ip = get_remote_address()
            print(f"DEBUG: POST request to {request.endpoint} from {ip}")
            print(f"DEBUG: Path: {request.path}")
            # Check if rate limiter is working
            if hasattr(current_app, 'limiter'):
                print(f"DEBUG: Rate limiter found")
            else:
                print(f"DEBUG: No rate limiter found")

    # ------------------------------------------------------------------
    # Backward‑compatibility endpoint aliases for templates created before
    # the blueprint refactor.
    # ------------------------------------------------------------------

    # alias for 'exposure_calculator'
    app.add_url_rule(
        "/exposure",
        endpoint="exposure_calculator",
        view_func=app.view_functions["exposure.exposure_calculator"],
        methods=["GET", "POST"],
    )

    # alias for 'test_calculator'
    app.add_url_rule(
        "/test",
        endpoint="test_calculator",
        view_func=app.view_functions["testcalc.test_calculator"],
        methods=["GET", "POST"],
    )
    # Register Jinja filters for percentage formatting
    from calculators.formatting import format_percent, format_ci_filter
    app.add_template_filter(format_percent, 'percent')
    app.add_template_filter(format_ci_filter, 'ci_format')

    # alias for 'faq'
    app.add_url_rule(
        "/faq",
        endpoint="faq",
        view_func=app.view_functions["main.faq"],
        methods=["GET"],
    )

    # alias for 'index'
    app.add_url_rule(
        "/",
        endpoint="index",
        view_func=app.view_functions["main.index"],
        methods=["GET"],
    )

    return app
