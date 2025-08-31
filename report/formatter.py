from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List

class ReportFormatter(ABC):
    """报告格式化器基类"""
    
    @abstractmethod
    def format_report(self, data: Dict) -> str:
        """格式化单个仓库报告"""
        pass
    
    @abstractmethod
    def format_weekly_report(self, data: Dict) -> str:
        """格式化每周汇总报告"""
        pass

class MarkdownFormatter(ReportFormatter):
    """Markdown格式报告生成器"""
    
    def format_report(self, data: Dict) -> str:
        """生成Markdown格式的仓库报告"""
        repo_info = data["repo_info"]
        generated_at = data["generated_at"].strftime("%Y-%m-%d %H:%M:%S")
        
        # 报告头部
        report = [
            f"# GitHub 仓库报告: {repo_info.get('full_name')}",
            f"生成时间: {generated_at}",
            "",
            "## 基本信息",
            f"- 名称: {repo_info.get('name')}",
            f"- 描述: {repo_info.get('description', '无描述')}",
            f"- 星级: {repo_info.get('stargazers_count', 0)} ⭐",
            f"- 分支: {repo_info.get('forks_count', 0)} 🍴",
            f"- 最后更新: {repo_info.get('updated_at', '未知')}"
        ]
        
        # 最新发布
        if data.get("releases"):
            report.extend([
                "",
                "## 最新发布",
                "| 版本 | 发布时间 | 发布者 | 描述 |",
                "|------|----------|--------|------|",
            ])
            
            for release in data["releases"]:
                report.append(
                    f"| {release.get('tag_name', 'N/A')} | {release.get('published_at', 'N/A')} | "
                    f"{release.get('author', {}).get('login', 'N/A')} | {release.get('name', '无描述')[:50]}... |"
                )
        
        # 最近提交
        if data.get("commits"):
            report.extend([
                "",
                "## 最近提交",
                "| 哈希 | 时间 | 作者 | 消息 |",
                "|------|------|------|------|",
            ])
            
            for commit in data["commits"]:
                sha = commit.get('sha', '')[:7]  # 只显示前7位哈希
                report.append(
                    f"| [{sha}]({commit.get('html_url')}) | {commit.get('commit', {}).get('committer', {}).get('date', 'N/A')} | "
                    f"{commit.get('author', {}).get('login', 'N/A')} | {commit.get('commit', {}).get('message', '').splitlines()[0][:50]}... |"
                )
        
        # 最近PR
        if data.get("pull_requests"):
            report.extend([
                "",
                "## 最近Pull Requests",
                "| 编号 | 状态 | 创建时间 | 作者 | 标题 |",
                "|------|------|----------|------|------|",
            ])
            
            for pr in data["pull_requests"]:
                report.append(
                    f"| #{pr.get('number')} | {pr.get('state')} | {pr.get('created_at')} | "
                    f"{pr.get('user', {}).get('login', 'N/A')} | {pr.get('title', '')[:50]}... |"
                )
        
        # 最近Issues
        if data.get("issues"):
            report.extend([
                "",
                "## 最近Issues",
                "| 编号 | 状态 | 创建时间 | 作者 | 标题 |",
                "|------|------|----------|------|------|",
            ])
            
            for issue in data["issues"]:
                report.append(
                    f"| #{issue.get('number')} | {issue.get('state')} | {issue.get('created_at')} | "
                    f"{issue.get('user', {}).get('login', 'N/A')} | {issue.get('title', '')[:50]}... |"
                )
        
        return "\n".join(report)
    
    def format_weekly_report(self, data: Dict) -> str:
        """生成Markdown格式的每周汇总报告"""
        start_date = data["time_range"]["start"].strftime("%Y-%m-%d")
        end_date = data["time_range"]["end"].strftime("%Y-%m-%d")
        
        report = [
            f"# {data['title']}",
            f"生成时间: {data['generated_at'].strftime('%Y-%m-%d %H:%M:%S')}",
            f"时间范围: {start_date} 至 {end_date}",
            f"监控仓库数量: {len(data['repos'])}",
            ""
        ]
        
        # 添加每个仓库的报告
        for repo in data["repos"]:
            report.extend([
                f"## 📦 {repo['name']}",
                "",
                repo["report"],
                "",
                "---",
                ""
            ])
        
        return "\n".join(report)

