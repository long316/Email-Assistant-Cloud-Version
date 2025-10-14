#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Email Assistant API server
Provides REST API endpoints for health, OAuth, templates/assets (v2 blueprint),
classic/template sending, scheduling control, and utilities.
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Optional

from flask import Flask, request, jsonify, redirect
from flask_cors import CORS

from src.email_assistant import EmailAssistant
from src.gmail_auth import GmailAuthManager
from src.token_store import TokenStore
from src.config import get_config
from src.api_v2 import bp as api_v2_bp
from src.job_runner import JobRunner


app = Flask(__name__)
CORS(app)
app.register_blueprint(api_v2_bp)

# Global instances
email_assistant = EmailAssistant()
gmail_auth_manager = GmailAuthManager()
token_store = TokenStore()
cfg = get_config()

# Background task handle
current_task_thread: Optional[threading.Thread] = None
job_runner = JobRunner()
job_runner.start()


# ===== API Key Auth =====
def require_api_key(fn):
    def wrapper(*args, **kwargs):
        api_key_conf = cfg.get("API_KEY")
        if api_key_conf:
            provided = request.headers.get("X-API-Key")
            if not provided or provided != api_key_conf:
                return jsonify({"success": False, "error": "Unauthorized"}), 401
        return fn(*args, **kwargs)

    # Preserve original function metadata
    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


@app.route("/api/authenticate", methods=["POST"])
def authenticate_sender():
    """Authenticate sender email (legacy/local)"""
    try:
        data = request.get_json() or {}
        sender_email = data.get("sender_email")
        if not sender_email:
            return jsonify({"success": False, "error": "Missing sender_email"}), 400
        success = email_assistant.authenticate_sender(sender_email)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/validate_excel", methods=["POST"])
def validate_excel():
    """Validate Excel file path"""
    try:
        data = request.get_json() or {}
        excel_file_path = data.get("excel_file_path")
        if not excel_file_path:
            return jsonify({"success": False, "error": "Missing excel_file_path"}), 400
        success = email_assistant.validate_excel_file(excel_file_path)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/preview", methods=["POST"])
