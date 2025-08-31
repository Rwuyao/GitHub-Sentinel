import logging
import sys
from logging.handlers import RotatingFileHandler
import os

def setup_logger(log_level: int = logging.INFO, log_file: str = None):
    """
    配置日志系统
    
    Args:
        log_level: 日志等级，如 logging.INFO, logging.DEBUG 等
        log_file: 日志文件路径，None表示仅输出到控制台
    """
    # 获取根日志器
    logger = logging.getLogger()
    
    # 清除现有处理器（避免重复配置）
    if logger.handlers:
        logger.handlers.clear()
    
    # 设置日志等级
    logger.setLevel(log_level)
    
    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了日志文件）
    if log_file:
        try:
            # 确保日志目录存在
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            # 创建滚动日志处理器，避免单个文件过大
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,          # 最多保留5个备份
                encoding='utf-8'
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            logger.info(f"日志文件已配置: {log_file}")
        except Exception as e:
            logger.warning(f"无法配置日志文件: {str(e)}，仅使用控制台输出")

def get_logger(name: str = None) -> logging.Logger:
    """
    获取指定名称的日志器
    
    Args:
        name: 日志器名称，通常使用 __name__
        
    Returns:
        配置好的日志器实例
    """
    return logging.getLogger(name)
