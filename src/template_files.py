import os
import re
from typing import Dict, Optional, List, Tuple
from bs4 import BeautifulSoup


LANG_PATTERN = re.compile(r"^[a-z]{2,5}(-[A-Z]{2})?$")


class TemplateFileManager:
    """Manage per-tenant language templates stored as files.

    Layout under files/:
      files/tenant_{master_user_id}_{store_id}/templates/{lang}_subject.txt
      files/tenant_{master_user_id}_{store_id}/templates/{lang}_content.txt
    """

    def __init__(self, files_root: str = "files"):
        self.files_root = files_root

    # ----- paths -----
    def _tenant_dir(self, master_user_id: str, store_id: str) -> str:
        return os.path.join(self.files_root, f"tenant_{master_user_id}_{store_id}", "templates")

    def _paths(self, master_user_id: str, store_id: str, language: str) -> Tuple[str, str]:
        tdir = self._tenant_dir(master_user_id, store_id)
        os.makedirs(tdir, exist_ok=True)
        return (
            os.path.join(tdir, f"{language}_subject.txt"),
            os.path.join(tdir, f"{language}_content.txt"),
        )

    # ----- validation & sanitize -----
    def _validate_language(self, language: str):
        if not language or not LANG_PATTERN.match(language):
            raise ValueError("invalid language code")

    def _sanitize_html(self, html_text: str) -> str:
        # basic sanitation: strip script/style, event handlers and javascript: urls
        soup = BeautifulSoup(html_text or "", "html.parser")
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()
        for tag in soup(True):
            # remove on* attributes
            for attr in list(tag.attrs.keys()):
                if isinstance(attr, str) and attr.lower().startswith("on"):
                    del tag.attrs[attr]
            # clean href/src javascript:
            for a in ("href", "src"):
                if a in tag.attrs and isinstance(tag.attrs[a], str) and tag.attrs[a].strip().lower().startswith("javascript:"):
                    del tag.attrs[a]
        # return pretty-ish but minimal
        return str(soup)

    # ----- CRUD -----
    def save_subject(self, master_user_id: str, store_id: str, language: str, text: str) -> None:
        self._validate_language(language)
        subject_path, _ = self._paths(master_user_id, store_id, language)
        with open(subject_path, "w", encoding="utf-8") as f:
            f.write(text or "")

    def save_content(self, master_user_id: str, store_id: str, language: str, html_text: str) -> None:
        self._validate_language(language)
        _, content_path = self._paths(master_user_id, store_id, language)
        clean = self._sanitize_html(html_text or "")
        # very small validation: require at least one visible char
        if not clean or len(clean.strip()) == 0:
            raise ValueError("empty or invalid html content")
        with open(content_path, "w", encoding="utf-8") as f:
            f.write(clean)

    def read_language(self, master_user_id: str, store_id: str, language: str) -> Dict[str, Optional[str]]:
        self._validate_language(language)
        subject_path, content_path = self._paths(master_user_id, store_id, language)
        subject = None
        content = None
        if os.path.exists(subject_path):
            subject = open(subject_path, "r", encoding="utf-8").read()
        if os.path.exists(content_path):
            content = open(content_path, "r", encoding="utf-8").read()
        return {"language": language, "subject": subject, "content": content}

    def delete_language(self, master_user_id: str, store_id: str, language: str, kind: Optional[str] = None) -> int:
        self._validate_language(language)
        subject_path, content_path = self._paths(master_user_id, store_id, language)
        removed = 0
        def _rm(p):
            nonlocal removed
            if os.path.exists(p):
                os.remove(p)
                removed += 1
        if not kind or kind == "subject":
            _rm(subject_path)
        if not kind or kind == "content":
            _rm(content_path)
        return removed

    def list_languages(self, master_user_id: str, store_id: str) -> List[Dict[str, any]]:
        tdir = self._tenant_dir(master_user_id, store_id)
        if not os.path.exists(tdir):
            return []
        seen = {}
        for name in os.listdir(tdir):
            if name.endswith("_subject.txt"):
                lang = name[:-12]
                seen.setdefault(lang, {"language": lang, "has_subject": False, "has_content": False})
                seen[lang]["has_subject"] = True
            elif name.endswith("_content.txt"):
                lang = name[:-12]
                seen.setdefault(lang, {"language": lang, "has_subject": False, "has_content": False})
                seen[lang]["has_content"] = True
        return sorted(seen.values(), key=lambda x: x["language"]) 
