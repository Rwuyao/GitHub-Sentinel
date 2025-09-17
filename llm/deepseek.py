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
        self.config = config
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
                timeout=60
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
        
        # 加载system-role提示词
        prompt_file = "config/prompts/github_release_prompts.txt"
        
        # 尝试从文件加载
        if self.config.load_prompt("github_release_prompts", prompt_file):
            systemPrompt = self.config.get_prompt("github_release_prompts")
        else:
            systemPrompt = "你是一个专业的GitHub仓库分析助手，擅长总结代码仓库的活动和变化。"    

        prompt = f"""Release: {json.dumps(release_data, ensure_ascii=False, indent=2)}"""
        return self._call_api([{"role": "system", "content": systemPrompt},{"role": "user", "content": prompt}])
 
    def summarize_issues_prs(self, issues: List[Dict], prs: List[Dict]) -> str:
        """总结Issues和PRs"""
        if not issues and not prs:
            return "无最近社区活动"
            
        issue_data = [{"编号": i.get("number"), "状态": i.get("state"), "标题": i.get("title")} for i in issues]
        pr_data = [{"编号": p.get("number"), "状态": p.get("state"), "标题": p.get("title"), "是否合并": "是" if p.get("merged_at") else "否"} for p in prs]
        
        # 加载system-role提示词
        prompt_file = "config/prompts/issues_pr_prompts.txt"
        
        # 尝试从文件加载
        if self.config.load_prompt("issues_pr_prompts", prompt_file):
            systemPrompt = self.config.get_prompt("issues_pr_prompts")
        else:
            systemPrompt = "你是一个专业的GitHub仓库分析助手，擅长总结代码仓库的活动和变化。"    

        prompt = f"""Issues: {json.dumps(issue_data, ensure_ascii=False)}
                     Pull Requests: {json.dumps(pr_data, ensure_ascii=False)}
                    """
        return self._call_api([{"role": "system", "content": systemPrompt},
                               {"role": "user", "content": prompt}])