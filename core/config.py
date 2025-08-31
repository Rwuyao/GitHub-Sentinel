import os
import json
import yaml
import logging
from typing import Dict, Any, Optional

class Config:
    """配置管理类，支持从环境变量和配置文件加载配置"""
    
    def __init__(self):
        """初始化配置对象"""
        self._config: Dict[str, Any] = {
            # 默认配置
            "github_token": None,
            "scheduler": {
                "daily_time": "09:00",  # 每日检查时间
                "weekly_day": "monday",  # 每周检查日
                "weekly_time": "09:00"   # 每周检查时间
            },
            "subscription": {
                "storage_type": "json",  # 存储类型: json 或 memory
                "storage_path": "subscriptions.json"  # JSON存储路径
            },
            "notifications": {
                "email": {
                    "enabled": False,
                    "smtp_server": "smtp.example.com",
                    "smtp_port": 587,
                    "smtp_username": None,
                    "smtp_password": None,
                    "from_address": "github-sentinel@example.com"
                },
                "slack": {
                    "enabled": False,
                    "webhook_url": None
                }
            },
            "logging": {
                "level": "INFO",
                "file": None  # 日志文件路径，None表示仅控制台输出
            }
        }
        
        self.logger = logging.getLogger(__name__)

    @classmethod
    def from_env(cls) -> 'Config':
        """从环境变量加载配置"""
        config = cls()
        config.load_from_env()
        return config

    @classmethod
    def from_file(cls, file_path: str) -> 'Config':
        """从配置文件加载配置"""
        config = cls()
        config.load_from_file(file_path)
        config.load_from_env()  # 环境变量配置优先级高于文件
        return config

    def load_from_file(self, file_path: str) -> None:
        """从文件加载配置（支持YAML和JSON）"""
        if not os.path.exists(file_path):
            self.logger.warning(f"配置文件 {file_path} 不存在，将使用默认配置")
            return

        try:
            with open(file_path, 'r') as f:
                # 根据文件扩展名判断格式
                if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    file_config = yaml.safe_load(f)
                elif file_path.endswith('.json'):
                    file_config = json.load(f)
                else:
                    self.logger.error(f"不支持的配置文件格式: {file_path}")
                    return

            # 合并配置（文件配置覆盖默认配置）
            self._merge_config(self._config, file_config)
            self.logger.info(f"已从 {file_path} 加载配置")
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {str(e)}")

    def load_from_env(self) -> None:
        """从环境变量加载配置"""
        env_mappings = {
            # 环境变量名 -> 配置路径
            "GITHUB_TOKEN": "github_token",
            "SCHEDULER_DAILY_TIME": "scheduler.daily_time",
            "SCHEDULER_WEEKLY_DAY": "scheduler.weekly_day",
            "SCHEDULER_WEEKLY_TIME": "scheduler.weekly_time",
            "SUBSCRIPTION_STORAGE_TYPE": "subscription.storage_type",
            "SUBSCRIPTION_STORAGE_PATH": "subscription.storage_path",
            "LOGGING_LEVEL": "logging.level",
            "LOGGING_FILE": "logging.file",
            # 邮件配置
            "EMAIL_ENABLED": "notifications.email.enabled",
            "SMTP_SERVER": "notifications.email.smtp_server",
            "SMTP_PORT": "notifications.email.smtp_port",
            "SMTP_USERNAME": "notifications.email.smtp_username",
            "SMTP_PASSWORD": "notifications.email.smtp_password",
            "EMAIL_FROM": "notifications.email.from_address",
            # Slack配置
            "SLACK_ENABLED": "notifications.slack.enabled",
            "SLACK_WEBHOOK_URL": "notifications.slack.webhook_url"
        }

        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_config_value(config_path, value)

        self.logger.info("已从环境变量加载配置")

    def _merge_config(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """递归合并配置字典"""
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._merge_config(target[key], value)
            else:
                target[key] = value

    def _set_config_value(self, path: str, value: str) -> None:
        """设置嵌套配置值"""
        parts = path.split('.')
        current = self._config

        for i, part in enumerate(parts[:-1]):
            if part not in current:
                self.logger.warning(f"配置路径不存在: {'.'.join(parts[:i+1])}")
                return
            current = current[part]

        # 尝试转换值类型
        last_part = parts[-1]
        original_value = current.get(last_part)
        
        if original_value is not None:
            # 根据原始值类型转换
            if isinstance(original_value, bool):
                value = value.lower() in ('true', '1', 'yes')
            elif isinstance(original_value, int):
                try:
                    value = int(value)
                except ValueError:
                    self.logger.warning(f"无法将 {value} 转换为整数，使用原始值")
                    return

        current[last_part] = value
        self.logger.debug(f"设置配置 {path} = {value}")

    def get(self, path: str, default: Any = None) -> Any:
        """获取配置值"""
        parts = path.split('.')
        current = self._config

        for part in parts:
            if part not in current:
                return default
            current = current[part]

        return current

    def set(self, path: str, value: Any) -> None:
        """设置配置值"""
        parts = path.split('.')
        current = self._config

        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        return self._config.copy()

    def save_to_file(self, file_path: str) -> None:
        """保存配置到文件"""
        try:
            with open(file_path, 'w') as f:
                if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    yaml.dump(self._config, f, sort_keys=False, default_flow_style=False)
                elif file_path.endswith('.json'):
                    json.dump(self._config, f, indent=2)
                else:
                    self.logger.error(f"不支持的配置文件格式: {file_path}")
                    return

            self.logger.info(f"配置已保存到 {file_path}")
        except Exception as e:
            self.logger.error(f"保存配置文件失败: {str(e)}")


# 配置示例生成函数
def generate_default_config(file_path: str = "config.yaml") -> None:
    """生成默认配置文件"""
    config = Config()
    config.save_to_file(file_path)
