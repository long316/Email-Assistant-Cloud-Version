import os
from typing import Tuple


def ensure_tenant_dirs(base_dir: str, master_user_id: str, store_id: str) -> Tuple[str, str]:
    tenant_root = os.path.join(base_dir, f"tenant_{master_user_id}_{store_id}")
    pics_dir = os.path.join(tenant_root, "pics")
    attach_dir = os.path.join(tenant_root, "attachments")
    os.makedirs(pics_dir, exist_ok=True)
    os.makedirs(attach_dir, exist_ok=True)
    return pics_dir, attach_dir
