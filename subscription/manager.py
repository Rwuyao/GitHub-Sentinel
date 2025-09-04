import logging
import json
import os
from datetime import datetime
from typing import List, Optional, Tuple
from .models import Subscription
from .storage import SubscriptionStorage
from github.client import GitHubClient
from core.config import Config

class SubscriptionManager:
    """订阅管理核心类（新增/删除/查看/处理）"""
    def __init__(self, config: Config, github_client: GitHubClient):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.github_client = github_client
        self.storage = SubscriptionStorage(config)
        # 默认时间范围：每日处理前一天数据
        self.default_time_range = {
            "start": lambda: datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1),
            "end": lambda: datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        }

    def add_subscription(self, repo_full_name: str, subscribers: List[str], 
                        time_range_type: str = "daily", 
                        custom_time_start: Optional[datetime] = None,
                        custom_time_end: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        新增订阅
        返回：(是否成功, 提示信息)
        """
        # 验证仓库是否存在
        repo_info = self.github_client.get_repo_info(repo_full_name)
        if not repo_info:
            return False, f"仓库 {repo_full_name} 不存在或无权限访问"
        
        # 加载现有订阅
        subs = self.storage.load_subscriptions()
        # 检查重复订阅
        if any(sub.repo_full_name == repo_full_name for sub in subs):
            return False, f"仓库 {repo_full_name} 已在订阅列表中"
        
        # 创建新订阅
        new_sub = Subscription(
            id=self.storage.get_next_id(),
            repo_full_name=repo_full_name,
            subscribers=subscribers,
            created_at=datetime.now(),
            time_range_type=time_range_type,
            custom_time_start=custom_time_start,
            custom_time_end=custom_time_end
        )
        
        # 保存
        subs.append(new_sub)
        self.storage.save_subscriptions(subs)
        return True, f"订阅成功！订阅ID: {new_sub.id}（仓库: {repo_full_name}）"

    def delete_subscription(self, sub_id: int) -> Tuple[bool, str]:
        """删除订阅（通过ID）"""
        subs = self.storage.load_subscriptions()
        original_count = len(subs)
        subs = [sub for sub in subs if sub.id != sub_id]
        
        if len(subs) == original_count:
            return False, f"未找到订阅ID: {sub_id}"
        
        self.storage.save_subscriptions(subs)
        return True, f"订阅ID {sub_id} 已删除"

    def list_subscriptions(self, repo_full_name: Optional[str] = None) -> List[Subscription]:
        """查看订阅（可选过滤仓库名）"""
        subs = self.storage.load_subscriptions()
        if repo_full_name:
            subs = [sub for sub in subs if sub.repo_full_name == repo_full_name]
        # 按ID排序
        return sorted(subs, key=lambda x: x.id)

    def get_subscription_time_range(self, sub: Subscription) -> Tuple[datetime, datetime]:
        """获取订阅的时间范围（处理默认值和自定义）"""
        if sub.time_range_type == "custom" and sub.custom_time_start and sub.custom_time_end:
            return sub.custom_time_start, sub.custom_time_end
        # 默认：前一天（00:00 ~ 次日00:00）
        return self.default_time_range["start"](), self.default_time_range["end"]()

    def process_single_subscription(self, sub: Subscription, 
                                   custom_time_start: Optional[datetime] = None,
                                   custom_time_end: Optional[datetime] = None) -> Tuple[bool, str, Optional[str]]:
        """
        处理单个订阅（获取数据并导出原始文件）
        返回：(是否成功, 提示信息, 原始数据文件路径)
        """
        if not sub.enabled:
            return False, f"订阅ID {sub.id} 已禁用", None
        
        # 确定时间范围（自定义优先）
        start_time = custom_time_start or self.get_subscription_time_range(sub)[0]
        end_time = custom_time_end or self.get_subscription_time_range(sub)[1]
        self.logger.info(f"处理订阅ID {sub.id}（{sub.repo_full_name}），时间范围：{start_time} ~ {end_time}")

        # 1. 获取GitHub数据
        try:
            repo_info = self.github_client.get_repo_info(sub.repo_full_name)
            releases = self.github_client.get_latest_releases(
                sub.repo_full_name, since=start_time, limit=50
            )
            commits = self.github_client.get_recent_commits(
                sub.repo_full_name, since=start_time, limit=100
            )
            prs = self.github_client.get_recent_pull_requests(
                sub.repo_full_name, since=start_time, limit=50
            )
            issues = self.github_client.get_recent_issues(
                sub.repo_full_name, since=start_time, limit=50
            )
        except Exception as e:
            return False, f"获取数据失败: {str(e)}", None

        # 2. 导出原始数据（供报告模块读取）
        raw_data_dir = self.config.get("subscription.raw_data_dir", "data/raw_subscription_data")
        os.makedirs(raw_data_dir, exist_ok=True)
        
        # 文件名：{日期}_{订阅ID}_{仓库名}_raw.json
        date_str = start_time.strftime("%Y%m%d")
        safe_repo_name = sub.repo_full_name.replace("/", "_")
        raw_file_path = os.path.join(
            raw_data_dir,
            f"{date_str}_sub{sub.id}_{safe_repo_name}_raw.json"
        )

        # 3. 保存原始数据
        raw_data = {
            "subscription_id": sub.id,
            "repo_full_name": sub.repo_full_name,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "data": {
                "repo_info": repo_info,
                "releases": releases,
                "commits": commits,
                "pull_requests": prs,
                "issues": issues
            },
            "generated_at": datetime.now().isoformat()
        }

        try:
            with open(raw_file_path, "w", encoding="utf-8") as f:
                json.dump(raw_data, f, ensure_ascii=False, indent=2)
            # 更新订阅最后处理时间
            subs = self.storage.load_subscriptions()
            for s in subs:
                if s.id == sub.id:
                    s.last_processed_at = datetime.now()
                    break
            self.storage.save_subscriptions(subs)
            return True, f"订阅ID {sub.id} 处理成功", raw_file_path
        except Exception as e:
            return False, f"保存原始数据失败: {str(e)}", None

    def process_all_subscriptions(self, 
                                 custom_time_start: Optional[datetime] = None,
                                 custom_time_end: Optional[datetime] = None) -> List[Tuple[bool, str, Optional[str]]]:
        """处理所有启用的订阅"""
        subs = self.list_subscriptions()
        results = []
        for sub in subs:
            if sub.enabled:
                res = self.process_single_subscription(sub, custom_time_start, custom_time_end)
                results.append(res)
        return results