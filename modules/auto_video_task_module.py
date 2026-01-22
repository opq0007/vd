"""
全自动视频生成任务模块（优化版）

复用任务编排能力，基于模板系统实现灵活的视频生成流程。
"""

import asyncio
from typing import Dict, Any, Optional, Callable

from config import config
from utils.logger import Logger
from modules.template_manager import template_manager
from modules.task_orchestrator import task_orchestrator


class AutoVideoTaskModule:
    """全自动视频生成任务模块（基于模板系统）"""

    def __init__(self):
        self.config = config

    async def generate_video_from_topic(
        self,
        topic: str,
        # 视频配置
        video_size: str = "portrait",
        duration: int = 60,
        fps: int = 25,
        # LLM 配置
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        # ComfyUI 配置
        comfyui_server_url: Optional[str] = None,
        image_workflow_path: Optional[str] = None,
        video_workflow_path: Optional[str] = None,
        # TTS 配置
        tts_feat_id: Optional[str] = None,
        tts_prompt_wav: Optional[str] = None,
        tts_prompt_text: Optional[str] = None,
        # 背景音乐配置
        background_music: Optional[str] = None,
        background_music_volume: float = 0.3,
        # 模板配置
        template_name: Optional[str] = None,
        # 进度回调
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        根据主题自动生成视频（基于模板系统）

        Args:
            topic: 视频主题
            video_size: 视频尺寸
            duration: 视频总时长（秒）
            fps: 帧率
            llm_model: LLM 模型名称
            llm_api_key: LLM API Key
            comfyui_server_url: ComfyUI 服务器地址
            image_workflow_path: 图片生成工作流路径
            video_workflow_path: 视频生成工作流路径
            tts_feat_id: TTS 预编码特征 ID
            tts_prompt_wav: TTS 参考音频路径
            tts_prompt_text: TTS 参考文本
            background_music: 背景音乐路径
            background_music_volume: 背景音乐音量
            template_name: 视频模板名称
            progress_callback: 进度回调函数

        Returns:
            Dict[str, Any]: 生成结果
        """
        try:
            # 使用默认模板名称
            if not template_name:
                template_name = "AIGC全自动视频生成"

            # 构建参数字典
            parameters = {
                "topic": topic,
                "video_size": video_size,
                "duration": duration,
                "fps": fps,
                "llm_model": llm_model or config.ZHIPU_MODEL,
                "llm_api_key": llm_api_key or config.ZHIPU_API_KEY,
                "comfyui_server_url": comfyui_server_url or config.COMFYUI_SERVER_URL,
                "image_workflow_path": image_workflow_path or "",
                "video_workflow_path": video_workflow_path or "",
                "tts_feat_id": tts_feat_id or "",
                "tts_prompt_wav": tts_prompt_wav or "",
                "tts_prompt_text": tts_prompt_text or "",
                "background_music": background_music or "",
                "background_music_volume": background_music_volume
            }

            Logger.info(f"开始执行AIGC全自动视频生成: {topic}")
            Logger.info(f"使用模板: {template_name}")

            # 使用任务编排器执行模板
            execution_result = await task_orchestrator.execute_template(
                template_name=template_name,
                parameters=parameters,
                progress_callback=progress_callback
            )

            if not execution_result["success"]:
                raise ValueError(f"模板执行失败: {execution_result.get('error')}")

            # 从任务输出中提取最终视频
            task_outputs = execution_result["task_outputs"]
            final_video = None

            # 查找最后一个任务的输出
            for task_id in sorted(task_outputs.keys(), reverse=True):
                task_output = task_outputs[task_id]
                if "output_path" in task_output:
                    final_video = task_output["output_path"]
                    break
                elif "output_files" in task_output and task_output["output_files"]:
                    final_video = task_output["output_files"][0]
                    break

            # 提取脚本数据
            script_data = None
            if "task_generate_script" in task_outputs:
                script_data = task_outputs["task_generate_script"].get("output")

            # 兼容 UI 的期望格式
            script_info = {}
            if script_data:
                scenes = script_data.get("scenes", [])
                script_info = {
                    "scene_count": len(scenes),
                    "total_duration": sum(scene.get("duration", 0) for scene in scenes),
                    "title": script_data.get("title", ""),
                    "full_text": script_data.get("full_text", "")
                }

            return {
                "success": True,
                "topic": topic,
                "script": script_info,
                "script_data": script_data,  # 保留原始脚本数据
                "output_video": final_video,
                "task_outputs": task_outputs
            }

        except Exception as e:
            Logger.error(f"视频生成失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())

            if progress_callback:
                await progress_callback({"step": "error", "progress": 0, "message": f"视频生成失败: {str(e)}"})

            return {
                "success": False,
                "error": str(e)
            }

    def get_module_info(self) -> Dict[str, Any]:
        """
        获取模块信息

        Returns:
            Dict[str, Any]: 模块信息
        """
        return {
            "name": "Auto Video Task Module",
            "version": "3.0.0",
            "description": "全自动视频生成任务模块（基于模板系统）",
            "features": [
                "基于模板系统的灵活编排",
                "复用任务编排器能力",
                "支持AIGC自定义任务处理器",
                "避免硬编码模块调用"
            ]
        }


# 创建全局服务实例
auto_video_task_module = AutoVideoTaskModule()