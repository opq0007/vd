"""
测试任务处理器
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.task_orchestrator import task_orchestrator
from modules.template_manager import template_manager


async def test_tts_handler():
    """测试TTS任务处理器"""
    print("=== 测试TTS任务处理器 ===")
    
    # 获取TTS处理器
    tts_handler = task_orchestrator._task_handlers.get("tts")
    
    if not tts_handler:
        print("❌ TTS处理器未注册")
        return
    
    print("✅ TTS处理器已注册")
    
    # 测试执行
    params = {
        "text": "这是一个测试"
    }
    
    try:
        result = await tts_handler(params)
        print(f"TTS任务结果: {result}")
    except Exception as e:
        print(f"❌ TTS任务执行失败: {e}")


async def test_template_execution():
    """测试模板执行"""
    print("\n=== 测试模板执行 ===")
    
    # 重新加载模板
    template_manager.reload_templates()
    
    # 获取模板列表
    templates = template_manager.get_template_names()
    print(f"可用模板: {templates}")
    
    if "简单TTS测试" not in templates:
        print("❌ 测试模板未找到")
        return
    
    # 执行模板
    result = await task_orchestrator.execute_template(
        "简单TTS测试",
        {"text": "测试模板执行"}
    )
    
    print(f"模板执行结果: {result}")


async def main():
    """主函数"""
    await test_tts_handler()
    await test_template_execution()


if __name__ == "__main__":
    asyncio.run(main())