def preview_emails():
    """Preview pending email list from Excel"""
    try:
        data = request.get_json() or {}
        excel_file_path = data.get("excel_file_path")
        if not excel_file_path:
            return jsonify({"success": False, "error": "Missing excel_file_path"}), 400
        result = email_assistant.preview_email_list(excel_file_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/send_emails", methods=["POST"])
@require_api_key
def send_emails():
    """Send emails in classic mode (subject/content/html)."""
    global current_task_thread
    try:
        data = request.get_json() or {}
        sender_email = data.get("sender_email")
        excel_file_path = data.get("excel_file_path")
        if not sender_email or not excel_file_path:
            return jsonify({
                "success": False,
                "error": "Missing required parameters: sender_email, excel_file_path",
            }), 400

        subject = data.get("subject")
        content = data.get("content")
        html_content = data.get("html_content")
        attachments = data.get("attachments", [])
        start_time_str = data.get("start_time")
        min_interval = data.get("min_interval", 20)
        max_interval = data.get("max_interval", 90)

        # parse start time
        start_time = None
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str)
            except ValueError:
                return jsonify({"success": False, "error": "Invalid start_time (ISO format)"}), 400
        else:
            start_time = datetime.now()

        if current_task_thread and current_task_thread.is_alive():
            return jsonify({"success": False, "error": "A task is already running"}), 409

        def run_email_task():
            email_assistant.send_emails(
                sender_email=sender_email,
                excel_file_path=excel_file_path,
                subject=subject,
                content=content,
                html_content=html_content,
                attachments=attachments,
                start_time=start_time,
                min_interval=min_interval,
                max_interval=max_interval,
            )

        current_task_thread = threading.Thread(target=run_email_task, daemon=True)
        current_task_thread.start()
        return jsonify({"success": True, "message": "Task started", "task_id": id(current_task_thread)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/status", methods=["GET"])
def get_status():
    try:
        status = email_assistant.get_scheduler_status()
        return jsonify({"success": True, "status": status})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/pause", methods=["POST"])
@require_api_key
def pause_sending():
    try:
        email_assistant.pause_sending()
        return jsonify({"success": True, "message": "Paused"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/resume", methods=["POST"])
@require_api_key
def resume_sending():
    try:
        email_assistant.resume_sending()
        return jsonify({"success": True, "message": "Resumed"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stop", methods=["POST"])
@require_api_key
def stop_sending():
    try:
        email_assistant.stop_sending()
        return jsonify({"success": True, "message": "Stopped"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/statistics", methods=["POST"])
def get_statistics():
    try:
        data = request.get_json() or {}
        excel_file_path = data.get("excel_file_path")
        if not excel_file_path:
            return jsonify({"success": False, "error": "Missing excel_file_path"}), 400
        result = email_assistant.get_statistics(excel_file_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/validate_templates", methods=["POST"])
def validate_templates():
    try:
        data = request.get_json() or {}
        excel_file_path = data.get("excel_file_path")
        if not excel_file_path:
            return jsonify({"success": False, "error": "Missing excel_file_path"}), 400
        result = email_assistant.validate_templates(excel_file_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/preview_template_emails", methods=["POST"])
def preview_template_emails():
    try:
        data = request.get_json() or {}
        excel_file_path = data.get("excel_file_path")
        max_previews = int(data.get("max_previews", 3))
        if not excel_file_path:
            return jsonify({"success": False, "error": "Missing excel_file_path"}), 400
        result = email_assistant.preview_template_emails(excel_file_path, max_previews)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/send_template_emails", methods=["POST"])
@require_api_key
def send_template_emails():
    """Send emails using templates (scheduled in background)."""
    global current_task_thread
    try:
        data = request.get_json() or {}
        sender_email = data.get("sender_email")
        excel_file_path = data.get("excel_file_path")
        attachments = data.get("attachments", [])
        start_time_str = data.get("start_time")
        min_interval = data.get("min_interval", 20)
        max_interval = data.get("max_interval", 90)
        if not sender_email or not excel_file_path:
            return jsonify({"success": False, "error": "Missing required parameters"}), 400

        # parse start time
        start_time = None
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str)
            except ValueError:
                return jsonify({"success": False, "error": "Invalid start_time (ISO format)"}), 400
        else:
            start_time = datetime.now()

        def run_task():
            email_assistant.send_template_emails(
                sender_email=sender_email,
                excel_file_path=excel_file_path,
                attachments=attachments,
                start_time=start_time,
                min_interval=min_interval,
                max_interval=max_interval,
            )

        current_task_thread = threading.Thread(target=run_task, daemon=True)
        current_task_thread.start()
        return jsonify({
            "success": True,
            "message": "Template email task started",
            "task_id": f"template_task_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ===== Error handlers =====
@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "API endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "Internal server error"}), 500


def create_app():
    """Factory for WSGI servers."""
    return app


def run_server(host: str = "127.0.0.1", port: int = 5000, debug: bool = False):
    """Run development server."""
    print("Starting Email Assistant API...")
    print(f"Listening at: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


# ===== OAuth Web Flow Routes =====
@app.route("/oauth/google/authorize", methods=["GET"])
def oauth_google_authorize():
    try:
        import base64, json
        sender_email = request.args.get("sender_email")
        mu = int(request.args.get("master_user_id", "0") or 0)
        store = int(request.args.get("store_id", "0") or 0)
        return_url = request.args.get("return_url")
        if not sender_email:
            return jsonify({"success": False, "error": "Missing sender_email"}), 400
        payload = {"sender": sender_email, "mu": mu, "store": store, "return_url": return_url}
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        state = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
        redirect_uri = cfg["OAUTH_REDIRECT_URL"]
        auth_url, _ = gmail_auth_manager.build_authorize_url(redirect_uri, state=state)
        return redirect(auth_url)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/oauth/google/callback", methods=["GET"])
def oauth_google_callback():
    try:
        import base64, json
        from urllib.parse import urlencode
        from src.url_utils import is_return_url_allowed
        from src.dao_mysql import upsert_sender_account

        code = request.args.get("code")
        state = request.args.get("state")
        if not code:
            return jsonify({"success": False, "error": "Missing code"}), 400

        payload = {}
        if state:
            pad = "=" * (-len(state) % 4)
            try:
                decoded = base64.urlsafe_b64decode(state + pad).decode("utf-8")
                payload = json.loads(decoded)
            except Exception:
                payload = {}

        mu = int(payload.get("mu", 0) or 0)
        store = int(payload.get("store", 0) or 0)
        return_url = payload.get("return_url")

        redirect_uri = cfg["OAUTH_REDIRECT_URL"]
        email, creds_json = gmail_auth_manager.exchange_code_for_token(code, redirect_uri)

        # save token to DB and file store (best effort)
        try:
            upsert_sender_account(mu, store, email, json.loads(creds_json))
        except Exception:
            pass
        try:
            token_store.save(email, creds_json)
        except Exception:
            pass

        allowed = cfg.get("ALLOWED_RETURN_URL_HOSTS", "")
        default_url = cfg.get("DEFAULT_RETURN_URL", "")
        allow_local = cfg.get("ALLOW_DEV_LOCALHOST", False)

        target = None
        if return_url and is_return_url_allowed(return_url, allowed, allow_local):
            target = return_url
        elif default_url:
            target = default_url

        if target:
            q = urlencode({"success": 1, "email": email})
            return redirect(f"{target}{'&' if ('?' in target) else '?'}{q}")
        return jsonify({"success": True, "email": email})
    except Exception as e:
        try:
            default_url = cfg.get("DEFAULT_RETURN_URL", "")
            if default_url:
                from urllib.parse import urlencode
                q = urlencode({"success": 0, "error": str(e)})
                return redirect(f"{default_url}{'&' if ('?' in default_url) else '?'}{q}")
        except Exception:
            pass
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Email Assistant API server")
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=int, default=5000, help="Server port")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()
    run_server(args.host, args.port, args.debug)
