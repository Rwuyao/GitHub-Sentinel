import requests
from typing import List, Dict
from .base import NotificationProvider
from core.config import Config

class SlackNotification(NotificationProvider):
    """Slack通知实现"""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.webhook_url = self.config.get("notifications.slack.webhook_url")
        self.message_prefix = self.config.get("notifications.slack.message_prefix", "GitHub 更新通知: ")
        self.include_links = self.config.get("notifications.slack.include_links", True)
        self.enabled = self.config.get("notifications.slack.enabled", False)
        # 验证必要配置
        if self.enabled and not self.webhook_url:
            self.logger.warning("Slack Webhook URL未配置，将禁用Slack通知")
            self.enabled = False
    
    def send(self, recipients: List[str], subject: str, content: str) -> bool:
        """发送Slack通知"""
        if not self.enabled:
            self.logger.debug("Slack通知已禁用，不发送通知")
            return False
            
        try:
            # Slack消息格式
            message = {
                "text": f"{self.message_prefix}{subject}\n\n{content}"
            }
            
            # 发送请求
            response = requests.post(
                self.webhook_url,
                json=message,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info("Slack通知发送成功")
                return True
            else:
                self.logger.error(f"Slack通知发送失败，状态码: {response.status_code}, 响应: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Slack通知发送异常: {str(e)}")
            return False

    def is_enabled(self) -> bool:
        """检查当前通知方式是否启用"""
        return self.enabled
