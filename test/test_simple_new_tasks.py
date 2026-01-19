"""
简单测试新增的3个任务功能

只测试任务处理器是否正确注册和基本功能是否可用
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.task_handlers import task_handlers
from utils.logger import Logger


def test_task_handlers():
    """测试任务处理器是否正确注册"""
    
    Logger.info("=" * 80)
    Logger.info("测试任务处理器注册情况")
    Logger.info("=" * 80)
    
    # 获取所有可用的任务处理器
    available_handlers = task_handlers.get_available_handlers()
    
    Logger.info(f"可用的任务处理器数量: {len(available_handlers)}")
    Logger.info("任务处理器列表:")
    for task_type, description in available_handlers.items():
        Logger.info(f"  - {task_type}: {description}")
    
    # 检查新增的3个任务处理器
    required_handlers = ["video_editor", "video_transition", "video_merge"]
    
    Logger.info("\n" + "=" * 80)
    Logger.info("检查新增的3个任务处理器")
    Logger.info("=" * 80)
    
    all_available = True
    for handler_type in required_handlers:
        handler = task_handlers.get_handler(handler_type)
        if handler:
            Logger.info(f"✅ {handler_type}: 已注册")
        else:
            Logger.error(f"❌ {handler_type}: 未注册")
            all_available = False
    
    if all_available:
        Logger.info("\n" + "=" * 80)
        Logger.info("🎉 所有新增任务处理器已正确注册！")
        Logger.info("=" * 80)
    else:
        Logger.error("\n" + "=" * 80)
        Logger.error("⚠️  部分任务处理器未注册！")
        Logger.error("=" * 80)
    
    return all_available


if __name__ == "__main__":
    result = test_task_handlers()
    sys.exit(0 if result else 1)