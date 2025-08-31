import logging
from datetime import datetime
from typing import Dict, Optional
from github.client import GitHubClient

class ReportGenerator:
    """报告生成器，用于生成仓库更新报告"""
    
    def __init__(self, github_client: GitHubClient):
        self.github_client = github_client
        self.logger = logging.getLogger(__name__)
    
    def generate_repo_report(self, repo: str) -> str:
        """
        生成指定仓库的更新报告
        
        Args:
            repo: 仓库名，格式为 "owner/repo"
            
        Returns:
            格式化的报告字符串
        """
        self.logger.info(f"Generating report for {repo}")
        
        # 获取仓库基本信息
        repo_info = self.github_client.get_repo_info(repo)
        if not repo_info:
            return f"无法获取仓库 {repo} 的信息"
        
        # 获取最新发布
        latest_release = self.github_client.get_latest_release(repo)
        
        # 构建报告
        report = []
        report.append(f"# GitHub 仓库报告: {repo}")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # 基本信息
        report.append("## 基本信息")
        report.append(f"- 名称: {repo_info.get('name')}")
        report.append(f"- 描述: {repo_info.get('description', '无描述')}")
        report.append(f"- 星级: {repo_info.get('stargazers_count', 0)} ⭐")
        report.append(f"- 分支: {repo_info.get('forks_count', 0)} 🍴")
        report.append(f"- 最后更新: {repo_info.get('updated_at', '未知')}\n")
        
        # 最新发布信息
        report.append("## 最新发布")
        if latest_release:
            report.append(f"- 版本: {latest_release.get('tag_name')}")
            report.append(f"- 发布时间: {latest_release.get('published_at')}")
            report.append(f"- 发布者: {latest_release.get('author', {}).get('login', '未知')}")
            report.append(f"- 下载次数: {self._calculate_downloads(latest_release)}")
            report.append("\n### 发布说明:")
            report.append(latest_release.get('body', '无发布说明').strip())
        else:
            report.append("该仓库尚未发布任何版本")
        
        return "\n".join(report)
    
    def _calculate_downloads(self, release: Dict) -> int:
        """计算发布的总下载次数"""
        assets = release.get('assets', [])
        return sum(asset.get('download_count', 0) for asset in assets)
    
    def save_report(self, report: str, repo: str, report_type: str = "latest") -> str:
        """保存报告到文件"""
        filename = f"{repo.replace('/', '-')}_{report_type}_report_{datetime.now().strftime('%Y%m%d')}.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        self.logger.info(f"Report saved to {filename}")
        return filename
