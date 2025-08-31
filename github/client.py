import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List

class GitHubClient:
    """GitHub API客户端，用于获取仓库信息"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.logger = logging.getLogger(__name__)
    
    def get_latest_release(self, repo: str) -> Optional[Dict]:
        """
        获取仓库的最新发布版本
        
        Args:
            repo: 仓库名，格式为 "owner/repo"
            
        Returns:
            包含最新发布信息的字典，或None（如果没有发布）
        """
        try:
            url = f"{self.base_url}/repos/{repo}/releases/latest"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 404:
                self.logger.warning(f"No releases found for {repo}")
                return None
                
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error fetching latest release for {repo}: {str(e)}")
            return None
    
    def get_recent_commits(self, repo: str, since: datetime) -> List[Dict]:
        """获取自指定时间以来的提交记录"""
        try:
            url = f"{self.base_url}/repos/{repo}/commits"
            params = {
                "since": since.isoformat(),
                "per_page": 100
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error fetching commits for {repo}: {str(e)}")
            return []
    
    def get_repo_info(self, repo: str) -> Optional[Dict]:
        """获取仓库基本信息"""
        try:
            url = f"{self.base_url}/repos/{repo}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error fetching info for {repo}: {str(e)}")
            return None
