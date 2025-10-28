import os
from pathlib import Path

# Load .env values if python-dotenv is available
try:
    from dotenv import load_dotenv, find_dotenv

    # Find nearest .env from CWD upwards; do not override existing env
    load_dotenv(find_dotenv(), override=False)
except Exception:
    # If python-dotenv is not installed or any error occurs, skip silently
    pass


def get_config():
    # Compute a stable default files root: project_root/files
    project_root = Path(__file__).resolve().parents[1]
    default_files_root = str(project_root / "files")
    return {
        "AUTH_FLOW": os.getenv("AUTH_FLOW", "desktop"),
        "GOOGLE_OAUTH_CLIENT_JSON": os.getenv("GOOGLE_OAUTH_CLIENT_JSON", "credentials.json"),
        "OAUTH_REDIRECT_URL": os.getenv("OAUTH_REDIRECT_URL", "http://127.0.0.1:5000/oauth/google/callback"),
        "API_KEY": os.getenv("API_KEY"),
        "ENCRYPTION_KEY": os.getenv("ENCRYPTION_KEY"),
        "DATABASE_URL": os.getenv("DATABASE_URL"),
        "ALLOWED_RETURN_URL_HOSTS": os.getenv("ALLOWED_RETURN_URL_HOSTS", ""),
        "DEFAULT_RETURN_URL": os.getenv("DEFAULT_RETURN_URL", ""),
        "ALLOW_DEV_LOCALHOST": os.getenv("ALLOW_DEV_LOCALHOST", "false").lower() == "true",
        # Absolute path to files root; defaults to project_root/files
        "FILES_ROOT": os.getenv("FILES_ROOT", default_files_root),
    }
