import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate
from typing import List, Dict
from .base import NotificationProvider

class EmailNotification(NotificationProvider):
    """邮件通知实现"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.smtp_server = self.config.get("smtp_server")
        self.smtp_port = self.config.get("smtp_port", 587)
        self.smtp_username = self.config.get("smtp_username")
        self.smtp_password = self.config.get("smtp_password")
        self.from_address = self.config.get("from_address", self.smtp_username)
        self.use_tls = self.config.get("smtp_use_tls", True)
        self.subject_prefix = self.config.get("subject_prefix", "[GitHub Sentinel] ")
        self.content_type = self.config.get("content_type", "plain")  # plain 或 html
        
        # 验证必要配置
        if self.enabled:
            required_fields = ["smtp_server", "smtp_username", "smtp_password"]
            missing = [f for f in required_fields if not self.config.get(f)]
            if missing:
                self.logger.warning(f"邮件通知配置不完整，缺少: {', '.join(missing)}，将禁用邮件通知")
                self.enabled = False
    
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
