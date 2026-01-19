"""
测试新增的3个任务功能

测试：
1. 在视频中添加视频
2. 为2张图片生成转场效果
3. 将多个视频进行合并
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.task_handlers import task_handlers
from utils.logger import Logger


async def test_new_tasks():
    """测试新增的3个任务"""
    
    Logger.info("=" * 80)
    Logger.info("测试新增的3个任务功能")
    Logger.info("=" * 80)
    
    # 创建测试目录
    test_dir = Path("output/test_new_tasks")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    results = {}
    
    # 测试1: 在视频中添加视频
    Logger.info("\n" + "=" * 80)
    Logger.info("测试1: 在视频中添加视频")
    Logger.info("=" * 80)
    try:
        handler = task_handlers.get_handler("video_editor")
        if handler:
            result = await handler({
                "input": str(project_root / "templates" / "atm" / "out_10.mp4"),
                "video_path": str(project_root / "templates" / "atm" / "out_10.mp4"),
                "video_x": 50,
                "video_y": 50,
                "video_width": 300,
                "video_height": 300,
                "task_id": "task7",
                "job_dir": str(test_dir)
            })
            results["task7"] = result
            if result.get("success"):
                Logger.info(f"✅ 测试1成功: {result.get('output')}")
            else:
                Logger.error(f"❌ 测试1失败: {result.get('error')}")
        else:
            Logger.error("未找到 video_editor 处理器")
    except Exception as e:
        Logger.error(f"❌ 测试1失败: {e}")
        import traceback
        Logger.error(traceback.format_exc())
        results["task7"] = {"success": False, "error": str(e)}
    
    # 测试2: 为2张图片生成转场效果
    Logger.info("\n" + "=" * 80)
    Logger.info("测试2: 为2张图片生成转场效果")
    Logger.info("=" * 80)
    try:
        handler = task_handlers.get_handler("video_transition")
        if handler:
            result = await handler({
                "video1": str(project_root / "templates" / "atm" / "background.png"),
                "video2": str(project_root / "templates" / "atm" / "background.png"),
                "transition_name": "crossfade",
                "total_frames": 30,
                "fps": 30,
                "width": 640,
                "height": 640,
                "task_id": "task8",
                "job_dir": str(test_dir)
            })
            results["task8"] = result
            if result.get("success"):
                Logger.info(f"✅ 测试2成功: {result.get('output')}")
            else:
                Logger.error(f"❌ 测试2失败: {result.get('error')}")
        else:
            Logger.error("未找到 video_transition 处理器")
    except Exception as e:
        Logger.error(f"❌ 测试2失败: {e}")
        import traceback
        Logger.error(traceback.format_exc())
        results["task8"] = {"success": False, "error": str(e)}
    
    # 测试3: 将多个视频进行合并
    Logger.info("\n" + "=" * 80)
    Logger.info("测试3: 将多个视频进行合并")
    Logger.info("=" * 80)
    try:
        handler = task_handlers.get_handler("video_merge")
        if handler:
            # 使用 task7 和 task8 的输出
            if results.get("task7", {}).get("success") and results.get("task8", {}).get("success"):
                video1 = results["task7"]["output"]
                video2 = results["task8"]["output"]
                
                result = await handler({
                    "videos": f"{video1}\n{video2}",
                    "output_name": "task9_merged",
                    "task_id": "task9",
                    "job_dir": str(test_dir)
                })
                results["task9"] = result
                if result.get("success"):
                    Logger.info(f"✅ 测试3成功: {result.get('output')}")
                else:
                    Logger.error(f"❌ 测试3失败: {result.get('error')}")
            else:
                Logger.warning("⚠️  跳过测试3: 前置任务未成功")
                results["task9"] = {"success": False, "error": "前置任务未成功"}
        else:
            Logger.error("未找到 video_merge 处理器")
    except Exception as e:
        Logger.error(f"❌ 测试3失败: {e}")
        import traceback
        Logger.error(traceback.format_exc())
        results["task9"] = {"success": False, "error": str(e)}
    
    # 打印测试结果摘要
    Logger.info("\n" + "=" * 80)
    Logger.info("测试结果摘要")
    Logger.info("=" * 80)
    
    success_count = 0
    for task_name, result in results.items():
        status = "✅ 成功" if result.get("success") else "❌ 失败"
        Logger.info(f"{task_name}: {status}")
        if result.get("success"):
            success_count += 1
        else:
            Logger.error(f"  错误: {result.get('error')}")
    
    Logger.info(f"\n总计: {success_count}/{len(results)} 个测试成功")
    
    if success_count == len(results):
        Logger.info("\n" + "=" * 80)
        Logger.info("🎉 所有测试通过！")
        Logger.info("=" * 80)
    else:
        Logger.error("\n" + "=" * 80)
        Logger.error("⚠️  部分测试失败！")
        Logger.error("=" * 80)
    
    return results


if __name__ == "__main__":
    results = asyncio.run(test_new_tasks())