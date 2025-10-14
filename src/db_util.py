import pymysql
from urllib.parse import urlparse, parse_qs

from src.config import get_config


def _parse_mysql_url(url: str):
    parsed = urlparse(url)
    if parsed.scheme.split('+')[0] != 'mysql':
        raise ValueError('DATABASE_URL must be a mysql URL')
    user = parsed.username
    password = parsed.password
    host = parsed.hostname or '127.0.0.1'
    port = parsed.port or 3306
    db = (parsed.path or '/').lstrip('/') or None
    qs = parse_qs(parsed.query)
    charset = (qs.get('charset', ['utf8mb4'])[0])
    return {
        'user': user,
        'password': password,
        'host': host,
        'port': int(port),
        'database': db,
        'charset': charset,
    }


def db_ping():
    cfg = get_config()
    dsn = cfg.get('DATABASE_URL')
    if not dsn:
        return {"success": False, "error": "DATABASE_URL not configured"}
    params = _parse_mysql_url(dsn)
    try:
        conn = pymysql.connect(
            host=params['host'],
            user=params['user'],
            password=params['password'],
            database=params['database'],
            port=params['port'],
            charset=params['charset'],
            connect_timeout=5,
            read_timeout=5,
            write_timeout=5,
            autocommit=True,
        )
        with conn.cursor() as cur:
            cur.execute('SELECT 1')
            row = cur.fetchone()
        conn.close()
        return {"success": True, "result": row[0] if row else None}
    except Exception as e:
        return {"success": False, "error": str(e)}

