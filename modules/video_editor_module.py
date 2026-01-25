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
        # 插视频配置
        video_config: Optional[Dict[str, Any]] = None,
        # 水印配置
        watermark_config: Optional[Dict[str, Any]] = None,
        out_basename: Optional[str] = None,
        # 任务目录配置（可选）
        job_dir: Optional[Path] = None,  # 可选的任务目录，如果提供则使用该目录
        # 模板目录配置（可选）
        template_dir: Optional[str] = None,  # 可选的模板目录，用于查找模板资源
        # 音频音量控制配置
        audio_volume: float = 1.0,  # 音频音量倍数（默认1.0，表示原音量）
        # 原音频保留配置
        keep_original_audio: bool = True  # 是否保留原视频音频（默认True，保留并混合；False则替换原音频）
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
            video_config: 插视频配置
            watermark_config: 水印配置
            out_basename: 输出文件名前缀
            audio_volume: 音频音量倍数（默认1.0，表示原音量；0.5表示降低一半音量；2.0表示提高一倍音量）
            keep_original_audio: 是否保留原视频音频（默认True，保留并混合；False则替换原音频）

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
                    # 先尝试直接处理路径
                    try:
                        local_input = FileUtils.process_path_input(video_path, job_dir)
                    except FileNotFoundError as e:
                        # 如果文件不存在，尝试从模板目录查找
                        if template_dir:
                            template_file = Path(template_dir) / video_path
                            if template_file.exists():
                                Logger.info(f"从模板目录找到文件: {template_file}")
                                local_input = FileUtils.process_path_input(str(template_file), job_dir)
                            else:
                                raise FileNotFoundError(f"无法找到文件: {video_path} (模板目录: {template_dir})")
                        else:
                            raise e
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
                    MediaProcessor.merge_audio_video(local_input, audio_input, merged_video_path, audio_volume=audio_volume, keep_original_audio=keep_original_audio)
                    base_video = merged_video_path
                    Logger.info(f"音视频合并成功: {merged_video_path}")
                except Exception as e:
                    Logger.error(f"音视频合并失败: {e}")
                    if local_input and FileUtils.is_video_file(str(local_input)):
                        base_video = local_input

            # 应用视频效果
            processing_success = True  # 标志变量，跟踪处理是否成功
            error_messages = []  # 收集错误信息

            if base_video and FileUtils.is_video_file(str(base_video)):
                has_effects = flower_config or image_config or video_config or watermark_config

                if has_effects:
                    temp_effects_video = job_dir / f"{out_basename}_temp_effects{base_video.suffix}"
                    video_output = job_dir / f"{out_basename}_effects{base_video.suffix}"

                    # 处理插视频配置，将视频文件复制到任务目录
                    local_video_config = None
                    if video_config and video_config.get('path'):
                        try:
                            video_to_insert_path = FileUtils.process_path_input(video_config['path'], job_dir)
                            if video_to_insert_path and video_to_insert_path.exists():
                                local_video_config = video_config.copy()
                                local_video_config['path'] = str(video_to_insert_path)
                                Logger.info(f"插视频文件已处理: {video_config['path']} -> {video_to_insert_path}")
                        except Exception as e:
                            error_msg = f"处理插视频文件失败: {str(e)}"
                            Logger.error(error_msg)
                            error_messages.append(error_msg)
                            processing_success = False  # 标记为失败

                    try:
                        VideoEffectsProcessor._current_job_id = out_basename
                        success = VideoEffectsProcessor.apply_video_effects(
                            base_video, temp_effects_video,
                            flower_config, image_config, local_video_config, watermark_config
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
                                # 在 Windows 系统上使用 GBK 编码，在其他系统上使用 UTF-8
                                encoding = 'gbk' if os.name == 'nt' else 'utf-8'
                                result = subprocess.run(probe_cmd, capture_output=True, text=True, encoding=encoding, errors='ignore')
                                # 检查 result.stderr 是否为 None
                                has_audio = result.stderr is not None and "Audio:" in result.stderr

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
                                error_msg = f"音频处理失败: {str(merge_error)}"
                                Logger.error(error_msg)
                                error_messages.append(error_msg)
                                shutil.copy2(temp_effects_video, video_output)

                            base_video = video_output
                        else:
                            error_msg = "视频效果应用失败：VideoEffectsProcessor 返回 False"
                            Logger.warning(error_msg)
                            error_messages.append(error_msg)
                            processing_success = False  # 标记为失败

                    except Exception as e:
                        error_msg = f"视频效果应用失败: {str(e)}"
                        Logger.error(error_msg)
                        import traceback
                        Logger.error(traceback.format_exc())
                        error_messages.append(error_msg)
                        processing_success = False  # 标记为失败

            # 构建结果
            result = {
                "success": processing_success,  # 使用标志变量
                "out_basename": out_basename
            }

            if base_video and base_video.exists():
                result["video_output_path"] = str(base_video)

            # 如果处理失败，添加错误信息
            if not processing_success and error_messages:
                result["error"] = "; ".join(error_messages)
                result["errors"] = error_messages  # 保留详细错误列表

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
            "video": {
                "name": "插视频",
                "description": "在视频上插入另一个视频的每一帧",
                "params": ["path", "x", "y", "width", "height", "timing_type"]
            },
            "watermark": {
                "name": "水印",
                "description": "为视频添加水印",
                "params": ["text", "font", "size", "color", "timing_type", "style"]
            }
        }


# 创建全局服务实例
video_editor_module = VideoEditorModule()
