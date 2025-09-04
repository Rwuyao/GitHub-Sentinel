import json
import os
import logging
from typing import List, Optional
from .models import Subscription
from core.config import Config

class SubscriptionStorage:
    """订阅数据持久化存储（JSON文件）"""
    def __init__(self, config: Config):
        self.logger = logging.getLogger(__name__)
        self.storage_path = config.get("subscription.storage_path", "data/subscriptions.json")
        self._init_storage_dir()

    def _init_storage_dir(self):
        """初始化存储目录"""
        dir_path = os.path.dirname(self.storage_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        # 初始化空文件
        if not os.path.exists(self.storage_path):
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False)

    def load_subscriptions(self) -> List[Subscription]:
        """加载所有订阅"""
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [Subscription.from_dict(item) for item in data]
        except Exception as e:
            self.logger.error(f"加载订阅失败: {str(e)}")
            return []

    def save_subscriptions(self, subscriptions: List[Subscription]):
        """保存所有订阅"""
        try:
            data = [sub.to_dict() for sub in subscriptions]
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存订阅失败: {str(e)}")

    def get_next_id(self) -> int:
        """获取下一个可用的订阅ID"""
        subs = self.load_subscriptions()
        return max([sub.id for sub in subs], default=0) + 1