import os
import base64
import json
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename

from src.config import get_config
from src.dao_mysql import (
    create_template,
    list_templates,
    get_template,
    update_template,
    delete_template,
    upsert_sender_account,
)
from src.assets_util import ensure_tenant_dirs
from src.dao_mysql import (
    create_job,
    add_job_recipients,
    get_job,
    list_job_recipients,
    resolve_attachment_paths,
    list_job_events,
    set_job_status,
    list_assets,
    get_asset_by_id,
    delete_asset,
    list_senders,
    delete_sender,
)
from src.template_files import TemplateFileManager
from datetime import datetime, timezone
import mimetypes


bp = Blueprint("api_v2", __name__, url_prefix="/api")


def _require_api_key():
    cfg = get_config()
    api_key_conf = cfg.get("API_KEY")
    if not api_key_conf:
        return True, None
    provided = request.headers.get("X-API-Key")
    if not provided or provided != api_key_conf:
        return False, (jsonify({"success": False, "error": "Unauthorized"}), 401)
    return True, None


@bp.route("/db/health", methods=["GET"])
def db_health():
    try:
        from src.db_util import db_ping
        res = db_ping()
        code = 200 if res.get("success") else 500
        return jsonify(res), code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ===== Jobs (JSON-based sending) =====
@bp.route("/jobs/send_template_emails", methods=["POST"])
def jobs_send_template():
    ok, resp = _require_api_key()
    if not ok:
        return resp
    data = request.get_json() or {}
    required = ["master_user_id", "store_id", "sender_email", "recipients"]
    for k in required:
        if k not in data:
            return jsonify({"success": False, "error": f"missing {k}"}), 400
    mu = str(data["master_user_id"])
    store = str(data["store_id"])
    sender = data["sender_email"]
    template_id = data.get("template_id")
    if template_id is not None:
        try:
            template_id = int(template_id)
        except Exception:
            return jsonify({"success": False, "error": "invalid template_id"}), 400
    recipients = data["recipients"]
    min_interval = int(data.get("min_interval", 20))
    max_interval = int(data.get("max_interval", 90))
    webhook_url = data.get("webhook_url")
    attachments = data.get("attachments", [])
    start_time_str = data.get("start_time")

    # compute schedule_at (UTC naive)
    schedule_at = None
    if start_time_str:
        try:
            dt = datetime.fromisoformat(start_time_str)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            schedule_at = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        except Exception:
            return jsonify({"success": False, "error": "invalid start_time"}), 400
    else:
        # immediate
        schedule_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")

    job_id = create_job(mu, store, "template", sender, template_id, None, None, None, min_interval, max_interval, webhook_url, schedule_at)

    # resolve attachments and embed into recipient variables under __attachments__ to keep for runner
    resolved_attachments = resolve_attachment_paths(mu, store, attachments)
    for r in recipients:
        vars = r.get("variables") or {}
        if not isinstance(vars, dict):
            vars = {}
        vars["__attachments__"] = resolved_attachments
        r["variables"] = vars
    added = add_job_recipients(job_id, recipients)

    # Start background sending using scheduler via classic app instance
    from src.email_scheduler import EmailScheduler
    from src.gmail_auth import GmailAuthManager
    from src.excel_processor import ExcelProcessor

    gmail_auth_manager = GmailAuthManager()
    excel_processor = ExcelProcessor()
    scheduler = EmailScheduler(gmail_auth_manager, excel_processor, min_interval=min_interval, max_interval=max_interval)

    # Resolve attachment paths relative to files/
    resolved_attachments = resolve_attachment_paths(mu, store, attachments)

    def run_job():
        try:
            scheduler.send_job_emails_from_db(
                sender_email=sender,
                master_user_id=mu,
                store_id=store,
                job_id=job_id,
                job_type="template",
                template_id=template_id,
                attachments=resolved_attachments,
                min_interval=min_interval,
                max_interval=max_interval,
            )
        except Exception:
            pass

    # Enqueue only; runner will pick it up
    return jsonify({"success": True, "job_id": job_id, "recipients": added, "queued": True, "schedule_at": schedule_at})


