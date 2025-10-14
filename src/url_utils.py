from urllib.parse import urlparse


def is_return_url_allowed(url: str, allowed_hosts: str, allow_dev_localhost: bool = False) -> bool:
    try:
        if not url:
            return False
        parsed = urlparse(url)
        if parsed.scheme not in ("https", "http"):
            return False
        host = parsed.hostname or ""
        if allow_dev_localhost and host in ("localhost", "127.0.0.1"):
            return True
        if not allowed_hosts:
            return False
        whitelist = [h.strip() for h in allowed_hosts.split(",") if h.strip()]
        for item in whitelist:
            if item.startswith("."):
                # suffix match, e.g. .example.com
                if host.endswith(item):
                    return True
            else:
                if host == item:
                    return True
        return False
    except Exception:
        return False

