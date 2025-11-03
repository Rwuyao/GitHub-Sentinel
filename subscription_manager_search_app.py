"""
Gradio搜索总结助手 - 无配置版
直接在代码中设置API密钥，删除配置界面
"""

import gradio as gr
import time
import re
import json
import requests
from datetime import datetime
from typing import Dict, Optional, List, Union

# 导入百度搜索模块
from search.baidu_search import BaiduQianfanSearch, initialize_searcher, search_function

# ==============================================================================
# API密钥配置 - 请在此处设置您的API密钥
# ==============================================================================
# DeepSeek大模型API配置
DEEPSEEK_API_KEY = "sk-9f4b5c77f02d4b22a23c4a4aa4a10054"  # 请设置您的DeepSeek API密钥
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# 百度千帆API配置
BAIDU_API_KEY = "bce-v3/ALTAK-6M0XZAP4p09OIa2y5O5FX/c4383c8998a48a0548bdeb0f1ac50d856ea350a1"  # 请设置您的百度千帆API密钥
# ==============================================================================

# 全局状态管理 - 使用更简单的方式
global_state = {
    "current_page": 1,
    "items_per_page": 5,
    "total_results": [],
    "search_results": [],
    "selected_results": [],
    "summary_output": ""
}

# 初始化百度搜索器
if BAIDU_API_KEY:
    initialize_searcher(BAIDU_API_KEY)

# 模拟搜索结果（用于测试）
mock_results = [
    {
        "title": "人工智能在医疗领域的应用",
        "content": "人工智能技术正在彻底改变医疗行业带来革命性的变化。从疾病诊断到药物研发，AI都发挥着重要作用。机器学习算法可以分析大量的医疗数据，帮助医生疾病模式，帮助医生做出更准确的诊断。在医学影像领域，AI系统可以自动检测肿瘤和其他异常，提高诊断效率。此外，AI还可以用于个性化医疗，根据患者的基因信息和生活习惯，制定定制化的治疗方案。随着技术的不断进步，AI在医疗领域的应用前景非常广阔，但同时需要解决数据隐私和算法透明度等挑战。"
    },
    {
        "title": "气候变化对全球生态系统的影响",
        "content": "气候变化是当今世界面临的最严峻挑战之一。全球气温上升导致冰川融化、海平面上升，威胁沿海地区的生态系统和人类居住地。极端天气天气事件如飓风、干旱和洪水变得更加频繁，给农业生产和粮食安全带来巨大压力。气候变化还影响生物多样性，许多物种面临灭绝的风险。海洋酸化是另一个严重问题，威胁着海洋生态系统的平衡。为了应对这些挑战，国际社会需要采取紧急行动，减少温室气体排放，保护生态系统，提高社会的适应能力。"
    },
    {
        "title": "量子计算的最新进展",
        "content": "量子计算是一种基于量子力学原理的计算方式，具有解决传统计算机难以处理的复杂问题的潜力。近年来，量子计算领域取得了显著进展。谷歌、IBM、微软等科技巨头纷纷投入巨资研发量子计算机。2019年，谷歌宣布实现了量子优越性，即量子计算机完成了传统超级计算机无法在合理时间内完成的计算任务。量子计算在密码学、材料科学、药物研发等领域有广泛应用前景。然而，量子计算机仍然面临着稳定性、错误率和 scalability等挑战。研究人员正在不断探索新的量子算法和硬件技术，推动量子计算的实用化进程。"
    },
    {
        "title": "元宇宙：数字与现实的融合",
        "content": "元宇宙是一个虚拟的数字空间，用户可以通过虚拟现实技术沉浸其中，与数字环境和其他用户进行互动。元宇宙概念近年来受到科技行业的广泛关注，被认为是互联网的下一代形态。在元宇宙中，人们可以工作、学习、娱乐、社交，甚至进行商业活动。元宇宙的发展依赖于虚拟现实（VR）、增强现实（AR）、区块链、人工智能等多种技术的融合。大型科技公司如Meta（原Facebook）、微软等都在积极布局元宇宙领域。然而，元宇宙的发展也面临着技术标准不统一、隐私安全、数字鸿沟等挑战。未来，元宇宙有望改变人们的生活和工作方式，但需要建立相应的法律和伦理框架来规范其发展。"
    },
    {
        "title": "可再生能源的发展趋势",
        "content": "随着全球对气候变化的关注日益增加，可再生能源的发展成为实现碳中和目标的关键。太阳能、风能、水能、生物质能等可再生能源技术不断进步，成本持续下降。近年来，全球可再生能源装机容量快速增长，特别是太阳能和风能。储能技术的发展也为可再生能源的间歇性问题提供了解决方案。智能电网和能源互联网技术的应用，提高了能源系统的效率和灵活性。然而，可再生能源的大规模发展仍面临着电网基础设施升级、能源存储成本、政策支持等挑战。未来，可再生能源有望成为全球能源结构的主体，推动能源转型和可持续发展。"
    }
]

