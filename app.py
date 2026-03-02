"""Runtime entry‑point expected by Gunicorn (`web: gunicorn app:app`).

All real application code now lives in *covid_app* as Blueprints; this file
merely creates the Flask app via the factory and, when executed directly,
opens the browser as before.
"""

import os
import sys

# ---------------------------------------------------------------------------
# Auto‑activate virtual environment so `python3 app.py` works without
# manually sourcing venv/bin/activate first.
# ---------------------------------------------------------------------------
_venv_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv")
_venv_python = os.path.join(_venv_dir, "bin", "python3")
if (
    os.path.exists(_venv_python)
    and os.path.realpath(sys.prefix) != os.path.realpath(_venv_dir)
):
    os.execv(_venv_python, [_venv_python] + sys.argv)

import socket
import subprocess
import threading

from covid_app import create_app

app = create_app()


# ---------------------------------------------------------------------------
# Developer convenience helpers
# ---------------------------------------------------------------------------


def _find_available_port(start=5000, max_tries=100):
    """Return the first available port starting from *start*."""
    for port in range(start, start + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No available port found in range {start}–{start + max_tries - 1}")


def _open_browser(port):
    """Open the development server URL in Safari on macOS."""
    import platform

    if platform.system() != "Darwin":
        return

    url = f"http://127.0.0.1:{port}"
    apple_script = f"""
        tell application \"Safari\"
            activate
            open location \"{url}\"
        end tell
    """
    try:
        subprocess.Popen(["osascript", "-e", apple_script])
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    debug_mode = app.config.get('DEBUG', False)

    # Find available port (parent process discovers; child inherits via env).
    port = int(os.environ.get("FLASK_RUN_PORT", 0))
    if not port:
        port = _find_available_port()
        os.environ["FLASK_RUN_PORT"] = str(port)

    # Auto-open browser only in development mode (reloader child process).
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" and debug_mode:
        threading.Timer(1.0, lambda: _open_browser(port)).start()

    app.run(host='0.0.0.0', port=port, debug=debug_mode)
