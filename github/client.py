import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

class GitHubClient:
    """GitHub API 客户端，用于获取仓库 仓库信息和动态"""
    
    def __init__(self, github_token: str, timeout: int = 10, retries: int = 3):
        self.logger = logging.getLogger(__name__)
        self.github_token = github_token
        self.timeout = timeout
        self.retries = retries  # 重试次数
        self.base_url = "https://api.github.com"
        
        # 请求头，包含认证信息
        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Sentinel"  # GitHub API 要求设置用户代理
        }
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Any]:
        """
        发送API请求的内部方法，包含错误处理和重试逻辑
        
        Args:
            endpoint: API端点路径，如 "/repos/langchain-ai/langchain"
            params: 请求参数
            
        Returns:
            API响应的JSON数据，或None（如果请求失败）
        """
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
                    reset_time = datetime.fromtimestamp(int(response.headers.get("X-RateLimit-Reset", 0)))
                    self.logger.warning(
                        f"GitHub API 速率限制已达。重置时间: {reset_time.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    return None
                
                response.raise_for_status()  # 抛出HTTP错误状态码
                response.encoding = "utf-8"  # 强制UTF-8编码处理
                return response.json()
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"API请求失败（尝试 {attempt + 1}/{self.retries}）: {str(e)}")
                if attempt == self.retries - 1:  # 最后一次尝试失败
                    self.logger.error(f"API请求最终失败: {str(e)}")
                    return None
                # 简单的指数退避重试
                import time
                time.sleep(2 **attempt)
        
        return None
    
    def get_repo_info(self, repo_full_name: str) -> Optional[Dict]:
        """
        获取仓库基本信息
        
        Args:
            repo_full_name: 仓库全名，格式为 "owner/repo"
            
        Returns:
            包含仓库信息的字典
        """
        self.logger.info(f"获取仓库信息: {repo_full_name}")
        endpoint = f"/repos/{repo_full_name}"
        return self._make_request(endpoint)
    
    def get_latest_releases(self, repo_full_name: str, limit: int = 5, since: Optional[datetime] = None) -> List[Dict]:
        """
        获取仓库最新发布
        
        Args:
            repo_full_name: 仓库全名
            limit: 最大返回数量
            since: 只返回此时间之后的发布
            
        Returns:
            发布信息列表
        """
        self.logger.info(f"获取仓库最新发布: {repo_full_name}")
        endpoint = f"/repos/{repo_full_name}/releases"
        
        params = {"per_page": limit}
        # 添加时间过滤
        if since:
            params["since"] = since.isoformat()
        
        releases = self._make_request(endpoint, params) or []
        
        # 过滤预发布（可选）
        return [
            release for release in releases
            if not release.get("prerelease", False)  # 排除预发布版本
        ][:limit]  # 再次确保不超过限制数量
    
    def get_recent_commits(self, repo_full_name: str, limit: int = 20, since: Optional[datetime] = None) -> List[Dict]:
        """
        获取仓库最近提交
        
        Args:
            repo_full_name: 仓库全名
            limit: 最大返回数量
            since: 只返回此时间之后的提交
            
        Returns:
            提交信息列表
        """
        self.logger.info(f"获取仓库最近提交: {repo_full_name}")
        endpoint = f"/repos/{repo_full_name}/commits"
        
        params = {"per_page": limit}
        if since:
            params["since"] = since.isoformat()
        
        return self._make_request(endpoint, params) or []
    
    def get_recent_pull_requests(self, repo_full_name: str, limit: int = 20, since: Optional[datetime] = None) -> List[Dict]:
        """
        获取仓库最近的Pull Requests
        
        Args:
            repo_full_name: 仓库全名
            limit: 最大返回数量
            since: 只返回此时间之后的PR
            
        Returns:
            PR信息列表
        """
        self.logger.info(f"获取仓库最近PR: {repo_full_name}")
        endpoint = f"/repos/{repo_full_name}/pulls"
        
        params = {
            "state": "all",  # 所有状态（open, closed, merged）
            "sort": "updated",
            "direction": "desc",
            "per_page": limit
        }
        
        prs = self._make_request(endpoint, params) or []
        
        # 如果指定了时间范围，进一步过滤
        if since:
            filtered_prs = []
            for pr in prs:
                updated_at = datetime.fromisoformat(pr.get("updated_at", "").replace("Z", "+00:00"))
                if updated_at >= since:
                    filtered_prs.append(pr)
                if len(filtered_prs) >= limit:
                    break
            return filtered_prs
        
        return prs[:limit]
    
    def get_recent_issues(self, repo_full_name: str, limit: int = 20, since: Optional[datetime] = None) -> List[Dict]:
        """
        获取仓库最近的Issues
        
        Args:
            repo_full_name: 仓库全名
            limit: 最大返回数量
            since: 只返回此时间之后的Issue
            
        Returns:
            Issue信息列表
        """
        self.logger.info(f"获取仓库最近Issues: {repo_full_name}")
        endpoint = f"/repos/{repo_full_name}/issues"
        
        params = {
            "state": "all",  # 所有状态（open, closed）
            "sort": "updated",
            "direction": "desc",
            "per_page": limit,
            "since": since.isoformat() if since else None
        }
        
        # 移除值为None的参数
        params = {k: v for k, v in params.items() if v is not None}
        
        issues = self._make_request(endpoint, params) or []
        
        # 过滤掉PR（因为GitHub API的issues端点会包含PR）
        return [
            issue for issue in issues
            if "pull_request" not in issue  # 排除PR，只保留真正的Issue
        ][:limit]
