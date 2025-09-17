import requests
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

class GitHubClient:
    """GitHub API 客户端，支持PR的完整时间范围过滤"""
    
    def __init__(self, github_token: str, timeout: int = 10, retries: int = 3):
        self.logger = logging.getLogger(__name__)
        self.github_token = github_token
        self.timeout = timeout
        self.retries = retries
        self.base_url = "https://api.github.com"
        
        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Sentinel"
        }
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Any]:
        """发送API请求的内部方法，包含错误处理和重试逻辑"""
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        
        for attempt in range(self.retries):
            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=self.timeout
                )
                
                # 处理速率限制
                if response.status_code == 403 and "rate limit" in response.text.lower():
                    reset_time = datetime.fromtimestamp(
                        int(response.headers.get("X-RateLimit-Reset", 0)),
                        tz=timezone.utc
                    )
                    self.logger.warning(
                        f"GitHub API 速率限制已达。重置时间: {reset_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    )
                    return None
                
                response.raise_for_status()
                response.encoding = "utf-8"
                return response.json()
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"API请求失败（尝试 {attempt + 1}/{self.retries}）: {str(e)}")
                if attempt == self.retries - 1:
                    self.logger.error(f"API请求最终失败: {str(e)}")
                    return None
                import time
                time.sleep(2 **attempt)
        
        return None
    
    def _parse_github_datetime(self, datetime_str: str) -> Optional[datetime]:
        """解析GitHub API返回的datetime字符串为带UTC时区的datetime对象"""
        if not datetime_str:
            return None
        try:
            # 处理GitHub的"Z"时区标识（表示UTC）
            return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        except ValueError:
            self.logger.warning(f"无法解析时间字符串: {datetime_str}")
            return None
    
    def _ensure_utc_timezone(self, dt: datetime) -> datetime:
        """确保datetime对象带UTC时区信息"""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        # 转换为UTC时区
        return dt.astimezone(timezone.utc)
    
    def get_repo_info(self, repo_full_name: str) -> Optional[Dict]:
        """获取仓库基本信息"""
        self.logger.info(f"获取仓库信息: {repo_full_name}")
        endpoint = f"/repos/{repo_full_name}"
        return self._make_request(endpoint)
    
    def get_latest_releases(self, 
                           repo_full_name: str, 
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           limit: Optional[int] = None) -> List[Dict]:
        """
        获取仓库在指定时间范围内的发布
        
        参数:
            repo_full_name: 仓库全名 (owner/repo)
            limit: 最大返回数量，默认None表示不限制
            start_time: 开始时间（包含）
            end_time: 结束时间（包含）
            
        返回:
            符合条件的发布列表
        """
        effective_limit = limit if limit is not None else 30
        self.logger.info(f"获取仓库发布 {repo_full_name} (时间范围: {start_time} 至 {end_time}, 限制: {effective_limit})")
        
        endpoint = f"/repos/{repo_full_name}/releases"
        params = {"per_page": min(100, effective_limit)}
        
        if start_time:
            start_utc = self._ensure_utc_timezone(start_time)
            params["since"] = start_utc.isoformat()
        
        releases = self._make_request(endpoint, params) or []
        filtered_releases = []
        
        for release in releases:
            if release.get("prerelease", False):
                continue
                
            published_at = self._parse_github_datetime(release.get("published_at"))
            if not published_at:
                continue
                
            in_range = True
            if start_time:
                start_utc = self._ensure_utc_timezone(start_time)
                in_range = in_range and (published_at >= start_utc)
                
            if end_time:
                end_utc = self._ensure_utc_timezone(end_time)
                in_range = in_range and (published_at <= end_utc)
                
            if in_range:
                filtered_releases.append(release)
                if limit is not None and len(filtered_releases) >= limit:
                    break
        
        return filtered_releases
    
    def get_recent_pull_requests(self, 
                                repo_full_name: str, 
                                start_time: Optional[datetime] = None,  # 重命名since为start_time
                                end_time: Optional[datetime] = None,
                                limit: Optional[int] = None) -> List[Dict]:
        """
        获取仓库在指定时间范围内的Pull Requests
        
        参数:
            repo_full_name: 仓库全名 (owner/repo)
            limit: 最大返回数量，默认None表示不限制
            start_time: 开始时间（包含）
            end_time: 结束时间（包含）
            
        返回:
            符合条件的PR列表
        """
        effective_limit = limit if limit is not None else 50
        self.logger.info(f"获取仓库PR {repo_full_name} (时间范围: {start_time} 至 {end_time}, 限制: {effective_limit})")
        
        endpoint = f"/repos/{repo_full_name}/pulls"
        
        params = {
            "state": "all",
            "sort": "updated",
            "direction": "desc",
            "per_page": min(100, effective_limit * 2)  # 请求更多数据以便过滤
        }
        
        # API支持的since参数（开始时间）
        if start_time:
            start_utc = self._ensure_utc_timezone(start_time)
            params["since"] = start_utc.isoformat()
        
        prs = self._make_request(endpoint, params) or []
        filtered = []
        
        for pr in prs:
            updated_at = self._parse_github_datetime(pr.get("updated_at"))
            if not updated_at:
                continue
                
            # 检查是否在时间范围内
            in_range = True
            
            if start_time:
                start_utc = self._ensure_utc_timezone(start_time)
                in_range = in_range and (updated_at >= start_utc)
                
            if end_time:
                end_utc = self._ensure_utc_timezone(end_time)
                in_range = in_range and (updated_at <= end_utc)
                
            if in_range:
                filtered.append(pr)
                # 达到数量限制则停止
                if limit is not None and len(filtered) >= limit:
                    break
        
        return filtered
    
    def get_recent_issues(self, 
                         repo_full_name: str, 
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None,
                         limit: Optional[int] = None,) -> List[Dict]:
        """
        获取仓库在指定时间范围内的Issues
        
        参数:
            repo_full_name: 仓库全名 (owner/repo)
            limit: 最大返回数量，默认None表示不限制
            start_time: 开始时间（包含）
            end_time: 结束时间（包含）
            
        返回:
            符合条件的Issues列表
        """
        effective_limit = limit if limit is not None else 50
        self.logger.info(f"获取仓库Issues {repo_full_name} (时间范围: {start_time} 至 {end_time}, 限制: {effective_limit})")
        
        endpoint = f"/repos/{repo_full_name}/issues"
        
        params = {
            "state": "all",
            "sort": "updated",
            "direction": "desc",
            "per_page": min(100, effective_limit * 2)
        }
        
        if start_time:
            start_utc = self._ensure_utc_timezone(start_time)
            params["since"] = start_utc.isoformat()
        
        issues = self._make_request(endpoint, params) or []
        filtered_issues = []
        
        for issue in issues:
            if "pull_request" in issue:
                continue
                
            updated_at = self._parse_github_datetime(issue.get("updated_at"))
            if not updated_at:
                continue
                
            in_range = True
            if start_time:
                start_utc = self._ensure_utc_timezone(start_time)
                in_range = in_range and (updated_at >= start_utc)
                
            if end_time:
                end_utc = self._ensure_utc_timezone(end_time)
                in_range = in_range and (updated_at <= end_utc)
                
            if in_range:
                filtered_issues.append(issue)
                if limit is not None and len(filtered_issues) >= limit:
                    break
        
        return filtered_issues
