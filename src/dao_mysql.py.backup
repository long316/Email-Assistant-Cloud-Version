import json
import os
import pymysql
from typing import Any, Dict, List, Optional, Tuple
import uuid

from src.config import get_config


def _conn():
    cfg = get_config()
    dsn = cfg.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL not configured")
    # Very small DSN parser for mysql+pymysql://user:pass@host:port/db?charset=utf8mb4
    # We will rely on PyMySQL.connect accepting those components extracted via urlsplit
    from urllib.parse import urlsplit, parse_qs
    u = urlsplit(dsn)
    if not u.scheme.startswith("mysql"):
        raise RuntimeError("DATABASE_URL must be mysql+pymysql://")
    params = parse_qs(u.query)
    return pymysql.connect(
        host=u.hostname or "127.0.0.1",
        user=u.username,
        password=u.password,
        database=(u.path or "/").lstrip("/") or None,
        port=u.port or 3306,
        charset=(params.get("charset", ["utf8mb4"])[0]),
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )


# Sender accounts
def upsert_sender_account(master_user_id: str, store_id: str, email: str, token_json: Dict[str, Any]) -> None:
    sql = (
        "INSERT INTO sender_accounts (master_user_id, store_id, email, provider, token_json)"
        " VALUES (%s,%s,%s,'gmail',%s)"
        " ON DUPLICATE KEY UPDATE token_json=VALUES(token_json), updated_at=CURRENT_TIMESTAMP(6)"
    )
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (master_user_id, store_id, email, json.dumps(token_json)))


# Templates minimal CRUD
def create_template(data: Dict[str, Any]) -> int:
    sql = (
        "INSERT INTO templates (master_user_id, store_id, name, language, subject, html_content, text_content, version, is_active)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    args = (
        data["master_user_id"],
        data["store_id"],
        data["name"],
        data["language"],
        data["subject"],
        data["html_content"],
        data.get("text_content"),
        int(data.get("version", 1)),
        1 if data.get("is_active", True) else 0,
    )
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.lastrowid


def get_template(master_user_id: str, store_id: str, template_id: int) -> Optional[Dict[str, Any]]:
    sql = "SELECT * FROM templates WHERE id=%s AND master_user_id=%s AND store_id=%s"
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (template_id, master_user_id, store_id))
            return cur.fetchone()


def list_templates(master_user_id: str, store_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM templates WHERE master_user_id=%s AND store_id=%s ORDER BY id DESC LIMIT %s OFFSET %s"
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (master_user_id, store_id, limit, offset))
            return cur.fetchall()


def update_template(master_user_id: str, store_id: str, template_id: int, updates: Dict[str, Any]) -> int:
    fields = []
    args: List[Any] = []
    for key in ("name", "language", "subject", "html_content", "text_content", "version", "is_active"):
        if key in updates:
            fields.append(f"{key}=%s")
            val = updates[key]
            if key == "is_active":
                val = 1 if bool(val) else 0
            args.append(val)
    if not fields:
        return 0
    sql = f"UPDATE templates SET {', '.join(fields)}, updated_at=CURRENT_TIMESTAMP(6) WHERE id=%s AND master_user_id=%s AND store_id=%s"
    args.extend([template_id, master_user_id, store_id])
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.rowcount


def delete_template(master_user_id: str, store_id: str, template_id: int) -> int:
    sql = "DELETE FROM templates WHERE id=%s AND master_user_id=%s AND store_id=%s"
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (template_id, master_user_id, store_id))
            return cur.rowcount


# Assets helpers
def resolve_attachment_paths(master_user_id: str, store_id: str, file_ids: List[str]) -> List[str]:
    """Map assets.file_id to relative paths under files/ for AttachmentManager.
    Returns list of relative file_ids like 'tenant_{mu}_{store}/attachments/filename.ext'.
    Falls back to original id if not found in DB.
    """
    if not file_ids:
        return []
    sql = (
        "SELECT file_id, filename FROM assets WHERE master_user_id=%s AND store_id=%s AND asset_type='attachment'"
        " AND file_id IN (%s)"
    )
    ph = ",".join(["%s"] * len(file_ids))
    sql = sql % ("%s", "%s", ph)
    mapping: Dict[str, str] = {}
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (master_user_id, store_id, *file_ids))
            for row in cur.fetchall():
                rel = f"tenant_{master_user_id}_{store_id}/attachments/{row['filename']}"
                mapping[row["file_id"]] = rel
    return [mapping.get(fid, fid) for fid in file_ids]


# Jobs and recipients
def create_job(
    master_user_id: str,
    store_id: str,
    job_type: str,
    sender_email: str,
    template_id: Optional[int],
    subject: Optional[str],
    content: Optional[str],
    html_content: Optional[str],
    min_interval: int,
    max_interval: int,
    webhook_url: Optional[str] = None,
    schedule_at: Optional[str] = None,
) -> str:
    job_id = str(uuid.uuid4())
    sql = (
        "INSERT INTO jobs (id, master_user_id, store_id, type, sender_email, template_id, subject, content, html_content,"
        " min_interval, max_interval, schedule_at, total, success_count, failure_count, status, webhook_url)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,0,0,'queued',%s)"
    )
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    job_id,
                    master_user_id,
                    store_id,
                    job_type,
                    sender_email,
                    template_id,
                    subject,
                    content,
                    html_content,
                    min_interval,
                    max_interval,
                    schedule_at,
                    webhook_url,
                ),
            )
    return job_id


