import threading
import time
from datetime import datetime
from typing import Optional

from src.dao_mysql import get_next_queued_job, claim_job
from src.gmail_auth import GmailAuthManager
from src.excel_processor import ExcelProcessor
from src.email_scheduler import EmailScheduler


class JobRunner:
    def __init__(self, interval_sec: int = 2):
        self.interval_sec = interval_sec
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self.gmail_auth_manager = GmailAuthManager()
        self.excel_processor = ExcelProcessor()
        self.scheduler = EmailScheduler(self.gmail_auth_manager, self.excel_processor)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.is_set():
            try:
                job = get_next_queued_job()
                if not job:
                    time.sleep(self.interval_sec)
                    continue
                job_id = job["id"]
                if not claim_job(job_id):
                    # Claimed by other runner
                    continue
                # dispatch job
                if job["type"] == "template":
                    self.scheduler.send_job_emails_from_db(
                        sender_email=job["sender_email"],
                        master_user_id=job["master_user_id"],
                        store_id=job["store_id"],
                        job_id=job_id,
                        job_type="template",
                        template_id=job.get("template_id"),
                        attachments=None,
                        min_interval=job.get("min_interval"),
                        max_interval=job.get("max_interval"),
                    )
                else:
                    self.scheduler.send_job_emails_from_db(
                        sender_email=job["sender_email"],
                        master_user_id=job["master_user_id"],
                        store_id=job["store_id"],
                        job_id=job_id,
                        job_type="custom",
                        subject=job.get("subject"),
                        content=job.get("content"),
                        html_content=job.get("html_content"),
                        attachments=None,
                        min_interval=job.get("min_interval"),
                        max_interval=job.get("max_interval"),
                    )
            except Exception:
                # swallow loop errors to keep runner alive
                time.sleep(self.interval_sec)

