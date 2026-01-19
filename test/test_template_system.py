"""
测试优化后的模板系统
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.template_manager import template_manager
from modules.task_orchestrator import task_orchestrator


async def test_template_loading():
    """测试模板加载"""
    print("=== 测试模板加载 ===")
    
    # 重新加载模板
    template_manager.reload_templates()
    
    # 获取所有模板
    templates = template_manager.get_template_names()
    print(f"可用模板: {templates}")
    
    # 检查每个模板的元数据
    for template_name in templates:
        template = template_manager.get_template(template_name)
        print(f"\n模板: {template_name}")
        print(f"  - 操作模板对象: {template.get('character', 'N/A')}")
        print(f"  - 主题: {template.get('theme', 'N/A')}")
        print(f"  - 模板文件: {template.get('template_file', 'N/A')}")
        print(f"  - 模板目录: {template.get('template_dir', 'N/A')}")
        print(f"  - 任务数量: {len(template.get('tasks', []))}")


async def test_template_execution():
    """测试模板执行"""
    print("\n=== 测试模板执行 ===")
    
    # 测试奥特曼生日模板
    print("\n测试: 奥特曼生日祝福")
    result = await task_orchestrator.execute_template(
        "奥特曼生日祝福",
        {
            "username": "小明",
            "age": 6,
            "theme_text": "生日快乐",
            "tts_text": "小明生日快乐！",
            "user_images": []
        }
    )
    
    print(f"执行结果: {result}")


async def main():
    """主函数"""
    await test_template_loading()
    await test_template_execution()


if __name__ == "__main__":
    asyncio.run(main())
