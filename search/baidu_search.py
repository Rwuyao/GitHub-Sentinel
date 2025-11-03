import requests
import json
import time
import logging
from typing import Dict, Optional, List, Union
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class BaiduQianfanSearch:
    """
    百度千帆搜索API封装类
    使用百度千帆平台提供的搜索API进行搜索
    
    注意：需要先在百度千帆平台获取API密钥
    """
    
    def __init__(self, api_key: str):
        """
        初始化百度千帆搜索API
        
        参数:
            api_key: 百度千帆平台的API密钥
        """
        self.api_key = api_key
        self.base_url = "https://qianfan.baidubce.com/v2/ai_search/web_search"
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        # API调用统计
        self.call_count = 0
        self.last_call_time = 0
        
    def search(self, 
              query: str, 
              edition: str = "standard",
              search_source: str = "baidu_search_v2",
              search_recency_filter: str = "week",
              timeout: int = 30) -> Optional[Dict]:
        """
        执行百度千帆搜索
        
        参数:
            query: 搜索关键词
            edition: API版本，默认为"standard"
            search_source: 搜索来源，默认为"baidu_search_v2"
            search_recency_filter: 时间过滤，可选值: "day", "week", "month", "year"
            timeout: 请求超时时间，默认为30秒
        
        返回:
            包含搜索结果的字典，或None表示失败
        """
        try:
            # 检查API密钥是否有效
            if not self.api_key:
                print("❌ API密钥不能为空")
                return None
            
            # 检查请求频率（简单限流）
            current_time = time.time()
            if current_time - self.last_call_time < 1:  # 限制1秒内最多1次请求
                time.sleep(1 - (current_time - self.last_call_time))
            
            # 构建请求参数
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "edition": edition,
                "search_source": search_source,
                "search_recency_filter": search_recency_filter
            }
            
            print(f"🔍 正在使用百度千帆搜索: {query}")
            print(f"📋 搜索参数: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            
            # 发送请求
            response = requests.post(
                self.base_url,
                headers=self.headers,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=timeout
            )
            
            # 更新调用统计
            self.call_count += 1
            self.last_call_time = time.time()
            
            # 检查响应状态码
            response.raise_for_status()
            
            # 设置响应响应编码
            response.encoding = "utf-8"
            
            # 解析JSON响应
            result = response.json()
            
            print(f"✅ 搜索成功，状态码: {response.status_code}")
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 搜索请求失败: {e}")
            if hasattr(e, 'response') and e.response:
                try:
                    error_detail = e.response.json()
                    print(f"❌ 错误详情: {json.dumps(error_detail, ensure_ascii=False, indent=2)}")
                except:
                    print(f"❌ 错误响应: {e.response.text[:500]}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            print(f"❌ 响应内容: {response.text[:500]}")
            return None
        except Exception as e:
            print(f"❌ 搜索过程异常: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def fetch_page_content(self, url: str, timeout: int = 10) -> Optional[str]:
        """
        通过URL获取页面静态内容，提取关键文本
        
        参数:
            url: 要获取的页面URL
            timeout: 请求超时时间，默认为10秒
        
        返回:
            提取的页面文本内容，或None表示失败
        """
        try:
            # 验证URL格式
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                print(f"❌ 无效的URL格式: {url}")
                return None
            
            # 创建会话并设置重试策略
            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            
            # 设置请求头，模拟浏览器访问
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.5,en;q=0.3',
                'Connection': 'keep-alive'
            }
            
            print(f"🌐 正在页面内容: {url}")
            
            # 发送GET请求
            response = session.get(
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            
            # 设置正确的编码
            response.encoding = response.apparent_encoding
            
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取页面标题
            title = soup.title.string.strip() if soup.title else "无标题"
            
            # 提取正文内容
            # 尝试提取常见的正文标签
            content_tags = ['div', 'article', 'main', 'section']
            content = ""
            
            for tag in content_tags:
                elements = soup.find_all(tag)
                for elem in elements:
                    # 过滤掉可能不是正文的内容
                    if not any(cls in elem.get('class', []) for cls in ['nav', 'menu', 'sidebar', 'footer', 'header', 'advertisement']):
                        paragraphs = elem.find_all('p')
                        if paragraphs:
                            content += '\n'.join([p.get_text(strip=True) for p in paragraphs])
            
            # 如果没有找到足够的内容，尝试提取所有文本
            if not content or len(content) < 100:
                # 提取所有文本，但过滤掉过短的内容
                all_text = soup.get_text(separator='\n', strip=True)
                # 按段落分割并过滤
                paragraphs = [p for p in all_text.split('\n') if len(p) > 50]
                content = '\n\n'.join(paragraphs[:10])  # 取前10个较长的段落
            
            # 清理内容
            content = content.strip()
            
            # 如果内容仍然太短，使用元描述
            if not content or len(content) < 50:
                meta_description = soup.find('meta', attrs={'name': 'description'})
                if meta_description and meta_description.get('content'):
                    content = meta_description['content']
            
            # 输出到日志
            if content:
                print(f"📄 提取页面内容成功: {title}")
                print(f"📝 内容长度: {len(content)} 字符")
                print(f"🔍 内容预览: {content[:200]}..." if len(content) > 200 else f"🔍 内容: {content}")
                print("-" * 80)
            else:
                print(f"⚠️  未能从页面提取有效内容: {url}")
            
            return content
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 获取页面内容失败: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"❌ 状态码: {e.response.status_code}")
            return None
        except Exception as e:
            print(f"❌ 解析页面内容异常: {e}")
            import traceback
            traceback.print_exc()
            return None

# 全局变量存储搜索器实例
searcher = None

def initialize_searcher(api_key: str) -> str:
    """初始化搜索器"""
    global searcher
    try:
        if api_key:
            searcher = BaiduQianfanSearch(api_key)
            return "✅ 搜索器初始化成功！"
        else:
            searcher = None
            return "⚠️ API密钥为空，请输入有效的API密钥。"
    except Exception as e:
        searcher = None
        return f"❌ 初始化失败: {str(e)}"

def search_function(query: str) -> List[Dict]:
    """使用百度千帆API进行搜索"""
    global searcher
    
    # 检查搜索器是否已初始化
    if not searcher:
        return []
    
    try:
        # 调用百度千帆API进行搜索
        result = searcher.search(query)
        
        if not result:
            return []
        
        # 解析搜索结果
        search_results = []
        
        # 检查响应结构
        if "references" in result:
            # 首先尝试从 references 数组获取结果
                for item in result["references"]:
                    # 提取标题、内容和URL
                    title = item.get("title", "无标题")
                    content = item.get("content", item.get("snippet", "无内容"))
                    url = item.get("url", "")
                    
                    # 如果内容太短，尝试从其他字段获取
                    if len(str(content)) < 50:
                        content = item.get("snippet", "无内容")
                    
                    search_results.append({
                        "title": title,
                        "content": content,
                        "url": url
                    })       
        print(f"📊 解析到 {len(search_results)} 个搜索结果")
        
        # 抓取每个搜索结果的页面内容
        print("\n" + "="*60)
        print("开始抓取页面内容...")
        print("="*60)
        
        for i, result in enumerate(search_results):
            url = result.get("url")
            if url and url.startswith(("http://", "https://")):
                try:
                    print(f"\n🔍 正在处理第 {i+1}/{len(search_results)} 个结果:")
                    print(f"   URL: {url}")
                    
                    # 调用fetch_page_content方法获取页面内容
                    page_content = searcher.fetch_page_content(url)
                    
                    # 如果获取到内容，更新结果中的content字段
                    if page_content and len(page_content) > len(result["content"]):
                        # 保留原始摘要的前200个字符作为摘要，完整内容存储在full_content中
                        result["full_content"] = page_content
                        # 更新content为更详细的摘要
                        if len(page_content) > 300:
                            result["content"] = page_content[:300] + "..."
                        
                except Exception as e:
                    print(f"❌ 处理URL {url} 时出错: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"\n⚠️  无效的URL: {url}")
        
        print("\n" + "="*60)
        print("页面内容抓取完成")
        print("="*60)
        
        return search_results
        
    except Exception as e:
        print(f"❌ 搜索过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
