import os
import time
import logging
import requests
from typing import List, Dict, Optional
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("hackernews-crawler")

class HackerNewsCrawler:
    """HackerNews热点爬取工具，获取最新热门技术话题"""
    
    def __init__(self, max_items: int = 30, timeout: int = 10):
        """
        初始化HackerNews爬虫
        
        参数:
            max_items: 最大获取条目数量
            timeout: 请求超时时间(秒)
        """
        self.base_api_url = "https://hacker-news.firebaseio.com/v0"
        self.max_items = max_items
        self.timeout = timeout
        self.session = requests.Session()
        # 添加请求头模拟浏览器
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
    
    def _fetch(self, endpoint: str) -> Optional[Dict or List]:
        """基础API请求方法"""
        try:
            url = f"{self.base_api_url}/{endpoint}"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()  # 抛出HTTP错误
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败 {endpoint}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"数据处理失败 {endpoint}: {str(e)}")
            return None
    
    def get_latest_stories(self) -> List[Dict]:
        """获取最新热点条目"""
        logger.info(f"获取HackerNews最新{self.max_items}条热点")
        
        # 获取最新条目ID列表
        story_ids = self._fetch("newstories.json")
        if not story_ids or not isinstance(story_ids, list):
            logger.error("无法获取热点ID列表")
            return []
        
        # 限制获取数量
        story_ids = story_ids[:self.max_items]
        stories = []
        
        # 逐个获取条目详情
        for idx, story_id in enumerate(story_ids, 1):
            # 添加延迟避免请求过于频繁
            if idx > 1:
                time.sleep(0.5)
                
            story = self._fetch(f"item/{story_id}.json")
            if story and self._is_valid_story(story):
                # 提取关键信息
                processed = self._process_story(story)
                stories.append(processed)
                logger.debug(f"已获取条目 {idx}/{self.max_items}: {processed['title']}")
        
        logger.info(f"成功获取{len(stories)}条有效热点")
        return stories
    
    def _is_valid_story(self, story: Dict) -> bool:
        """验证条目是否为有效的故事（排除评论、失效条目）"""
        return (
            story.get("type") == "story" and 
            story.get("title") and 
            (story.get("url") or story.get("text"))
        )
    
    def _process_story(self, story: Dict) -> Dict:
        """处理原始条目数据，提取关键信息"""
        return {
            "id": story.get("id"),
            "title": story.get("title"),
            "url": story.get("url"),
            "text": story.get("text", ""),  # 有些条目是文本内容而非链接
            "score": story.get("score", 0),
            "by": story.get("by", "unknown"),
            "time": datetime.fromtimestamp(story.get("time", 0)).strftime('%Y-%m-%d %H:%M:%S'),
            "descendants": story.get("descendants", 0),  # 评论数
            "kids": story.get("kids", [])  # 评论ID列表
        }
    
    def get_trending_topics(self, stories: List[Dict], top_n: int = 5) -> List[str]:
        """从热点中提取趋势话题（简单关键词提取）"""
        if not stories:
            return []
            
        # 简单关键词库（可扩展为更复杂的NLP分析）
        tech_keywords = {
            "AI": ["ai", "artificial intelligence", "machine learning", "llm", "gpt", "neural network"],
            "Python": ["python", "django", "flask"],
            "JavaScript": ["javascript", "typescript", "node.js", "react", "vue"],
            "Cloud": ["cloud", "aws", "azure", "gcp", "serverless"],
            "Blockchain": ["blockchain", "crypto", "bitcoin", "ethereum", "nft"],
            "DevOps": ["devops", "docker", "kubernetes", "ci/cd", "terraform"],
            "Security": ["security", "privacy", "cyber", "encryption", "vulnerability"],
            "Data": ["data", "database", "sql", "nosql", "data science", "big data"]
        }
        
        # 统计关键词出现次数
        keyword_counts = {category: 0 for category in tech_keywords}
        
        for story in stories:
            content = f"{story['title'].lower()} {story['text'].lower()}"
            for category, keywords in tech_keywords.items():
                for keyword in keywords:
                    if keyword in content:
                        keyword_counts[category] += 1
                        break  # 每个条目对同一类别只计数一次
        
        # 排序并返回前N个趋势话题
        trending = sorted(
            keyword_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:top_n]
        
        # 过滤掉计数为0的话题
        return [category for category, count in trending if count > 0]

if __name__ == "__main__":
    # 获取最新的15条热点新闻
    latest_stories = get_latest_hackernews(15)
    
    if latest_stories:
        print("HackerNews 最新热点：\n")
        for i, story in enumerate(latest_stories, 1):
            print(f"{i}. {story['title']}")
            print(f"   链接: {story['url']}")
            print(f"   分数: {story['score']} | 作者: {story['author']} | 发布时间: {story['time']} | 评论数: {story['comments']}")
            print("-" * 80)
    else:
        print("未能获取到新闻数据")