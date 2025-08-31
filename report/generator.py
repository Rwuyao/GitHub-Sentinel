import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from .formatter import MarkdownFormatter, HtmlFormatter
from github.client import GitHubClient

class ReportGenerator:
    """报告生成器，负责收集仓库信息并生成格式化报告"""
    
    def __init__(self, github_client: GitHubClient, config: Dict = None):
        self.github_client = github_client
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # 报告配置
        self.report_config = self.config.get("report", {})
        self.save_path = self.report_config.get("save_path", "reports/")
        self.format = self.report_config.get("format", "markdown")
        self.include = self.report_config.get("include", {
            "releases": True,
            "commits": True,
            "pull_requests": True,
            "issues": True,
            "max_items": 20
        })
        
        # 初始化格式化器
        self.formatters = {
            "markdown": MarkdownFormatter(),
            "html": HtmlFormatter()
        }
        
        # 确保报告目录存在
        os.makedirs(self.save_path, exist_ok=True)
    
    def generate_repo_report(self, repo_full_name: str, since: Optional[datetime] = None) -> str:
        """
        生成单个仓库的报告
        
        Args:
            repo_full_name: 仓库全名，格式为 "owner/repo"
            since: 只包含此时间之后的更新，None表示获取最新信息
            
        Returns:
            格式化的报告内容
        """
        self.logger.info(f"生成仓库报告: {repo_full_name}")
        
        try:
            # 获取仓库基本信息
            repo_info = self.github_client.get_repo_info(repo_full_name)
            if not repo_info:
                return f"无法获取仓库 {repo_full_name} 的信息"
            
            # 收集需要包含的内容
            report_data = {
                "repo_info": repo_info,
                "generated_at": datetime.now(),
                "since": since,
                "releases": [],
                "commits": [],
                "pull_requests": [],
                "issues": []
            }
            
            # 获取最新发布
            if self.include.get("releases", True):
                report_data["releases"] = self.github_client.get_latest_releases(
                    repo_full_name, 
                    limit=self.include.get("max_items", 20),
                    since=since
                )
            
            # 获取最近提交
            if self.include.get("commits", True):
                report_data["commits"] = self.github_client.get_recent_commits(
                    repo_full_name, 
                    limit=self.include.get("max_items", 20),
                    since=since
                )
            
            # 获取最近PR
            if self.include.get("pull_requests", True):
                report_data["pull_requests"] = self.github_client.get_recent_pull_requests(
                    repo_full_name, 
                    limit=self.include.get("max_items", 20),
                    since=since
                )
            
            # 获取最近Issues
            if self.include.get("issues", True):
                report_data["issues"] = self.github_client.get_recent_issues(
                    repo_full_name, 
                    limit=self.include.get("max_items", 20),
                    since=since
                )
            
            # 选择格式化器并生成报告
            formatter = self.formatters.get(self.format, self.formatters["markdown"])
            return formatter.format_report(report_data)
            
        except Exception as e:
            self.logger.error(f"生成报告失败: {str(e)}")
            return f"生成报告时发生错误: {str(e)}"
    
    def generate_weekly_report(self, subscriptions: List[Dict]) -> str:
        """生成包含多个订阅仓库的每周汇总报告"""
        self.logger.info(f"生成每周汇总报告，包含 {len(subscriptions)} 个仓库")
        
        report_data = {
            "title": "GitHub Sentinel 每周汇总报告",
            "generated_at": datetime.now(),
            "time_range": {
                "start": datetime.now() - timedelta(days=7),
                "end": datetime.now()
            },
            "repos": []
        }
        
        # 为每个订阅仓库生成报告片段
        for sub in subscriptions:
            repo_report = self.generate_repo_report(
                sub["repository"],
                since=report_data["time_range"]["start"]
            )
            report_data["repos"].append({
                "name": sub["repository"],
                "report": repo_report
            })
        
        # 选择格式化器并生成汇总报告
        formatter = self.formatters.get(self.format, self.formatters["markdown"])
        return formatter.format_weekly_report(report_data)
    
    def save_report(self, content: str, repo_full_name: str) -> str:
        """
        保存报告到文件
        
        Args:
            content: 报告内容
            repo_full_name: 仓库全名
            
        Returns:
            保存的文件路径
        """
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_repo_name = repo_full_name.replace("/", "_")
        file_ext = "md" if self.format == "markdown" else "html"
        filename = f"{safe_repo_name}_{timestamp}.{file_ext}"
        file_path = os.path.join(self.save_path, filename)
        
        # 保存文件
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.logger.info(f"报告已保存到: {file_path}")
            return file_path
        except Exception as e:
            self.logger.error(f"保存报告失败: {str(e)}")
            return ""
