import logging
import markdown
from typing import Optional

logger = logging.getLogger("markdown-converter")

class MarkdownConverter:
    """独立的Markdown转HTML工具类，负责格式转换和样式处理"""
    
    def __init__(self, base_css: Optional[str] = None):
        """
        初始化转换器
        
        参数:
            base_css: 自定义基础CSS样式，为None则使用默认样式
        """
        self.base_css = base_css or self._get_default_css()
    
    def _get_default_css(self) -> str:
        """获取默认CSS样式（适配主流邮箱客户端）"""
        return """
            <style>
                body { 
                    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
                    max-width: 800px; 
                    margin: 0 auto; 
                    padding: 20px;
                    color: #333;
                }
                h1, h2, h3 { 
                    color: #2c3e50; 
                    margin-top: 1.5em;
                    margin-bottom: 0.8em;
                }
                h1 { 
                    border-bottom: 2px solid #f1f1f1;
                    padding-bottom: 0.5em;
                }
                p { 
                    line-height: 1.7;
                    margin: 1em 0;
                }
                ul, ol { 
                    margin: 1em 0;
                    padding-left: 2em;
                }
                li { 
                    margin: 0.5em 0;
                    line-height: 1.6;
                }
                code { 
                    background: #f8f8f8;
                    padding: 2px 5px;
                    border-radius: 3px;
                    font-family: monospace;
                }
                pre { 
                    background: #f8f8f8;
                    padding: 15px;
                    border-radius: 5px;
                    overflow-x: auto;
                    margin: 1em 0;
                }
                pre code { 
                    padding: 0;
                }
                blockquote { 
                    border-left: 3px solid #ddd;
                    padding-left: 15px;
                    margin: 1em 0;
                    color: #666;
                }
                table { 
                    border-collapse: collapse;
                    width: 100%;
                    margin: 1em 0;
                }
                th, td { 
                    border: 1px solid #eee;
                    padding: 10px;
                    text-align: left;
                }
                th { 
                    background-color: #f8f8f8;
                }
                .footer { 
                    margin-top: 2em;
                    padding-top: 1em;
                    border-top: 1px solid #eee;
                    color: #777;
                    font-size: 0.9em;
                }
            </style>
        """
    
    def add_custom_css(self, custom_css: str) -> None:
        """添加自定义CSS样式（会覆盖默认样式中相同的规则）"""
        self.base_css += "\n" + custom_css
    
    def convert(self, md_text: str, add_header_footer: bool = True) -> str:
        """
        将Markdown文本转换为HTML
        
        参数:
            md_text: Markdown格式的文本
            add_header_footer: 是否添加HTML头部和尾部
            
        返回:
            转换后的HTML字符串
        """
        if not md_text:
            logger.warning("转换内容为空")
            return ""
        
        try:
            # 转换Markdown为HTML主体内容
            html_body = markdown.markdown(md_text)
            
            # 如果需要完整HTML文档，则添加头部和样式
            if add_header_footer:
                full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Markdown Content</title>
    {self.base_css}
</head>
<body>
    {html_body}
</body>
</html>"""
                return full_html
            else:
                return html_body
                
        except Exception as e:
            logger.error(f"Markdown转换失败: {str(e)}")
            return f"<p>转换内容时发生错误: {str(e)}</p>"
