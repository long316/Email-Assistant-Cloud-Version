import json
import os
from typing import Optional


class TokenStore:
    

    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir

    def _safe_email(self, email: str) -> str:
        return email.replace("@", "_").replace(".", "_")

    def get_token_file_path(self, email: str) -> str:
        return os.path.join(self.base_dir, f"token_{self._safe_email(email)}.json")

    def save(self, email: str, creds_json: str):
        path = self.get_token_file_path(email)
        with open(path, "w", encoding="utf-8") as f:
            f.write(creds_json)

    def load(self, email: str) -> Optional[str]:
        path = self.get_token_file_path(email)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def delete(self, email: str) -> bool:
        path = self.get_token_file_path(email)
        if os.path.exists(path):
            os.remove(path)
        return True