@bp.route("/jobs/send_emails", methods=["POST"])
def jobs_send_custom():
    ok, resp = _require_api_key()
    if not ok:
        return resp
    data = request.get_json() or {}
    required = ["master_user_id", "store_id", "sender_email", "subject", "content", "recipients"]
    for k in required:
        if k not in data:
            return jsonify({"success": False, "error": f"missing {k}"}), 400
    mu = str(data["master_user_id"])
    store = str(data["store_id"])
    sender = data["sender_email"]
    subject = data["subject"]
    content = data["content"]
    html_content = data.get("html_content")
    recipients = data["recipients"]
    min_interval = int(data.get("min_interval", 20))
    max_interval = int(data.get("max_interval", 90))
    webhook_url = data.get("webhook_url")
    attachments = data.get("attachments", [])
    start_time_str = data.get("start_time")
    # compute schedule_at
    schedule_at = None
    if start_time_str:
        try:
            dt = datetime.fromisoformat(start_time_str)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            schedule_at = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        except Exception:
            return jsonify({"success": False, "error": "invalid start_time"}), 400
    else:
        schedule_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")

    job_id = create_job(mu, store, "custom", sender, None, subject, content, html_content, min_interval, max_interval, webhook_url, schedule_at)
    resolved_attachments = resolve_attachment_paths(mu, store, attachments)
    for r in recipients:
        vars = r.get("variables") or {}
        if not isinstance(vars, dict):
            vars = {}
        vars["__attachments__"] = resolved_attachments
        r["variables"] = vars
    added = add_job_recipients(job_id, recipients)

    from src.email_scheduler import EmailScheduler
    from src.gmail_auth import GmailAuthManager
    from src.excel_processor import ExcelProcessor

    gmail_auth_manager = GmailAuthManager()
    excel_processor = ExcelProcessor()
    scheduler = EmailScheduler(gmail_auth_manager, excel_processor, min_interval=min_interval, max_interval=max_interval)

    resolved_attachments = resolve_attachment_paths(mu, store, attachments)

    def run_job():
        try:
            scheduler.send_job_emails_from_db(
                sender_email=sender,
                master_user_id=mu,
                store_id=store,
                job_id=job_id,
                job_type="custom",
                subject=subject,
                content=content,
                html_content=html_content,
                attachments=resolved_attachments,
                min_interval=min_interval,
                max_interval=max_interval,
            )
        except Exception:
            pass

    return jsonify({"success": True, "job_id": job_id, "recipients": added, "queued": True, "schedule_at": schedule_at})


@bp.route("/jobs/<string:job_id>", methods=["GET"])
def jobs_get(job_id: str):
    row = get_job(job_id)
    if not row:
        return jsonify({"success": False, "error": "not found"}), 404
    return jsonify({"success": True, "job": row, "recipients": len(list_job_recipients(job_id))})


@bp.route("/jobs/<string:job_id>/events", methods=["GET"])
def jobs_events(job_id: str):
    try:
        items = list_job_events(job_id)
        return jsonify({"success": True, "events": items})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/jobs/<string:job_id>/pause", methods=["POST"])
def jobs_pause(job_id: str):
    ok, resp = _require_api_key()
    if not ok:
        return resp
    try:
        set_job_status(job_id, "paused")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/jobs/<string:job_id>/resume", methods=["POST"])
def jobs_resume(job_id: str):
    ok, resp = _require_api_key()
    if not ok:
        return resp
    try:
        set_job_status(job_id, "running")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/jobs/<string:job_id>/cancel", methods=["POST"])
def jobs_cancel(job_id: str):
    ok, resp = _require_api_key()
    if not ok:
        return resp
    try:
        set_job_status(job_id, "stopped")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



