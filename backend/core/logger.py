import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from core.config import settings


def setup_logger():
    # 日志格式
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 创建logger
    logger = logging.getLogger('ai_file_processing')
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # 确保目录存在
    log_dir = Path(__file__).parent.parent
    log_file = log_dir / 'app.log'

    # 文件处理器
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,  # 保留5个备份
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    return logger


# 全局logger实例
logger = setup_logger()
