import logging
import os
import json
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple, Dict
from .models import Subscription
from .storage import SubscriptionStorage
from github.client import GitHubClient
from core.config import Config

class SubscriptionManager:
    """订阅管理核心类，支持新增、删除、查看和处理订阅"""
    
    def __init__(self, config: Config, github_client: GitHubClient):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.github_client = github_client
        self.storage = SubscriptionStorage(config)
        self.raw_data_dir = config.get("subscription.raw_data_dir", "data/raw_subscription_data")
        
        # 确保原始数据目录存在
        os.makedirs(self.raw_data_dir, exist_ok=True)
        
        # 默认时间范围：每日处理前一天数据（00:00 ~ 次日00:00）
        self.default_time_range = {
            "start": lambda: datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=1),
            "end": lambda: datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        }

    def add_subscription(self, 
                        repo_full_name: str, 
                        subscribers: List[str], 
                        time_range_type: str = "daily", 
                        custom_time_start: Optional[datetime] = None,
                        custom_time_end: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        新增订阅
        
        Args:
            repo_full_name: 仓库全名（格式：owner/repo）
            subscribers: 订阅者邮箱列表
            time_range_type: 时间范围类型（daily/custom）
            custom_time_start: 自定义时间起始（仅time_range_type=custom时有效）
            custom_time_end: 自定义时间结束（仅time_range_type=custom时有效）
            
        Returns:
            (是否成功, 提示信息)
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
        
        # 验证自定义时间范围
        if time_range_type == "custom":
            if not (custom_time_start and custom_time_end):
                return False, "自定义时间范围需要同时指定开始和结束时间"
            if custom_time_start >= custom_time_end:
                return False, "开始时间必须早于结束时间"
        
        # 创建新订阅
        new_sub = Subscription(
            id=self.storage.get_next_id(),
            repo_full_name=repo_full_name,
            subscribers=subscribers,
            created_at=datetime.now(),
            time_range_type=time_range_type,
            custom_time_start=custom_time_start,
            custom_time_end=custom_time_end,
            enabled=True
        )
        
        # 保存订阅
        subs.append(new_sub)
        self.storage.save_subscriptions(subs)
        return True, f"订阅成功！订阅ID: {new_sub.id}（仓库: {repo_full_name}）"

    def delete_subscription(self, sub_id: int) -> Tuple[bool, str]:
        """
        删除订阅
        
        Args:
            sub_id: 订阅ID
            
        Returns:
            (是否成功, 提示信息)
        """
        subs = self.storage.load_subscriptions()
        original_count = len(subs)
        
        # 过滤掉要删除的订阅
        subs = [sub for sub in subs if sub.id != sub_id]
        
        if len(subs) == original_count:
            return False, f"未找到订阅ID: {sub_id}"
        
        # 保存更新后的订阅列表
        self.storage.save_subscriptions(subs)
        return True, f"订阅ID {sub_id} 已成功删除"

    def list_subscriptions(self, repo_full_name: Optional[str] = None) -> List[Subscription]:
        """
        查看订阅列表
        
        Args:
            repo_full_name: 可选，指定仓库名过滤
            
        Returns:
            订阅列表（按ID排序）
        """
        subs = self.storage.load_subscriptions()
        
        # 按仓库名过滤
        if repo_full_name:
            subs = [sub for sub in subs if sub.repo_full_name == repo_full_name]
        
        # 按ID排序
        return sorted(subs, key=lambda x: x.id)

    def toggle_subscription_status(self, sub_id: int) -> Tuple[bool, str]:
        """
        启用/禁用订阅
        
        Args:
            sub_id: 订阅ID
            
        Returns:
            (是否成功, 提示信息)
        """
        subs = self.storage.load_subscriptions()
        for sub in subs:
            if sub.id == sub_id:
                sub.enabled = not sub.enabled
                self.storage.save_subscriptions(subs)
                status = "启用" if sub.enabled else "禁用"
                return True, f"订阅ID {sub_id} 已{status}"
        
        return False, f"未找到订阅ID: {sub_id}"

    def get_subscription_time_range(self, sub: Subscription) -> Tuple[datetime, datetime]:
        """
        获取订阅的时间范围
        
        Args:
            sub: 订阅对象
            
        Returns:
            (开始时间, 结束时间)
        """
        if sub.time_range_type == "custom" and sub.custom_time_start and sub.custom_time_end:
            return sub.custom_time_start, sub.custom_time_end
        
        # 默认返回前一天的时间范围
        return self.default_time_range["start"](), self.default_time_range["end"]()

    def _is_duplicate_raw_data(self, sub: Subscription, start_date: date) -> bool:
        """
        检查是否已存在该日期的原始数据（避免重复生成）
        
        Args:
            sub: 订阅对象
            start_date: 开始日期
            
        Returns:
            是否存在重复数据
        """
        # 生成标准文件名：{日期}_sub{ID}_{仓库名}_raw.json
        safe_repo_name = sub.repo_full_name.replace("/", "_")
        date_str = start_date.strftime("%Y%m%d")
        target_filename = f"{date_str}_sub{sub.id}_{safe_repo_name}_raw.json"
        
        # 检查文件是否存在
        if os.path.exists(os.path.join(self.raw_data_dir, target_filename)):
            self.logger.info(f"原始数据文件已存在：{target_filename}")
            return True
        return False

    def process_single_subscription(self, 
                                   sub: Subscription, 
                                   custom_time_start: Optional[datetime] = None,
                                   custom_time_end: Optional[datetime] = None,
                                   avoid_duplicate: bool = False) -> Tuple[bool, str, Optional[str]]:
        """
        处理单个订阅，获取数据并导出为原始文件（不含commits）
        
        Args:
            sub: 订阅对象
            custom_time_start: 自定义开始时间（覆盖订阅默认设置）
            custom_time_end: 自定义结束时间（覆盖订阅默认设置）
            avoid_duplicate: 是否避免重复生成
            
        Returns:
            (是否成功, 提示信息, 原始数据文件路径)
        """
        # 检查订阅是否启用
        if not sub.enabled:
            return False, f"订阅ID {sub.id} 已禁用，跳过处理", None
        
        # 确定时间范围
        default_start, default_end = self.get_subscription_time_range(sub)
        start_time = custom_time_start or default_start
        end_time = custom_time_end or default_end
        
        # 确保时间带有时区信息（与GitHub客户端保持一致）
        start_time = self.github_client._ensure_utc_timezone(start_time)
        end_time = self.github_client._ensure_utc_timezone(end_time)
        
        # 按日期去重检查
        start_date = start_time.date()
        if avoid_duplicate and self._is_duplicate_raw_data(sub, start_date):
            return False, f"订阅ID {sub.id} 已存在 {start_date} 的数据，跳过", None

        self.logger.info(
            f"处理订阅ID {sub.id}（{sub.repo_full_name}），时间范围："
            f"{start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}"
        )

        # 获取GitHub数据（不含commits）
        try:
            repo_info = self.github_client.get_repo_info(sub.repo_full_name)
            releases = self.github_client.get_latest_releases(
                sub.repo_full_name, 
                since=start_time, 
                limit=50
            )
            prs = self.github_client.get_recent_pull_requests(
                sub.repo_full_name, 
                since=start_time, 
                limit=50
            )
            issues = self.github_client.get_recent_issues(
                sub.repo_full_name, 
                since=start_time, 
                limit=50
            )
        except Exception as e:
            error_msg = f"获取数据失败: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, None

        # 准备原始数据
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
                "pull_requests": prs,
                "issues": issues  # 已移除commits相关内容
            },
            "generated_at": datetime.now().isoformat()
        }

        # 生成文件名并保存
        try:
            safe_repo_name = sub.repo_full_name.replace("/", "_")
            date_str = start_date.strftime("%Y%m%d")
            filename = f"{date_str}_sub{sub.id}_{safe_repo_name}_raw.json"
            raw_file_path = os.path.join(self.raw_data_dir, filename)

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
            error_msg = f"保存原始数据失败: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, None

    def process_all_subscriptions(self, 
                                 custom_time_start: Optional[datetime] = None,
                                 custom_time_end: Optional[datetime] = None,
                                 avoid_duplicate: bool = True) -> List[Tuple[bool, str, Optional[str]]]:
        """
        处理所有启用的订阅
        
        Args:
            custom_time_start: 自定义开始时间（覆盖所有订阅默认设置）
            custom_time_end: 自定义结束时间（覆盖所有订阅默认设置）
            avoid_duplicate: 是否避免重复生成
            
        Returns:
            处理结果列表，每个元素为(是否成功, 提示信息, 原始数据文件路径)
        """
        subs = self.list_subscriptions()
        results = []
        
        for sub in subs:
            if sub.enabled:  # 只处理启用的订阅
                res = self.process_single_subscription(
                    sub, 
                    custom_time_start=custom_time_start,
                    custom_time_end=custom_time_end,
                    avoid_duplicate=avoid_duplicate
                )
                results.append(res)
            else:
                results.append((False, f"订阅ID {sub.id} 已禁用，未处理", None))
        
        return results
    