def add_job_recipients(job_id: str, recipients: List[Dict[str, Any]]) -> int:
    if not recipients:
        return 0
    sql = (
        "INSERT INTO job_recipients (job_id, to_email, language, variables, status)"
        " VALUES (%s,%s,%s,%s,'pending')"
    )
    count = 0
    with _conn() as conn:
        with conn.cursor() as cur:
            for r in recipients:
                cur.execute(
                    sql,
                    (
                        job_id,
                        r.get("to_email"),
                        r.get("language"),
                        json.dumps(r.get("variables", {})),
                    ),
                )
                count += 1
            cur.execute("UPDATE jobs SET total = total + %s WHERE id=%s", (count, job_id))
    return count


def list_job_recipients(job_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    if status:
        sql = "SELECT * FROM job_recipients WHERE job_id=%s AND status=%s ORDER BY id"
        args = (job_id, status)
    else:
        sql = "SELECT * FROM job_recipients WHERE job_id=%s ORDER BY id"
        args = (job_id,)
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM jobs WHERE id=%s", (job_id,))
            return cur.fetchone()


def get_next_queued_job() -> Optional[Dict[str, Any]]:
    sql = (
        "SELECT * FROM jobs WHERE status='queued' AND schedule_at IS NOT NULL AND schedule_at<=NOW()"
        " ORDER BY schedule_at, created_at LIMIT 1"
    )
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchone()


def claim_job(job_id: str) -> bool:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE jobs SET status='running', started_at=NOW() WHERE id=%s AND status='queued'",
                (job_id,),
            )
            return cur.rowcount == 1


def list_job_events(job_id: str) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM job_events WHERE job_id=%s ORDER BY created_at"
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (job_id,))
            return cur.fetchall()


def insert_job_event(job_id: str, event_type: str, payload: Optional[Dict[str, Any]] = None) -> None:
    import json as _json
    sql = "INSERT INTO job_events (job_id, event_type, payload) VALUES (%s,%s,%s)"
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (job_id, event_type, _json.dumps(payload or {})))


def get_job_status(job_id: str) -> Optional[str]:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM jobs WHERE id=%s", (job_id,))
            row = cur.fetchone()
            return row["status"] if row else None


# ===== Assets =====
def list_assets(master_user_id: str, store_id: str, asset_type: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    if asset_type:
        sql = (
            "SELECT * FROM assets WHERE master_user_id=%s AND store_id=%s AND asset_type=%s"
            " ORDER BY id DESC LIMIT %s OFFSET %s"
        )
        args = (master_user_id, store_id, asset_type, limit, offset)
    else:
        sql = (
            "SELECT * FROM assets WHERE master_user_id=%s AND store_id=%s"
            " ORDER BY id DESC LIMIT %s OFFSET %s"
        )
        args = (master_user_id, store_id, limit, offset)
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()


def get_asset_by_id(asset_id: int, master_user_id: str, store_id: str) -> Optional[Dict[str, Any]]:
    sql = "SELECT * FROM assets WHERE id=%s AND master_user_id=%s AND store_id=%s"
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (asset_id, master_user_id, store_id))
            return cur.fetchone()


def delete_asset(asset_id: int, master_user_id: str, store_id: str) -> int:
    sql = "DELETE FROM assets WHERE id=%s AND master_user_id=%s AND store_id=%s"
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (asset_id, master_user_id, store_id))
            return cur.rowcount


def get_asset_by_file_id(master_user_id: str, store_id: str, asset_type: str, file_id: str) -> Optional[Dict[str, Any]]:
    sql = (
        "SELECT * FROM assets WHERE master_user_id=%s AND store_id=%s AND asset_type=%s AND file_id=%s"
        " ORDER BY id DESC LIMIT 1"
    )
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (master_user_id, store_id, asset_type, file_id))
            return cur.fetchone()


# ===== Sender accounts =====
def list_senders(master_user_id: str, store_id: str) -> List[Dict[str, Any]]:
    sql = (
        "SELECT id, master_user_id, store_id, email, provider, status, created_at, updated_at"
        " FROM sender_accounts WHERE master_user_id=%s AND store_id=%s ORDER BY id DESC"
    )
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (master_user_id, store_id))
            return cur.fetchall()


def delete_sender(sender_id: int, master_user_id: str, store_id: str) -> int:
    sql = "DELETE FROM sender_accounts WHERE id=%s AND master_user_id=%s AND store_id=%s"
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (sender_id, master_user_id, store_id))
            return cur.rowcount


def update_job_counts(job_id: str, success_inc: int = 0, failure_inc: int = 0):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE jobs SET success_count=success_count+%s, failure_count=failure_count+%s WHERE id=%s",
                (success_inc, failure_inc, job_id),
            )


def set_job_status(job_id: str, status: str):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE jobs SET status=%s WHERE id=%s", (status, job_id))


def set_recipient_status(job_recipient_id: int, status: str, error: Optional[str] = None, provider_message_id: Optional[str] = None):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE job_recipients SET status=%s, error=%s, provider_message_id=%s, updated_at=CURRENT_TIMESTAMP(6) WHERE id=%s",
                (status, error, provider_message_id, job_recipient_id),
            )
