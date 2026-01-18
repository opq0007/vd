"""
测试扩展模板功能

测试模板中的新任务：
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

from modules.task_orchestrator import task_orchestrator
from utils.logger import Logger


async def test_template_extended():
    """测试扩展模板功能"""
    
    Logger.info("=" * 80)
    Logger.info("开始测试扩展模板功能")
    Logger.info("=" * 80)
    
    # 准备测试参数
    parameters = {
        "username": "测试用户",
        "age": 6,
        "theme_text": "生日快乐",
        "tts_text": "祝你生日快乐！希望你每天都能开心快乐！",
        "user_images": [
            str(project_root / "templates" / "atm" / "background.png"),
            str(project_root / "templates" / "atm" / "background.png")
        ],
        "insert_video": str(project_root / "templates" / "atm" / "out_10.mp4"),
        "transition_images": [
            str(project_root / "templates" / "atm" / "background.png"),
            str(project_root / "templates" / "atm" / "background.png")
        ]
    }
    
    Logger.info(f"测试参数: {parameters}")
    
    # 定义进度回调函数
    async def progress_callback(progress_info):
        task_id = progress_info.get("task_id")
        task_name = progress_info.get("task_name")
        progress = progress_info.get("progress", 0)
        status = progress_info.get("status", "unknown")
        
        status_emoji = "✅" if status == "completed" else "❌" if status == "failed" else "⏳"
        Logger.info(f"{status_emoji} 任务进度: {task_name} ({task_id}) - {progress:.1%} - {status}")
        
        if status == "failed":
            error = progress_info.get("error", "未知错误")
            Logger.error(f"任务失败: {error}")
    
    try:
        # 执行模板
        Logger.info("开始执行模板: 奥特曼生日祝福")
        result = await task_orchestrator.execute_template(
            template_name="奥特曼生日祝福",
            parameters=parameters,
            progress_callback=progress_callback
        )
        
        Logger.info("=" * 80)
        Logger.info("模板执行完成")
        Logger.info("=" * 80)
        
        # 打印结果摘要
        Logger.info(f"模板名称: {result.get('template_name')}")
        Logger.info(f"总任务数: {result.get('total_tasks')}")
        Logger.info(f"完成任务数: {result.get('completed_tasks')}")
        
        # 打印每个任务的输出
        task_outputs = result.get("task_outputs", {})
        Logger.info("\n任务输出详情:")
        for task_id, output in task_outputs.items():
            Logger.info(f"  {task_id}: {output}")
        
        # 检查关键任务是否成功
        critical_tasks = ["task7", "task8", "task9"]
        all_critical_success = True
        
        for task_id in critical_tasks:
            if task_id in task_outputs:
                task_result = task_outputs[task_id]
                if task_result.get("success"):
                    Logger.info(f"✅ {task_id} 执行成功")
                    if "output" in task_result:
                        Logger.info(f"   输出文件: {task_result['output']}")
                else:
                    Logger.error(f"❌ {task_id} 执行失败: {task_result.get('error')}")
                    all_critical_success = False
            else:
                Logger.warning(f"⚠️  {task_id} 未找到输出")
                all_critical_success = False
        
        if all_critical_success:
            Logger.info("\n" + "=" * 80)
            Logger.info("✅ 所有关键任务执行成功！")
            Logger.info("=" * 80)
        else:
            Logger.error("\n" + "=" * 80)
            Logger.error("❌ 部分关键任务执行失败！")
            Logger.error("=" * 80)
        
        return result
        
    except Exception as e:
        Logger.error(f"测试失败: {e}")
        import traceback
        Logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def test_individual_handlers():
    """测试各个任务处理器"""
    
    Logger.info("=" * 80)
    Logger.info("开始测试各个任务处理器")
    Logger.info("=" * 80)
    
    from modules.task_handlers import task_handlers
    from utils.file_utils import FileUtils
    
    # 创建测试目录
    test_dir = Path("output/test_individual_handlers")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    results = {}
    
    # 测试1: 视频编辑器（添加视频）
    Logger.info("\n测试1: 视频编辑器（添加视频）")
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
                "task_id": "test_video_insert",
                "job_dir": str(test_dir)
            })
            results["video_editor_insert"] = result
            Logger.info(f"结果: {result}")
        else:
            Logger.error("未找到 video_editor 处理器")
    except Exception as e:
        Logger.error(f"测试失败: {e}")
        results["video_editor_insert"] = {"success": False, "error": str(e)}
    
    # 测试2: 视频转场（图片转场）
    Logger.info("\n测试2: 视频转场（图片转场）")
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
                "task_id": "test_transition",
                "job_dir": str(test_dir)
            })
            results["transition"] = result
            Logger.info(f"结果: {result}")
        else:
            Logger.error("未找到 video_transition 处理器")
    except Exception as e:
        Logger.error(f"测试失败: {e}")
        results["transition"] = {"success": False, "error": str(e)}
    
    # 测试3: 视频合并
    Logger.info("\n测试3: 视频合并")
    try:
        handler = task_handlers.get_handler("video_merge")
        if handler:
            result = await handler({
                "videos": f"{project_root / 'templates' / 'atm' / 'out_10.mp4'}\n{project_root / 'templates' / 'atm' / 'out_10.mp4'}",
                "output_name": "test_merged",
                "task_id": "test_merge",
                "job_dir": str(test_dir)
            })
            results["video_merge"] = result
            Logger.info(f"结果: {result}")
        else:
            Logger.error("未找到 video_merge 处理器")
    except Exception as e:
        Logger.error(f"测试失败: {e}")
        results["video_merge"] = {"success": False, "error": str(e)}
    
    # 打印测试结果摘要
    Logger.info("\n" + "=" * 80)
    Logger.info("测试结果摘要")
    Logger.info("=" * 80)
    for test_name, result in results.items():
        status = "✅ 成功" if result.get("success") else "❌ 失败"
        Logger.info(f"{test_name}: {status}")
        if not result.get("success"):
            Logger.error(f"  错误: {result.get('error')}")
    
    return results


if __name__ == "__main__":
    # 运行单个处理器测试
    Logger.info("运行单个处理器测试...")
    individual_results = asyncio.run(test_individual_handlers())
    
    # 运行完整模板测试
    Logger.info("\n运行完整模板测试...")
    template_result = asyncio.run(test_template_extended())
