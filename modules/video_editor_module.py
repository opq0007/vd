"""
视频编辑模块 (Video Editor Module)

提供花字、插图、水印等高级视频效果功能。
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

from config import config
from utils.logger import Logger
from utils.file_utils import FileUtils
from utils.video_effects import VideoEffectsProcessor


class VideoEditorModule:
    """视频编辑模块"""

    def __init__(self):
        self.config = config

    async def apply_video_effects(
        self,
        input_type: str = "upload",
        video_file: Optional[str] = None,
        video_path: Optional[str] = None,
        audio_file: Optional[str] = None,
        audio_path: Optional[str] = None,
        # 花字配置
        flower_config: Optional[Dict[str, Any]] = None,
        # 插图配置
        image_config: Optional[Dict[str, Any]] = None,
        # 水印配置
        watermark_config: Optional[Dict[str, Any]] = None,
        out_basename: Optional[str] = None,
        # 任务目录配置（可选）
        job_dir: Optional[Path] = None  # 可选的任务目录，如果提供则使用该目录
    ) -> Dict[str, Any]:
        """
        应用视频效果

        Args:
            input_type: 输入类型 (upload/path)
            video_file: 上传的视频文件
            video_path: 视频文件路径
            audio_file: 上传的音频文件
            audio_path: 音频文件路径
            flower_config: 花字配置
            image_config: 插图配置
            watermark_config: 水印配置
            out_basename: 输出文件名前缀

        Returns:
            Dict[str, Any]: 视频编辑结果
        """
        try:
            # 创建任务目录（如果未提供）
            if job_dir is None:
                job_dir = FileUtils.create_job_dir()
            else:
                # 确保 job_dir 存在
                job_dir = Path(job_dir)
                job_dir.mkdir(parents=True, exist_ok=True)

            out_basename = out_basename or f"output_{FileUtils.generate_job_id()}"

            # 处理输入文件
            local_input = None
            audio_input = None

            if input_type == "upload":
                # 处理上传文件
                if video_file:
                    # 处理元组或字符串
                    if isinstance(video_file, tuple):
                        video_file = video_file[0]
                    elif isinstance(video_file, int):
                        pass  # 跳过采样率
                    if isinstance(video_file, str):
                        video_file_path = Path(video_file)
                        local_input = job_dir / video_file_path.name
                        import shutil
                        shutil.copy2(video_file, local_input)
                elif audio_file:
                    # 处理音频文件
                    if isinstance(audio_file, tuple):
                        audio_file = audio_file[0]
                    elif isinstance(audio_file, int):
                        pass  # 跳过采样率
                    if isinstance(audio_file, str):
                        audio_file_path = Path(audio_file)
                        audio_input = job_dir / audio_file_path.name
                        import shutil
                        shutil.copy2(audio_file, audio_input)

            elif input_type == "path":
                # 处理路径输入
                if video_path:
                    local_input = FileUtils.process_path_input(video_path, job_dir)
                if audio_path:
                    audio_input = FileUtils.process_path_input(audio_path, job_dir)

            # 确定基础视频文件
            base_video = None
            if local_input and FileUtils.is_video_file(str(local_input)):
                base_video = local_input

            # 合并音视频（如果需要）
            if audio_input and local_input:
                merged_video_path = job_dir / f"{out_basename}_merged{local_input.suffix}"
                try:
                    from utils.media_processor import MediaProcessor
                    MediaProcessor.merge_audio_video(local_input, audio_input, merged_video_path)
                    base_video = merged_video_path
                    Logger.info(f"音视频合并成功: {merged_video_path}")
                except Exception as e:
                    Logger.error(f"音视频合并失败: {e}")
                    if local_input and FileUtils.is_video_file(str(local_input)):
                        base_video = local_input

            # 应用视频效果
            if base_video and FileUtils.is_video_file(str(base_video)):
                has_effects = flower_config or image_config or watermark_config

                if has_effects:
                    temp_effects_video = job_dir / f"{out_basename}_temp_effects{base_video.suffix}"
                    video_output = job_dir / f"{out_basename}_effects{base_video.suffix}"

                    try:
                        VideoEffectsProcessor._current_job_id = out_basename
                        success = VideoEffectsProcessor.apply_video_effects(
                            base_video, temp_effects_video,
                            flower_config, image_config, watermark_config
                        )
                        VideoEffectsProcessor._current_job_id = None

                        if success:
                            # 合并原始视频的音频（如果存在）
                            try:
                                from utils.system_utils import SystemUtils
                                import shutil
                                import subprocess
                                ffmpeg_path = SystemUtils.get_ffmpeg_path()
                                import os
                                original_cwd = os.getcwd()

                                output_dir = video_output.parent
                                os.chdir(output_dir)

                                base_video_rel = os.path.relpath(base_video, output_dir).replace('\\', '/')
                                temp_video_rel = temp_effects_video.name
                                output_rel = video_output.name

                                # 检查原始视频是否有音频流
                                probe_cmd = [ffmpeg_path, "-i", base_video_rel, "-hide_banner"]
                                result = subprocess.run(probe_cmd, capture_output=True, text=True)
                                has_audio = "Audio:" in result.stderr

                                if has_audio:
                                    # 有音频，合并音频和视频
                                    cmd = [
                                        ffmpeg_path, "-y",
                                        "-i", base_video_rel,
                                        "-i", temp_video_rel,
                                        "-map", "0:a:0",
                                        "-map", "1:v:0",
                                        "-c:a", "copy",
                                        "-c:v", "copy",
                                        output_rel
                                    ]
                                    SystemUtils.run_cmd(cmd)
                                    Logger.info(f"视频效果应用成功（含音频）: {video_output}")
                                else:
                                    # 没有音频，直接使用处理后的视频
                                    shutil.copy2(temp_effects_video, video_output)
                                    Logger.info(f"视频效果应用成功（无音频）: {video_output}")

                                os.chdir(original_cwd)

                            except Exception as merge_error:
                                Logger.error(f"音频处理失败: {merge_error}")
                                shutil.copy2(temp_effects_video, video_output)

                            base_video = video_output
                        else:
                            Logger.warning("视频效果应用失败")

                    except Exception as e:
                        Logger.error(f"视频效果应用失败: {e}")
                        import traceback
                        Logger.error(traceback.format_exc())

            # 构建结果
            result = {
                "success": True,
                "out_basename": out_basename
            }

            if base_video and base_video.exists():
                result["video_output_path"] = str(base_video)

            Logger.info(f"视频编辑完成: {out_basename}")
            return result

        except Exception as e:
            Logger.error(f"视频编辑失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }

    def get_available_effects(self) -> Dict[str, Any]:
        """
        获取可用的视频效果

        Returns:
            Dict[str, Any]: 视频效果信息
        """
        return {
            "flower": {
                "name": "花字",
                "description": "在视频上添加装饰性文字效果",
                "params": ["text", "font", "size", "color", "x", "y", "timing_type", "stroke_enabled", "stroke_color", "stroke_width"]
            },
            "image": {
                "name": "插图",
                "description": "在视频上插入图片",
                "params": ["path", "x", "y", "width", "height", "remove_bg", "timing_type"]
            },
            "watermark": {
                "name": "水印",
                "description": "为视频添加水印",
                "params": ["text", "font", "size", "color", "timing_type", "style"]
            }
        }


# 创建全局服务实例
video_editor_module = VideoEditorModule()
