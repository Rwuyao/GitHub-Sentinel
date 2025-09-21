import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate
from typing import List, Dict
from .base import NotificationProvider
from core.config import Config

class EmailNotification(NotificationProvider):
    """邮件通知实现"""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.smtp_server = config.get("notifications.email.smtp_server")
        self.smtp_port = config.get("notifications.email.smtp_port", 587)
        self.smtp_username = config.get("notifications.email.smtp_username")
        self.smtp_password = config.get("notifications.email.smtp_password")
        self.from_address = config.get("notifications.email.from_address", self.smtp_username)
        self.use_tls = config.get("notifications.email.smtp_use_tls", True)
        self.subject_prefix = config.get("notifications.email.subject_prefix", "[GitHub Sentinel] ")
        self.content_type = config.get("notifications.email.content_type", "plain")  # plain 或 html
        self.enabled = config.get("notifications.email.enabled", False)

    def send(self, recipients: List[str], subject: str, content: str) -> bool:
        """发送邮件通知"""
        if not self.enabled:
            self.logger.debug("邮件通知已禁用，不发送通知")
            return False
            
        if not recipients:
            self.logger.warning("没有收件人，不发送邮件")
            return False
            
        try:
            # 构建邮件内容
            msg = MIMEText(content, self.content_type, "utf-8")
            msg["Subject"] = f"{self.subject_prefix}{subject}"
            msg["From"] = self.from_address
            msg["To"] = ", ".join(recipients)
            msg["Date"] = formatdate()
            
            # 发送邮件
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
                
            self.logger.info(f"已向 {len(recipients)} 个收件人发送邮件通知")
            return True
            
        except Exception as e:
            self.logger.error(f"邮件发送失败: {str(e)}")
            return False

    def is_enabled(self) -> bool:
        """检查当前通知方式是否启用"""
        return self.enabled