@bp.route("/templates", methods=["POST"])
def templates_create():
    ok, resp = _require_api_key()
    if not ok:
        return resp
    data = request.get_json() or {}
    required = ["master_user_id", "store_id", "name", "language", "subject", "html_content"]
    for k in required:
        if k not in data:
            return jsonify({"success": False, "error": f"missing {k}"}), 400
    tpl_id = create_template(data)
    return jsonify({"success": True, "id": tpl_id})


@bp.route("/templates", methods=["GET"])
def templates_list():
    try:
        master_user_id = request.args.get("master_user_id", "")
        store_id = request.args.get("store_id", "")
        if not master_user_id or not store_id:
            return jsonify({"success": False, "error": "missing master_user_id/store_id"}), 400
        limit = int(request.args.get("limit", "50"))
        offset = int(request.args.get("offset", "0"))
        rows = list_templates(master_user_id, store_id, limit, offset)
        return jsonify({"success": True, "items": rows})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/templates/<int:tpl_id>", methods=["GET"])
def templates_get(tpl_id: int):
    try:
        master_user_id = request.args.get("master_user_id", "")
        store_id = request.args.get("store_id", "")
        row = get_template(master_user_id, store_id, tpl_id)
        if not row:
            return jsonify({"success": False, "error": "not found"}), 404
        return jsonify({"success": True, "item": row})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/templates/<int:tpl_id>", methods=["PUT", "PATCH"])
def templates_update(tpl_id: int):
    ok, resp = _require_api_key()
    if not ok:
        return resp
    data = request.get_json() or {}
    try:
        master_user_id = str(data.get("master_user_id", "") or "")
        store_id = str(data.get("store_id", "") or "")
        if not master_user_id or not store_id:
            return jsonify({"success": False, "error": "missing master_user_id/store_id"}), 400
        cnt = update_template(master_user_id, store_id, tpl_id, data)
        if cnt == 0:
            return jsonify({"success": False, "error": "not found or nothing changed"}), 404
        return jsonify({"success": True, "updated": cnt})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/templates/<int:tpl_id>", methods=["DELETE"])
def templates_delete(tpl_id: int):
    ok, resp = _require_api_key()
    if not ok:
        return resp
    try:
        master_user_id = request.args.get("master_user_id", "")
        store_id = request.args.get("store_id", "")
        cnt = delete_template(master_user_id, store_id, tpl_id)
        if cnt == 0:
            return jsonify({"success": False, "error": "not found"}), 404
        return jsonify({"success": True, "deleted": cnt})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/assets", methods=["POST"])
def assets_upload():
    ok, resp = _require_api_key()
    if not ok:
        return resp
    try:
        master_user_id = request.form.get("master_user_id", "")
        store_id = request.form.get("store_id", "")
        asset_type = request.form.get("asset_type")
        file_id = request.form.get("file_id")
        if asset_type not in ("image", "attachment"):
            return jsonify({"success": False, "error": "asset_type must be image|attachment"}), 400
        f = request.files.get("file")
        if not f:
            return jsonify({"success": False, "error": "missing file"}), 400
        files_root = get_config().get("FILES_ROOT")
        pics_dir, attach_dir = ensure_tenant_dirs(files_root, master_user_id, store_id)
        target_dir = pics_dir if asset_type == "image" else attach_dir
        filename = secure_filename(f.filename)
        if not filename:
            return jsonify({"success": False, "error": "invalid filename"}), 400
        os.makedirs(target_dir, exist_ok=True)
        save_path = os.path.join(target_dir, filename)
        f.save(save_path)
        # Write DB row via direct SQL to assets table (simple inline to reduce imports)
        from src.dao_mysql import _conn
        size_bytes = os.path.getsize(save_path)
        mime_type = (f.mimetype or "application/octet-stream")
        if not file_id:
            file_id = os.path.splitext(filename)[0]
        sql = (
            "INSERT INTO assets (master_user_id, store_id, asset_type, file_id, filename, mime_type, size_bytes, storage_path) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON DUPLICATE KEY UPDATE filename=VALUES(filename), mime_type=VALUES(mime_type), size_bytes=VALUES(size_bytes), storage_path=VALUES(storage_path), updated_at=CURRENT_TIMESTAMP(6)"
        )
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (master_user_id, store_id, asset_type, file_id, filename, mime_type, size_bytes, save_path))
        return jsonify({"success": True, "file_id": file_id, "path": save_path})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ===== Template files CRUD =====