class HtmlFormatter(ReportFormatter):
    """HTML格式报告生成器"""
    
    def format_report(self, data: Dict) -> str:
        """生成HTML格式的仓库报告"""
        repo_info = data["repo_info"]
        generated_at = data["generated_at"].strftime("%Y-%m-%d %H:%M:%S")
        
        # HTML头部
        html = [
            "<!DOCTYPE html>",
            "<html lang='en'>",
            "<head>",
            "    <meta charset='UTF-8'>",
            "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
            f"    <title>GitHub 仓库报告: {repo_info.get('full_name')}</title>",
            "    <style>",
            "        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; color: #333; }",
            "        h1, h2 { color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 10px; }",
            "        .info { margin-bottom: 20px; }",
            "        .info p { margin: 8px 0; }",
            "        table { width: 100%; border-collapse: collapse; margin: 20px 0; }",
            "        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }",
            "        th { background-color: #f8f9fa; }",
            "        tr:hover { background-color: #f5f5f5; }",
            "    </style>",
            "</head>",
            "<body>",
            f"    <h1>GitHub 仓库报告: {repo_info.get('full_name')}</h1>",
            f"    <p><em>生成时间: {generated_at}</em></p>",
            
            "    <h2>基本信息</h2>",
            "    <div class='info'>",
            f"        <p><strong>名称:</strong> {repo_info.get('name')}</p>",
            f"        <p><strong>描述:</strong> {repo_info.get('description', '无描述')}</p>",
            f"        <p><strong>星级:</strong> {repo_info.get('stargazers_count', 0)} ⭐</p>",
            f"        <p><strong>分支:</strong> {repo_info.get('forks_count', 0)} 🍴</p>",
            f"        <p><strong>最后更新:</strong> {repo_info.get('updated_at', '未知')}</p>",
            "    </div>"
        ]
        
        # 最新发布
        if data.get("releases"):
            html.extend([
                "    <h2>最新发布</h2>",
                "    <table>",
                "        <tr><th>版本</th><th>发布时间</th><th>发布者</th><th>描述</th></tr>"
            ])
            
            for release in data["releases"]:
                html.append(
                    f"        <tr>",
                    f"            <td>{release.get('tag_name', 'N/A')}</td>",
                    f"            <td>{release.get('published_at', 'N/A')}</td>",
                    f"            <td>{release.get('author', {}).get('login', 'N/A')}</td>",
                    f"            <td>{release.get('name', '无描述')}</td>",
                    f"        </tr>"
                )
            
            html.append("    </table>")
        
        # 其他部分（提交、PR、Issues）类似Markdown格式器的逻辑，省略实现...
        
        # HTML尾部
        html.extend([
            "</body>",
            "</html>"
        ])
        
        return "\n".join(html)
    
    def format_weekly_report(self, data: Dict) -> str:
        """生成HTML格式的每周汇总报告"""
        # 实现逻辑类似Markdown版本，省略具体实现
        start_date = data["time_range"]["start"].strftime("%Y-%m-%d")
        end_date = data["time_range"]["end"].strftime("%Y-%m-%d")
        
        html = [
            "<!DOCTYPE html>",
            "<html lang='en'>",
            "<head>",
            "    <meta charset='UTF-8'>",
            "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
            f"    <title>{data['title']}</title>",
            "    <style>",
            "        /* 样式定义 */",
            "    </style>",
            "</head>",
            "<body>",
            f"    <h1>{data['title']}</h1>",
            f"    <p>生成时间: {data['generated_at'].strftime('%Y-%m-%d %H:%M:%S')}</p>",
            f"    <p>时间范围: {start_date} 至 {end_date}</p>",
            f"    <p>监控仓库数量: {len(data['repos'])}</p>",
        ]
        
        # 添加每个仓库的报告
        for repo in data["repos"]:
            html.extend([
                f"    <h2>{repo['name']}</h2>",
                f"    <div class='repo-report'>{repo['report']}</div>",
                "    <hr>"
            ])
        
        html.extend([
            "</body>",
            "</html>"
        ])
        
        return "\n".join(html)
