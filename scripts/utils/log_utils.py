"""
日志工具模块。
统一日志配置，确保 logs 目录存在，输出到控制台和文件。
"""

import logging
from pathlib import Path
from datetime import datetime


def setup_logger(log_dir: Path, log_name: str = "run") -> logging.Logger:
    """初始化日志记录器，同时输出到控制台和日志文件。"""
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{log_name}_{timestamp}.log"

    logger = logging.getLogger(log_name)
    logger.setLevel(logging.INFO)

    # 避免重复添加 handler（当脚本被多次 import 时）
    if logger.handlers:
        return logger

    # 文件 handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)

    # 控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "[%(levelname)-5s] %(message)s"
    )
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