@bp.route("/template_files", methods=["POST"])
def template_files_upload():
    ok, resp = _require_api_key()
    if not ok:
        return resp
    try:
        mu = request.form.get("master_user_id", "")
        store = request.form.get("store_id", "")
        language = (request.form.get("language") or "").strip()
        kind = (request.form.get("kind") or "").strip()  # subject|content
        f = request.files.get("file")
        if not (mu and store and language and kind and f):
            return jsonify({"success": False, "error": "missing fields"}), 400
        tfm = TemplateFileManager(get_config().get("FILES_ROOT"))
        if kind == "subject":
            tfm.save_subject(mu, store, language, f.read().decode("utf-8", errors="ignore"))
        elif kind == "content":
            tfm.save_content(mu, store, language, f.read().decode("utf-8", errors="ignore"))
        else:
            return jsonify({"success": False, "error": "kind must be subject|content"}), 400
        return jsonify({"success": True, "language": language, "kind": kind})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@bp.route("/template_files", methods=["GET"])
def template_files_list():
    try:
        mu = request.args.get("master_user_id", "")
        store = request.args.get("store_id", "")
        tfm = TemplateFileManager(get_config().get("FILES_ROOT"))
        items = tfm.list_languages(mu, store)
        return jsonify({"success": True, "items": items})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/template_files/<string:language>", methods=["GET"])
