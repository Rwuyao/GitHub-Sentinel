import logging
import json
import requests
from typing import List, Dict, Optional
from core.config import Config

class DeepSeekClient:
    """DeepSeek大模型客户端（独立模块）"""
    
    def __init__(self, api_key: str, config: Optional[Config] = None):
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key
        
        # 从配置获取参数，或使用默认值
        if config:
            self.api_url = config.get("deepseek.api_url", "https://api.deepseek.com/v1/chat/completions")
            self.model = config.get("deepseek.model", "deepseek-chat")
            self.temperature = config.get("deepseek.temperature", 0.3)
            self.max_tokens = config.get("deepseek.max_tokens", 1000)
        else:
            self.api_url = "https://api.deepseek.com/v1/chat/completions"
            self.model = "deepseek-chat"
            self.temperature = 0.3
            self.max_tokens = 1000
        
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def _call_api(self, messages: List[Dict[str, str]]) -> str:
        """调用DeepSeek API"""
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                data=json.dumps(payload),
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                self.logger.error("DeepSeek API返回格式异常")
                return "未能生成总结（API返回格式异常）"
                
        except Exception as e:
            self.logger.error(f"DeepSeek API调用失败: {str(e)}")
            return f"未能生成总结（错误: {str(e)}）"
    
    def summarize_releases(self, releases: List[Dict]) -> str:
        """总结发布信息"""
        if not releases:
            return "无最新发布信息"
            
        release_data = []
        for release in releases:
            release_data.append({
                "版本": release.get("tag_name", "未知版本"),
                "发布时间": release.get("published_at", "未知时间"),
                "标题": release.get("name", "无标题"),
                "描述": release.get("body", "无描述")[:500]
            })
        
        prompt = f"""请总结以下GitHub仓库的最新发布信息，突出主要功能变化和重要修复：
{json.dumps(release_data, ensure_ascii=False, indent=2)}

总结要求：
1. 分点列出每个版本的主要变化
2. 语言简洁明了，重点说明对用户有影响的变更
"""
        
        return self._call_api([{"role": "user", "content": prompt}])
    
    def summarize_commits(self, commits: List[Dict]) -> str:
        """总结提交记录"""
        if not commits:
            return "无最近提交记录"
            
        commit_data = []
        for commit in commits:
            commit_msg = commit.get("commit", {}).get("message", "无提交信息").splitlines()[0]
            commit_data.append({
                "哈希": commit.get("sha", "")[:7],
                "作者": commit.get("author", {}).get("login", "未知作者"),
                "时间": commit.get("commit", {}).get("committer", {}).get("date", "未知时间"),
                "信息": commit_msg
            })
        
        prompt = f"""请总结以下GitHub仓库的最近提交记录，识别开发趋势：
{json.dumps(commit_data, ensure_ascii=False, indent=2)}

总结要求：
1. 归纳主要的开发工作方向（功能开发、bug修复等）
2. 指出是否有集中解决的问题或重点开发的功能
3. 语言简洁，条理清晰
"""
        
        return self._call_api([{"role": "user", "content": prompt}])
    
    def summarize_issues_prs(self, issues: List[Dict], prs: List[Dict]) -> str:
        """总结Issues和PRs"""
        if not issues and not prs:
            return "无最近社区活动"
            
        issue_data = [{"编号": i.get("number"), "状态": i.get("state"), "标题": i.get("title")} for i in issues]
        pr_data = [{"编号": p.get("number"), "状态": p.get("state"), "标题": p.get("title"), "是否合并": "是" if p.get("merged_at") else "否"} for p in prs]
        
        prompt = f"""请总结以下GitHub仓库的社区活动：
Issues: {json.dumps(issue_data, ensure_ascii=False)}
Pull Requests: {json.dumps(pr_data, ensure_ascii=False)}

总结要求：
1. 分析主要讨论的问题和贡献的功能
2. 指出社区关注的焦点
3. 语言简洁，重点突出
"""
        
        return self._call_api([{"role": "user", "content": prompt}])
