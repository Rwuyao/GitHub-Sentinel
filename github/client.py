import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class GitHubClient:
    """GitHub API客户端，用于获取仓库信息和更新"""
    
    def __init__(self, config):
        self.api_url = config.github_api_url
        self.headers = {
            "Authorization": f"token {config.github_api_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.logger = logging.getLogger(__name__)
        
        # 缓存最近的请求结果以减少API调用
        self.cache = {}
        self.cache_ttl = 300  # 缓存有效期5分钟
    
    def _api_request(self, endpoint: str, params: Dict = None) -> Dict:
        """发送GitHub API请求"""
        url = f"{self.api_url}{endpoint}"
        cache_key = f"{url}?{params}" if params else url
        
        # 检查缓存
        now = datetime.now().timestamp()
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if now - cache_entry['timestamp'] < self.cache_ttl:
                self.logger.debug(f"Using cached data for {url}")
                return cache_entry['data']
        
        # 发送请求
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            # 更新缓存
            self.cache[cache_key] = {
                'timestamp': now,
                'data': response.json()
            }
            
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"GitHub API request failed: {str(e)}")
            raise
    
    def get_recent_updates(self, repo_full_name: str, since: Optional[datetime] = None) -> List[Dict]:
        """获取仓库的最近更新
        
        Args:
            repo_full_name: 仓库全名，格式为"owner/repo"
            since: 从该时间点开始的更新，None表示获取最近24小时的更新
        
        Returns:
            包含更新信息的字典列表
        """
        self.logger.info(f"Fetching recent updates for {repo_full_name}")
        
        if not since:
            since = datetime.now() - timedelta(days=1)
        
        # 格式化为ISO 8601
        since_str = since.isoformat() + "Z"
        
        # 获取提交
        commits = self._api_request(
            f"/repos/{repo_full_name}/commits",
            params={"since": since_str}
        )
        
        # 获取issues
        issues = self._api_request(
            f"/repos/{repo_full_name}/issues",
            params={"since": since_str, "state": "all"}
        )
        
        # 获取pull requests
        pulls = self._api_request(
            f"/repos/{repo_full_name}/pulls",
            params={"since": since_str, "state": "all"}
        )
        
        return {
            "commits": commits,
            "issues": issues,
            "pull_requests": pulls,
            "since": since
        }
    
    def get_weekly_updates(self, repo_full_name: str) -> Dict:
        """获取仓库过去一周的更新"""
        one_week_ago = datetime.now() - timedelta(weeks=1)
        return self.get_recent_updates(repo_full_name, since=one_week_ago)
    
    def get_repo_info(self, repo_full_name: str) -> Dict:
        """获取仓库基本信息"""
        self.logger.info(f"Fetching info for {repo_full_name}")
        return self._api_request(f"/repos/{repo_full_name}")
    
    def validate_repo(self, repo_full_name: str) -> bool:
        """验证仓库是否存在"""
        try:
            self.get_repo_info(repo_full_name)
            return True
        except requests.exceptions.RequestException:
            return False
