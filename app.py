"""Runtime entry‑point expected by Gunicorn (`web: gunicorn app:app`).

All real application code now lives in *covid_app* as Blueprints; this file
merely creates the Flask app via the factory and, when executed directly,
opens the browser as before.
"""

import os
import subprocess
import threading

from covid_app import create_app

app = create_app()


# ---------------------------------------------------------------------------
# Developer convenience – auto‑open local browser on macOS when run directly.
# ---------------------------------------------------------------------------


def _open_browser():
    """Open the development server URL in Safari on macOS.

    Wrapped in a platform check so it does *not* run (and therefore cannot
    error) on other operating systems or production servers.
    """

    import platform

    if platform.system() != "Darwin":
        return

    url = "http://127.0.0.1:5000"
    apple_script = f"""
        tell application \"Safari\"
            activate
            open location \"{url}\"
        end tell
    """
    try:
        subprocess.Popen(["osascript", "-e", apple_script])
    except FileNotFoundError:
        # osascript not available (minimal environments); silently ignore.
        pass


if __name__ == "__main__":
    # Auto-open browser only in development mode
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" and app.config['DEBUG']:
        threading.Timer(1.0, _open_browser).start()
    
    # Use environment-based debug setting
    debug_mode = app.config.get('DEBUG', False)
    app.run(host='0.0.0.0', debug=debug_mode)
