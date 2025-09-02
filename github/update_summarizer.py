import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from github.client import GitHubClient
from llm.deepseek import DeepSeekClient
from core.config import Config

class GitHubAIReportGenerator:
    """GitHub仓库AI报告生成器"""
    
    def __init__(self, github_token: str, deepseek_api_key: str, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 初始化依赖组件
        self.github_client = GitHubClient(
            github_token=github_token,
            timeout=config.get("api_timeout", 10),
            retries=config.get("api_retries", 3)
        )
        
        self.deepseek_client = DeepSeekClient(
            api_key=deepseek_api_key,
            config=config
        )
        
        # 报告配置
        self.output_dir = config.get("report.output_dir", "ai_reports")
        self.max_items = config.get("report.max_preview_items", {
            "releases": 3,
            "commits": 5,
            "pull_requests": 5,
            "issues": 5
        })
    
    def generate_ai_enhanced_report(self, repo_full_name: str, since: Optional[datetime] = None,
                                   time_range_desc: str = "最近更新") -> str:
        """生成包含AI总结的报告"""
        os.makedirs(self.output_dir, exist_ok=True)
        
        try:
            self.logger.info(f"开始生成 {repo_full_name} 的AI报告...")
            
            # 1. 获取仓库数据
            repo_info = self.github_client.get_repo_info(repo_full_name)
            if not repo_info:
                self.logger.error(f"无法获取仓库信息: {repo_full_name}")
                return ""
            
            releases = self.github_client.get_latest_releases(
                repo_full_name, 
                limit=self.max_items["releases"],
                since=since
            )
            
            commits = self.github_client.get_recent_commits(
                repo_full_name,
                limit=self.max_items["commits"],
                since=since
            )
            
            prs = self.github_client.get_recent_pull_requests(
                repo_full_name,
                limit=self.max_items["pull_requests"],
                since=since
            )
            
            issues = self.github_client.get_recent_issues(
                repo_full_name,
                limit=self.max_items["issues"],
                since=since
            )
            
            # 2. AI总结
            self.logger.info("正在生成AI总结...")
            summaries = {
                "releases": self.deepseek_client.summarize_releases(releases),
                "commits": self.deepseek_client.summarize_commits(commits),
                "issues_prs": self.deepseek_client.summarize_issues_prs(issues, prs)
            }
            
            # 3. 生成Markdown
            markdown = self._generate_markdown(repo_info, releases, commits, prs, issues, summaries, time_range_desc)
            
            # 4. 保存报告
            return self._save_report(markdown, repo_full_name)
            
        except Exception as e:
            self.logger.error(f"报告生成失败: {str(e)}", exc_info=True)
            return ""
    
    def _generate_markdown(self, repo_info: Dict, releases: List[Dict], commits: List[Dict],
                          prs: List[Dict], issues: List[Dict], summaries: Dict, time_range: str) -> str:
        """生成Markdown内容"""
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        repo_url = repo_info.get("html_url", "")
        
        # 报告头部
        md = [
            f"# 🤖 GitHub仓库AI总结报告: {repo_info.get('full_name')}",
            f"**生成时间**: {generated_at}",
            f"**时间范围**: {time_range}",
            f"**仓库链接**: [{repo_url}]({repo_url})",
            "",
            "## 📊 仓库基本信息",
            f"- 名称: {repo_info.get('name')}",
            f"- 描述: {repo_info.get('description', '无描述')}",
            f"- 星级: {repo_info.get('stargazers_count', 0)} ⭐",
            f"- 分支: {repo_info.get('forks_count', 0)} 🍴",
            f"- 最后更新: {repo_info.get('updated_at', '未知')}",
            "",
            "---",
            "",
            "## 📝 AI智能总结",
        ]
        
        # 发布总结
        md.extend([
            "### 🔖 发布总结",
            summaries["releases"],
            "",
        ])
        
        # 提交总结
        md.extend([
            "### 💻 开发提交总结",
            summaries["commits"],
            "",
        ])
        
        # 社区活动总结
        md.extend([
            "### 📢 社区活动总结",
            summaries["issues_prs"],
            "",
            "---",
            "",
        ])
        
        # 原始数据预览
        md.append("## 🔍 原始数据预览")
        
        # 发布预览
        if releases:
            md.extend([
                "### 最新发布",
                "| 版本 | 发布时间 | 标题 |",
                "|------|----------|------|",
            ])
            for r in releases:
                md.append(f"| {r.get('tag_name')} | {r.get('published_at', '')[:10]} | {r.get('name', '')[:50]} |")
            md.append("")
        
        # 提交预览
        if commits:
            md.extend([
                "### 最近提交",
                "| 哈希 | 作者 | 时间 | 信息 |",
                "|------|------|------|------|",
            ])
            for c in commits:
                sha = c.get('sha', '')[:7]
                msg = c.get('commit', {}).get('message', '').splitlines()[0][:50]
                md.append(f"| {sha} | {c.get('author', {}).get('login', '未知')} | {c.get('commit', {}).get('committer', {}).get('date', '')[:10]} | {msg} |")
            md.append("")
        
        return "\n".join(md)
    
    def _save_report(self, content: str, repo_full_name: str) -> str:
        """保存报告到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = repo_full_name.replace("/", "_")
        filename = f"{safe_name}_ai_report_{timestamp}.md"
        path = os.path.join(self.output_dir, filename)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return path