def template_files_get(language: str):
    try:
        mu = request.args.get("master_user_id", "")
        store = request.args.get("store_id", "")
        tfm = TemplateFileManager(get_config().get("FILES_ROOT"))
        data = tfm.read_language(mu, store, language)
        return jsonify({"success": True, "template": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@bp.route("/template_files/all", methods=["GET"])
def template_files_all():
    try:
        mu = request.args.get("master_user_id", "")
        store = request.args.get("store_id", "")
        include_empty = request.args.get("include_empty", "false").strip().lower() in ("1", "true", "yes")
        tfm = TemplateFileManager(get_config().get("FILES_ROOT"))
        langs = tfm.list_languages(mu, store)
        items = []
        for it in langs:
            lang = it.get("language")
            if not lang:
                continue
            data = tfm.read_language(mu, store, lang)
            if not include_empty and (data.get("subject") is None and data.get("content") is None):
                continue
            items.append(data)
        return jsonify({"success": True, "items": items})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/template_files/<string:language>", methods=["DELETE"])
def template_files_delete(language: str):
    ok, resp = _require_api_key()
    if not ok:
        return resp
    try:
        mu = request.args.get("master_user_id", "")
        store = request.args.get("store_id", "")
        kind = request.args.get("kind")  # subject|content|None
        tfm = TemplateFileManager()
        removed = tfm.delete_language(mu, store, language, kind)
        return jsonify({"success": True, "removed": removed})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ===== Assets list/get/delete =====
@bp.route("/assets", methods=["GET"])
def assets_list():
    try:
        mu = request.args.get("master_user_id", "")
        store = request.args.get("store_id", "")
        asset_type = request.args.get("asset_type")  # image|attachment|None
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        items = list_assets(mu, store, asset_type, limit, offset)
        return jsonify({"success": True, "items": items})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/assets/<int:asset_id>", methods=["GET"])
def assets_get(asset_id: int):
    try:
        mu = request.args.get("master_user_id", "")
        store = request.args.get("store_id", "")
        row = get_asset_by_id(asset_id, mu, store)
        if not row:
            return jsonify({"success": False, "error": "not found"}), 404
        return jsonify({"success": True, "item": row})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/assets/<int:asset_id>", methods=["DELETE"])
def assets_delete(asset_id: int):
    ok, resp = _require_api_key()
    if not ok:
        return resp
    try:
        mu = request.args.get("master_user_id", "")
        store = request.args.get("store_id", "")
        deleted = delete_asset(asset_id, mu, store)
        if deleted == 0:
            return jsonify({"success": False, "error": "not found"}), 404
        return jsonify({"success": True, "deleted": deleted})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ===== Tenant files list (pics/attachments) =====
@bp.route("/files/<string:kind>", methods=["GET"])
def files_list(kind: str):
    try:
        kind = (kind or "").strip().lower()
        if kind not in ("pics", "attachments"):
            return jsonify({"success": False, "error": "kind must be pics|attachments"}), 400
        mu = request.args.get("master_user_id", "")
        store = request.args.get("store_id", "")
        if not mu or not store:
            return jsonify({"success": False, "error": "missing master_user_id/store_id"}), 400
        files_root = get_config().get("FILES_ROOT")
        pics_dir, attach_dir = ensure_tenant_dirs(files_root, mu, store)
        base_dir = pics_dir if kind == "pics" else attach_dir
        items = []
        try:
            names = sorted(os.listdir(base_dir))
        except FileNotFoundError:
            names = []
        for name in names:
            full = os.path.join(base_dir, name)
            if not os.path.isfile(full):
                continue
            try:
                st = os.stat(full)
            except Exception:
                continue
            mime, _ = mimetypes.guess_type(full)
            items.append({
                "name": name,
                "size_bytes": st.st_size,
                "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(),
                "mime_type": mime or "application/octet-stream",
            })
        return jsonify({"success": True, "items": items, "kind": kind})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/files/<string:kind>/<path:filename>", methods=["GET"])
def file_get(kind: str, filename: str):
    try:
        kind = (kind or "").strip().lower()
        if kind not in ("pics", "attachments"):
            return jsonify({"success": False, "error": "kind must be pics|attachments"}), 400
        mu = request.args.get("master_user_id", "")
        store = request.args.get("store_id", "")
        download = (request.args.get("download", "0") or "").strip().lower() in ("1", "true", "yes")
        if not mu or not store:
            return jsonify({"success": False, "error": "missing master_user_id/store_id"}), 400
        files_root = get_config().get("FILES_ROOT")
        pics_dir, attach_dir = ensure_tenant_dirs(files_root, mu, store)
        base_dir = pics_dir if kind == "pics" else attach_dir
        safe_name = secure_filename(filename)
        if not safe_name:
            return jsonify({"success": False, "error": "invalid filename"}), 400
        full = os.path.join(base_dir, safe_name)
        if not os.path.isfile(full):
            return jsonify({"success": False, "error": "not found"}), 404
        mime, _ = mimetypes.guess_type(full)
        return send_file(full, mimetype=mime or "application/octet-stream", as_attachment=download, download_name=safe_name, conditional=True)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ===== Sender accounts list/delete =====
@bp.route("/senders", methods=["GET"])
def senders_list():
    try:
        mu = request.args.get("master_user_id", "")
        store = request.args.get("store_id", "")
        items = list_senders(mu, store)
        return jsonify({"success": True, "items": items})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/senders/<int:sender_id>", methods=["DELETE"])
def senders_delete(sender_id: int):
    ok, resp = _require_api_key()
    if not ok:
        return resp
    try:
        mu = request.args.get("master_user_id", "")
        store = request.args.get("store_id", "")
        deleted = delete_sender(sender_id, mu, store)
        if deleted == 0:
            return jsonify({"success": False, "error": "not found"}), 404
        return jsonify({"success": True, "deleted": deleted})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
