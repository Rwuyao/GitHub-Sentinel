import requests
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

class GitHubClient:
    """GitHub API 客户端，修复了时区比较问题"""
    
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
    
    def get_latest_releases(self, repo_full_name: str, limit: int = 5, since: Optional[datetime] = None) -> List[Dict]:
        """获取仓库最新发布"""
        self.logger.info(f"获取仓库最新发布: {repo_full_name}")
        endpoint = f"/repos/{repo_full_name}/releases"
        
        params = {"per_page": limit}
        if since:
            # 转换为ISO格式的UTC时间字符串
            since_utc = self._ensure_utc_timezone(since)
            params["since"] = since_utc.isoformat()
        
        releases = self._make_request(endpoint, params) or []
        
        # 过滤预发布并确保时间正确
        filtered_releases = []
        for release in releases:
            if release.get("prerelease", False):
                continue
                
            # 如果指定了since，进一步过滤
            if since:
                published_at = self._parse_github_datetime(release.get("published_at"))
                if not published_at:
                    continue
                    
                since_utc = self._ensure_utc_timezone(since)
                if published_at >= since_utc:
                    filtered_releases.append(release)
            else:
                filtered_releases.append(release)
                
            if len(filtered_releases) >= limit:
                break
        
        return filtered_releases
    
    def get_recent_commits(self, repo_full_name: str, limit: int = 20, since: Optional[datetime] = None) -> List[Dict]:
        """获取仓库最近提交"""
        self.logger.info(f"获取仓库最近提交: {repo_full_name}")
        endpoint = f"/repos/{repo_full_name}/commits"
        
        params = {"per_page": limit}
        if since:
            since_utc = self._ensure_utc_timezone(since)
            params["since"] = since_utc.isoformat()
        
        return self._make_request(endpoint, params) or []
    
    def get_recent_pull_requests(self, repo_full_name: str, limit: int = 20, since: Optional[datetime] = None) -> List[Dict]:
        """获取仓库最近的Pull Requests"""
        self.logger.info(f"获取仓库最近PR: {repo_full_name}")
        endpoint = f"/repos/{repo_full_name}/pulls"
        
        params = {
            "state": "all",
            "sort": "updated",
            "direction": "desc",
            "per_page": limit
        }
        
        prs = self._make_request(endpoint, params) or []
        filtered = []
        
        if since:
            since_utc = self._ensure_utc_timezone(since)
            
            for pr in prs:
                updated_at = self._parse_github_datetime(pr.get("updated_at"))
                if not updated_at:
                    continue
                    
                if updated_at >= since_utc and len(filtered) < limit:
                    filtered.append(pr)
                    
            return filtered
        
        return prs[:limit]
    
    def get_recent_issues(self, repo_full_name: str, limit: int = 20, since: Optional[datetime] = None) -> List[Dict]:
        """获取仓库最近的Issues"""
        self.logger.info(f"获取仓库最近Issues: {repo_full_name}")
        endpoint = f"/repos/{repo_full_name}/issues"
        
        params = {
            "state": "all",
            "sort": "updated",
            "direction": "desc",
            "per_page": limit
        }
        
        if since:
            since_utc = self._ensure_utc_timezone(since)
            params["since"] = since_utc.isoformat()
        
        issues = self._make_request(endpoint, params) or []
        
        # 过滤掉PR并确保时间正确
        filtered_issues = []
        for issue in issues:
            # 排除PR，只保留真正的Issue
            if "pull_request" in issue:
                continue
                
            # 如果指定了since，进一步过滤
            if since:
                updated_at = self._parse_github_datetime(issue.get("updated_at"))
                if not updated_at:
                    continue
                    
                since_utc = self._ensure_utc_timezone(since)
                if updated_at >= since_utc:
                    filtered_issues.append(issue)
            else:
                filtered_issues.append(issue)
                
            if len(filtered_issues) >= limit:
                break
        
        return filtered_issues
