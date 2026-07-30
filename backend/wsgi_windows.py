"""Production entrypoint for Windows. gunicorn (requirements.txt) doesn't
run on Windows at all -- it forks -- so this uses waitress instead, a
pure-Python WSGI server that works the same on Windows and Linux.

Run directly for a foreground smoke test:
    venv\\Scripts\\python wsgi_windows.py

In real deployment this is what windows_service.py calls to run as a
background Windows Service; see docs/WINDOWS_SERVER_INSTALL.md.
"""
import os

from dotenv import load_dotenv

load_dotenv()

from waitress import serve

from app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("WAITRESS_HOST", "127.0.0.1")
    port = int(os.environ.get("WAITRESS_PORT", "5000"))
    threads = int(os.environ.get("WAITRESS_THREADS", "8"))
    serve(app, host=host, port=port, threads=threads)