def summarize_content(content):
    """简单的内容总结函数"""
    time.sleep(2)  # 模拟总结过程
    
    # 提取关键句子（这里使用简单的句号分割，实际应用中可以使用更复杂的NLP技术）
    sentences = re.split(r'(?<=[。.!?])\s+', content)
    
    # 如果句子数量较少，直接返回原文
    if len(sentences) <= 3:
        return content
    
    # 简单选择开头和结尾的句子作为摘要
    summary = " ".join(sentences[:2] + sentences[-1:])
    
    # 添加总结标记
    summary = f"【内容总结】\n{summary}\n\n【总结说明】本总结基于原文的关键信息提取，保留了核心观点和结论。"
    
    return summary

def call_deepseek_api(messages):
    """调用DeepSeek大模型API"""
    if not DEEPSEEK_API_KEY:
        return "❌ DeepSeek API密钥密钥未配置，请在代码中设置API密钥。"
    
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048
        }
        
        print(f"📤 调用DeepSeek API: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            return f"❌ DeepSeek API返回空结果: {json.dumps(result, ensure_ascii=False)}"
            
    except requests.exceptions.RequestException as e:
        error_msg = f"❌ DeepSeek API请求失败: {e}"
        if hasattr(e, 'response') and e.response:
            try:
                error_detail = e.response.json()
                error_msg += f"\n详细错误: {json.dumps(error_detail, ensure_ascii=False)}"
            except:
                error_msg += f"\n响应内容: {e.response.text[:500]}"
        return error_msg
    except Exception as e:
        return f"❌ DeepSeek API调用异常: {e}"

def summarize_with_deepseek(selected_contents):
    """使用DeepSeek大模型总结选中的内容"""
    if not selected_contents:
        return "请先选择至少一个搜索结果。"
    
    try:
        # 构建提示词
        system_prompt = """你是一个专业的内容总结助手。请基于提供的搜索结果，撰写一份全面、准确、简洁的总结。
要求：
1. 总结所有关键信息和核心观点
2. 保持客观的中立态度
3. 使用清晰的结构和逻辑
4. 避免冗余信息，突出重点
5. 使用Markdown格式进行排版"""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加所有选中的内容
        for i, item in enumerate(selected_contents):
            title = item.get("title", f"结果 {i+1}")
            content = item.get("full_content", item.get("content", "无内容"))
            
            # 构建用户消息
            user_message = f"## 搜索结果 {i+1}: {title}\n\n{content}"
            messages.append({"role": "user", "content": user_message})
        
        # 添加总结请求
        messages.append({"role": "user", "content": "请基于以上所有搜索结果，撰写一份综合总结。"})
        
        # 调用DeepSeek API
        print(f"📝 正在使用DeepSeek大模型总结 {len(selected_contents)} 个搜索结果...")
        summary = call_deepseek_api(messages)
        
        return summary
        
    except Exception as e:
        print(f"❌ DeepSeek总结过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ 总结过程中出现错误: {str(e)}"

def download_markdown(title, content):
    """生成Markdown格式的下载内容"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    markdown_content = f"""# {title}

## 内容总结

{content}

---

*本文件由Gradio搜索总结助手生成*  
*生成时间: {timestamp}*
"""
    
    return markdown_content

def download_summary(selected_results, content):
    """下载总结内容"""
    if not selected_results or not content:
        return None
    
    # 如果是多个标题，创建一个综合标题
    if len(selected_results) > 1:
        title = "多个搜索结果总结"
    elif len(selected_results) == 1:
        title = selected_results[0]
    else:
        title = "搜索结果总结"
    
    markdown_content = download_markdown(title, content)
    return gr.File.update(value=markdown_content, visible=True, label="下载总结文件")

def get_selected_contents(selected_titles, search_results):
    """从选中的标题中获取完整内容"""
    if not selected_titles or not search_results:
        return []
    
    selected_contents = []
    for title in selected_titles:
        for item in search_results:
            if item["title"] == title:
                selected_contents.append(item)
                break
    
    return selected_contents

def summarize_selected_contents(selected_titles, search_results):
    """总结选中的内容"""
    selected_contents = get_selected_contents(selected_titles, search_results)
    
    if not selected_contents:
        return "请先选择至少一个搜索结果。"
    
    # 如果只选中了一个结果，直接总结
    if len(selected_contents) == 1:
        return summarize_content(selected_contents[0]["content"])
    
    # 如果选中了多个结果，分别总结后合并
    summaries = []
    for i, item in enumerate(selected_contents):
        summary = summarize_content(item["content"])
        summaries.append(f"## 结果 {i+1}: {item['title']}\n\n{summary}")
    
    return "\n\n---\n\n".join(summaries)

def format_results_for_page(page_num):
    """格式化指定页的结果为卡片式HTML"""
    if not global_state["total_results"]:
        return "<div class='no-results'>未找到相关结果，请尝试其他关键词。</div>"
    
    # 计算当前页的结果范围
    start_idx = (page_num - 1) * global_state["items_per_page"]
    end_idx = start_idx + global_state["items_per_page"]
    current_results = global_state["total_results"][start_idx:end_idx]
    
    # 格式化结果为卡片式HTML
    cards_html = []
    for i, result in enumerate(current_results):
        title = result["title"]
        content = result["content"]
        url = result.get("url", "")
        
        # 截断超过200字符的内容
        if len(content) > 200:
            snippet = content[:200] + "..."
        else:
            snippet = content
        
        # 创建卡片HTML
        card_html = f"""
        <div class="search-card" id="result-{i}">
            <div class="search-card-checkbox">
                <input type="checkbox" id="checkbox-{i}" class="result-checkbox" data-title="{title}">
            </div>
            <div class="search-card-content">
                <div class="search-card-title">
                    {f'<a href="{url}" target="_blank" class="result-title-link" title="在新窗口打开">{title}</a>' if url else f'<label for="checkbox-{i}" class="result-title">{title}</label>'}
                </div>
                <div class="search-card-snippet">
                    {snippet}
                </div>
                {f'<div class="search-card-url"><a href="{url}" target="_blank" class="result-url">查看原文</a></div>' if url else ''}
            </div>
        </div>
        """
        cards_html.append(card_html)
    
    return f"""
    <div class="search-results-container">
        {"".join(cards_html)}
    </div>
    
    <script>
        // 处理复选框点击事件
        document.addEventListener('DOMContentLoaded', function() {{
            const checkboxes = document.querySelectorAll('.result-checkbox');
            checkboxes.forEach(checkbox => {{
                checkbox.addEventListener('change', function() {{
                    const title = this.getAttribute('data-title');
                    const isChecked = this.checked;
                    
                    // 获取当前选中的结果
                    let selectedResults = gradioApp().getState('selected_results');
                    if (!selectedResults) {{
                        selectedResults = [];
                    }}
                    
                    // 更新选中的结果
                    if (isChecked) {{
                        // 添加到选中列表
                        if (!selectedResults.includes(title)) {{
                            selectedResults.push(title);
                        }}
                    }} else {{
                        // 从选中列表中移除
                        selectedResults = selectedResults.filter(t => t !== title);
                    }}
                    
                    // 更新状态
                    gradioApp().setState('selected_results', selectedResults);
                }});
            }});
        }});
    </script>
    """

def perform_search(query):
    """执行搜索并返回结果"""
    try:
        # 使用全局状态
        global global_state
        
        # 执行搜索
        if BAIDU_API_KEY :
            results = search_function(query)
        else:
            # 使用模拟数据
            results = mock_results
            print("⚠️ 使用模拟数据，因为百度API密钥未配置")
        
        # 更新全局状态
        global_state["total_results"] = results
        global_state["current_page"] = 1
        global_state["search_results"] = results
        
        # 格式化当前页结果为卡片式HTML
        cards_html = format_results_for_page(1)
        
        # 获取分页信息
        total_pages = get_total_pages()
        
        # 返回结果
        return (
            cards_html, 
            gr.update(visible=True), 
            gr.update(visible=DEEPSEEK_API_KEY != ""),  # 只有配置了API密钥才显示AI总结按钮
            gr.update(value=f"第 1/{total_pages} 页"),
            gr.update(interactive=False),
            gr.update(interactive=total_pages > 1)
        )
    except Exception as e:
        print(f"❌ 搜索过程中出现错误: {e}")
        return (
            f"<div class='error-message'>搜索失败: {str(e)}</div>",
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(value="第 1/1 页"),
            gr.update(interactive=False),
            gr.update(interactive=False)
        )

def get_total_pages():
    """计算总页数"""
    if not global_state["total_results"]:
        return 1
    return (len(global_state["total_results"]) + global_state["items_per_page"] - 1) // global_state["items_per_page"]

def go_to_page(page_num):
    """跳转到指定页码"""
    try:
        global global_state
        
        total_pages = get_total_pages()
        
        if page_num < 1 or page_num > total_pages:
            return (
                gr.update(),  # 搜索结果不变
                gr.update(),  # 页码显示不变
                gr.update(),  # 上一页按钮状态不变
                gr.update()   # 下一页按钮状态不变
            )
        
        global_state["current_page"] = page_num
        cards_html = format_results_for_page(page_num)
        
        return (
            gr.update(value=cards_html),
            gr.update(value=f"第 {page_num}/{total_pages} 页"),
            gr.update(interactive=page_num > 1),
            gr.update(interactive=page_num < total_pages)
        )
    except Exception as e:
        print(f"❌ 分页过程中出现错误: {e}")
        return (
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update()
        )

def go_to_previous_page():
    """跳转到上一页"""
    return go_to_page(global_state["current_page"] - 1)

def go_to_next_page():
    """跳转到下一页"""
    return go_to_page(global_state["current_page"] + 1)

def on_select_change(selected_titles):
    """当选中结果变化时"""
    global global_state
    global_state["selected_results"] = selected_titles
    
    # 如果有选中的结果，显示总结按钮
    return gr.update(visible=len(selected_titles) > 0)

def generate_local_summary(selected_titles):
    """生成本地总结"""
    global global_state
    
    try:
        summary = summarize_selected_contents(selected_titles, global_state["search_results"])
        global_state["summary_output"] = summary
        
        return (
            gr.update(visible=True, value=summary),
            gr.update(visible=True)
        )
    except Exception as e:
        error_msg = f"❌ 总结过程中出现错误: {str(e)}"
        return (
            gr.update(visible=True, value=error_msg),
            gr.update(visible=True)
        )

def generate_deepseek_summary(selected_titles):
    """生成DeepSeek总结"""
    global global_state
    
    try:
        # 显示加载状态
        yield (
            gr.update(visible=True, value="🤖 正在使用DeepSeek大模型总结..."),
            gr.update(visible=False)
        )
        
        # 获取选中的内容
        selected_contents = get_selected_contents(selected_titles, global_state["search_results"])
        
        # 生成总结
        summary = summarize_with_deepseek(selected_contents)
        global_state["summary_output"] = summary
        
        yield (
            gr.update(visible=True, value=summary),
            gr.update(visible=True)
        )
    except Exception as e:
        error_msg = f"❌ 总结过程中出现错误: {str(e)}"
        yield (
            gr.update(visible=True, value=error_msg),
            gr.update(visible=True)
        )

def download_current_summary():
    """下载当前总结"""
    global global_state
    
    try:
        if not global_state["selected_results"] or not global_state["summary_output"]:
            return gr.update(visible=False)
        
        return download_summary(global_state["selected_results"], global_state["summary_output"])
    except Exception as e:
        print(f"❌ 下载过程中出现错误: {e}")
        return gr.update(visible=False)

def get_api_status():
    """获取API状态信息"""
    status_lines = []
    
    # 百度API状态
    if BAIDU_API_KEY :
        status_lines.append("✅ 百度千帆API已配置")
    else:
        status_lines.append("⚠️ 百度千帆API未配置，将使用模拟数据")
    
    # DeepSeek API状态
    if DEEPSEEK_API_KEY:
        status_lines.append("✅ DeepSeek大模型API已配置")
    else:
        status_lines.append("⚠️ DeepSeek大模型API未配置，AI总结功能不可用")
    
    return "\n".join(status_lines)

# 创建Gradio应用
def create_app():
    """创建Gradio应用"""
    with gr.Blocks(title="搜索与总结助手", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🔍 搜索与总结助手")
        gr.Markdown("输入关键词并回车搜索，点击标题查看详细内容并生成总结。")
        
        # 显示API状态
        api_status = gr.Markdown(
            value=get_api_status(),
            elem_id="api-status"
        )
        
        # 存储当前选中的标题
        selected_results = gr.State([])
        
        # 主容器，用于水平居中
        with gr.Column(elem_id="main-container"):
            # 搜索行：输入框 + 搜索按钮
            with gr.Row(elem_id="search-row"):
                search_input = gr.Textbox(
                    placeholder="请输入搜索关键词...",
                    lines=1,
                    label="搜索框",
                    container=False,
                    elem_id="search-input"
                )
                
                search_btn = gr.Button(
                    "🔍 搜索",
                    elem_id="search-btn"
                )
            
            # 内容容器，用于保持尺寸一致
            with gr.Column(elem_id="content-container"):
                # 搜索结果区域
                search_results = gr.HTML(
                    value="",
                    label="搜索结果",
                    elem_id="search-results"
                )
                
                # 分页控制
                with gr.Row(elem_id="pagination-controls"):
                    prev_page_btn = gr.Button(
                        "◀️ 上一页",
                        interactive=False,
                        elem_id="prev-page-btn"
                    )
                    
                    page_info = gr.Markdown(
                        value="第 1/1 页",
                        elem_id="page-info"
                    )
                    
                    next_page_btn = gr.Button(
                        "下一页 ▶️",
                        interactive=False,
                        elem_id="next-page-btn"
                    )
            
            # 总结按钮行
            with gr.Row(elem_id="summary-buttons-row"):
                summarize_local_btn = gr.Button(
                    "📝 生成总结 (本地)",
                    visible=False,
                    elem_id="summarize-local-btn"
                )
                
                summarize_deepseek_btn = gr.Button(
                    "🤖 生成总结 (AI)",
                    visible=False,
                    elem_id="summarize-deepseek-btn"
                )
            
            # 总结结果
            summary_output = gr.Textbox(
                value="",
                label="内容总结",
                lines=10,
                interactive=False,
                visible=False,
                elem_id="summary-output"
            )
            
            # 下载按钮
            download_btn = gr.Button(
                "💾 下载Markdown文件",
                visible=False,
                elem_id="download-btn"
            )
            
            download_file = gr.File(
                label="下载文件",
                visible=False
            )
        
        # 搜索功能
        search_input.submit(
            fn=perform_search,
            inputs=[search_input],
            outputs=[search_results, summarize_local_btn, summarize_deepseek_btn, page_info, prev_page_btn, next_page_btn]
        )
        
        search_btn.click(
            fn=perform_search,
            inputs=[search_input],
            outputs=[search_results, summarize_local_btn, summarize_deepseek_btn, page_info, prev_page_btn, next_page_btn]
        )
        
        # 分页功能
        prev_page_btn.click(
            fn=go_to_previous_page,
            inputs=[],
            outputs=[search_results, page_info, prev_page_btn, next_page_btn]
        )
        
        next_page_btn.click(
            fn=go_to_next_page,
            inputs=[],
            outputs=[search_results, page_info, prev_page_btn, next_page_btn]
        )
        
        # 监听选中结果变化
        selected_results.change(
            fn=on_select_change,
            inputs=[selected_results],
            outputs=[summarize_local_btn]
        )
        
        # 只有配置了DeepSeek API密钥才显示AI总结按钮
        if DEEPSEEK_API_KEY:
            selected_results.change(
                fn=on_select_change,
                inputs=[selected_results],
                outputs=[summarize_deepseek_btn]
            )
        
        # 生成总结 - 本地
        summarize_local_btn.click(
            fn=generate_local_summary,
            inputs=[selected_results],
            outputs=[summary_output, download_btn]
        )
        
        # 生成总结 - DeepSeek（只有配置了API密钥才添加这个事件）
        if DEEPSEEK_API_KEY:
            summarize_deepseek_btn.click(
                fn=generate_deepseek_summary,
                inputs=[selected_results],
                outputs=[summary_output, download_btn]
            )
        
        # 下载总结
        download_btn.click(
            fn=download_current_summary,
            inputs=[],
            outputs=[download_file]
        )
        
        # 添加一些CSS样式
        demo.load(None, None, None, js="""() => {
            const style = document.createElement('style');
            style.textContent = `
                .gradio-container {
                    max-width: 1000px !important;
                    margin-left: auto !important;
                    margin-right: auto !important;
                }
                #main-container {
                    width: 100%;
                    max-width: 1000px;
                    margin: 0 auto;
                }
                .gr-textbox {
                    margin-bottom: 10px !important;
                }
                #api-status {
                    margin-top: 5px;
                    margin-bottom: 15px;
                    font-size: 0.9em;
                    padding: 10px;
                    border-radius: 8px;
                    background-color: #f8f9fa;
                    border: 1px solid #e9ecef;
                }
                #search-row {
                    margin-bottom: 20px;
                    align-items: center;
                }
                #search-input {
                    flex-grow: 1;
                    margin-right: 10px;
                }
                #search-btn, #summarize-local-btn, #summarize-deepseek-btn {
                    white-space: nowrap;
                    margin-left: 5px;
                }
                #content-container {
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 20px;
                    min-height: 300px;
                    background-color: white;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                }
                #search-results {
                    width: 100%;
                    margin-bottom: 20px;
                }
                .search-results-container {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(100%, 1fr));
                    gap: 15px;
                }
                .search-card {
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 15px;
                    background-color: white;
                    transition: all 0.3s ease;
                    display: flex;
                    align-items: flex-start;
                }
                .search-card:hover {
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    transform: translateY(-2px);
                }
                .search-card-checkbox {
                    margin-right: 15px;
                    margin-top: 3px;
                }
                .search-card-content {
                    flex-grow: 1;
                }
                .search-card-title {
                    font-size: 1.1em;
                    font-weight: 600;
                    margin-bottom: 8px;
                }
                .result-title-link {
                    color: #1a73e8;
                    text-decoration: none;
                    transition: color 0.2s ease;
                }
                .result-title-link:hover {
                    color: #1967d2;
                    text-decoration: underline;
                }
                .result-title-link::after {
                    content: " ↗";
                    font-size: 0.8em;
                    color: #666;
                }
                .search-card-snippet {
                    color: #333;
                    font-size: 0.95em;
                    line-height: 1.5;
                    margin-bottom: 10px;
                }
                .search-card-url {
                    font-size: 0.85em;
                }
                .result-url {
                    color: #0d6628;
                    text-decoration: none;
                    transition: color 0.2s ease;
                }
                .result-url:hover {
                    color: #0a5120;
                    text-decoration: underline;
                }
                .result-url::after {
                    content: " ↗";
                    font-size: 0.8em;
                }
                .no-results {
                    text-align: center;
                    padding: 50px 0;
                    color: #666;
                    font-size: 1.1em;
                }
                .error-message {
                    text-align: center;
                    padding: 50px 0;
                    color: #dc3545;
                    font-size: 1.1em;
                }
                #summary-buttons-row {
                    margin-top: 10px;
                    margin-bottom: 10px;
                    display: flex;
                    justify-content: center;
                    gap: 10px;
                }
                #summary-output {
                    width: 100%;
                    border-radius: 8px;
                    border: 1px solid #e0e0e0;
                    background-color: white;
                }
                #download-btn {
                    margin-top: 10px;
                    width: 100%;
                }
                .result-checkbox {
                    width: 18px;
                    height: 18px;
                    cursor: pointer;
                }
                
                /* 分页控件样式 */
                #pagination-controls {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    margin-top: 20px;
                    gap: 15px;
                }
                #prev-page-btn, #next-page-btn {
                    padding: 6px 12px;
                    border-radius: 4px;
                    border: 1px solid #e0e0e0;
                    background-color: white;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                #prev-page-btn:hover:not(:disabled), #next-page-btn:hover:not(:disabled) {
                    background-color: #f5f5f5;
                    border-color: #d0d0d0;
                }
                #prev-page-btn:disabled, #next-page-btn:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }
                #page-info {
                    font-size: 0.95em;
                    color: #666;
                }
                
                @media (max-width: 768px) {
                    #search-row, #summary-buttons-row {
                        flex-direction: column;
                        align-items: stretch;
                    }
                    #search-input {
                        margin-right: 0;
                        margin-bottom: 10px;
                    }
                    #search-btn, #summarize-local-btn, #summarize-deepseek-btn {
                        width: 100%;
                        margin-left: 0;
                        margin-bottom: 5px;
                    }
                    #pagination-controls {
                        flex-direction: column;
                        gap: 10px;
                    }
                }
            `;
           document.head.appendChild(style);
    }""")
    return demo
if __name__ == "__main__":
    demo = create_app()
    demo.launch(server_name="0.0.0.0", server_port=7860)