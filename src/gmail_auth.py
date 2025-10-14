"""
Gmail认证管理模块
负责管理多个邮箱的OAuth认证和凭据
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Gmail API所需权限：
# - gmail.send 用于发送邮件
# - gmail.readonly 用于读取基础资料（users.getProfile 等）
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

class GmailAuthManager:
    """Gmail认证管理器"""

    def __init__(self, credentials_file: str = "credentials.json"):
        """
        初始化认证管理器

        Args:
            credentials_file: Google OAuth客户端凭据文件路径
        """
        self.credentials_file = credentials_file
        self.logger = logging.getLogger(__name__)

        # 确保凭据文件存在
        if not os.path.exists(credentials_file):
            raise FileNotFoundError(f"凭据文件不存在: {credentials_file}")

    def get_token_file_path(self, email: str) -> str:
        """
        获取指定邮箱的token文件路径

        Args:
            email: 邮箱地址

        Returns:
            token文件路径
        """
        safe_email = email.replace("@", "_").replace(".", "_")
        return f"token_{safe_email}.json"

    def is_authenticated(self, email: str) -> bool:
        """
        检查指定邮箱是否已认证

        Args:
            email: 邮箱地址

        Returns:
            是否已认证
        """
        token_file = self.get_token_file_path(email)
        return os.path.exists(token_file)

    def authenticate(self, email: str) -> Optional[Credentials]:
        """
        对指定邮箱进行认证

        Args:
            email: 邮箱地址

        Returns:
            认证凭据，失败时返回None
        """
        token_file = self.get_token_file_path(email)
        creds = None

        # 检查是否存在已保存的token
        if os.path.exists(token_file):
            try:
                creds = Credentials.from_authorized_user_file(token_file, SCOPES)
                self.logger.info(f"加载已存在的认证文件: {token_file}")
            except Exception as e:
                self.logger.warning(f"加载认证文件失败: {e}")
                creds = None

        # 如果没有有效凭据，进行认证流程
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self.logger.info(f"刷新认证token成功: {email}")
                except Exception as e:
                    self.logger.error(f"刷新token失败: {e}")
                    creds = None

            if not creds:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES
                    )
                    # 提示用户进行认证
                    print(f"\n正在为邮箱 {email} 进行认证...")
                    print("将会打开浏览器进行OAuth认证，请按照指示完成认证。")

                    creds = flow.run_local_server(port=0)
                    self.logger.info(f"OAuth认证成功: {email}")
                except Exception as e:
                    self.logger.error(f"OAuth认证失败: {e}")
                    return None

            # 保存认证凭据
            if creds:
                try:
                    with open(token_file, "w", encoding="utf-8") as token:
                        token.write(creds.to_json())
                    self.logger.info(f"认证凭据已保存: {token_file}")
                except Exception as e:
                    self.logger.error(f"保存认证凭据失败: {e}")

        return creds

    # ===== Web OAuth Support =====
    def build_authorize_url(self, redirect_uri: str, state: str = ""):
        """构建 Web 授权 URL（服务端授权）。"""
        flow = Flow.from_client_secrets_file(
            self.credentials_file,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        auth_url, new_state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state or None,
        )
        return auth_url, (state or new_state)

    def exchange_code_for_token(self, code: str, redirect_uri: str):
        """用授权码换取令牌，并返回邮箱与凭据 JSON。"""
        flow = Flow.from_client_secrets_file(
            self.credentials_file,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        flow.fetch_token(code=code)
        creds = flow.credentials

        # 获取邮箱地址用于绑定
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        email_address = profile.get("emailAddress", "")

        return email_address, creds.to_json()

    def get_gmail_service(self, email: str):
        """
        获取指定邮箱的Gmail服务对象

        Args:
            email: 邮箱地址

        Returns:
            Gmail API服务对象，失败时返回None
        """
        creds = self.authenticate(email)
        if not creds:
            self.logger.error(f"获取认证凭据失败: {email}")
            return None

        try:
            service = build("gmail", "v1", credentials=creds)
            self.logger.info(f"Gmail服务初始化成功: {email}")
            return service
        except HttpError as e:
            self.logger.error(f"Gmail服务初始化失败: {e}")
            return None

    def validate_authentication(self, email: str) -> bool:
        """
        验证邮箱认证是否有效

        Args:
            email: 邮箱地址

        Returns:
            认证是否有效
        """
        service = self.get_gmail_service(email)
        if not service:
            return False

        try:
            # 尝试获取用户资料以验证认证
            profile = service.users().getProfile(userId="me").execute()
            actual_email = profile.get("emailAddress", "")

            if actual_email.lower() != email.lower():
                self.logger.warning(f"邮箱地址不匹配: 期望 {email}, 实际 {actual_email}")
                return False

            self.logger.info(f"认证验证成功: {email}")
            return True
        except HttpError as e:
            self.logger.error(f"认证验证失败: {e}")
            return False

    def remove_authentication(self, email: str) -> bool:
        """
        移除指定邮箱的认证

        Args:
            email: 邮箱地址

        Returns:
            是否成功移除
        """
        token_file = self.get_token_file_path(email)
        try:
            if os.path.exists(token_file):
                os.remove(token_file)
                self.logger.info(f"认证文件已删除: {token_file}")
            return True
        except Exception as e:
            self.logger.error(f"删除认证文件失败: {e}")
            return False
