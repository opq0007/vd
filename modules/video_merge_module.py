"""
视频合并模块 (Video Merge Module)

提供多个视频文件合并成一个视频文件的功能。
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

from config import config
from utils.logger import Logger
from utils.file_utils import FileUtils
from utils.media_processor import MediaProcessor


class VideoMergeModule:
    """视频合并模块"""

    def __init__(self):
        self.config = config

    async def merge_videos(
        self,
        video_paths: str,
        out_basename: Optional[str] = None,
        # 任务目录配置（可选）
        job_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        合并多个视频文件

        Args:
            video_paths: 视频文件路径列表，用换行符分隔
            out_basename: 输出文件名前缀
            job_dir: 可选的任务目录，如果提供则使用该目录

        Returns:
            Dict[str, Any]: 合并结果
        """
        try:
            # 创建任务目录（如果未提供）
            if job_dir is None:
                job_dir = FileUtils.create_job_dir()
            else:
                # 确保 job_dir 存在
                job_dir = Path(job_dir)
                job_dir.mkdir(parents=True, exist_ok=True)

            out_basename = out_basename or f"merged_video_{FileUtils.generate_job_id()}"

            # 解析视频路径列表
            # 支持换行符（\n 或 \r\n）分割
            # 防呆处理：剔除前后空格和引号（包括英文双引号和中文引号）
            paths = []
            for p in video_paths.split('\n'):
                # 去除前后空格
                p = p.strip()
                if not p:
                    continue
                # 去除前后英文双引号
                if p.startswith('"') and p.endswith('"'):
                    p = p[1:-1].strip()
                # 去除前后中文引号
                if p.startswith('"') and p.endswith('"'):
                    p = p[1:-1].strip()
                if p:
                    paths.append(p)

            if not paths:
                raise ValueError("请提供至少一个视频文件路径")

            Logger.info(f"开始合并视频，共 {len(paths)} 个文件")

            # 处理每个视频路径，下载或复制到任务目录
            local_video_paths = []
            for i, path in enumerate(paths):
                try:
                    local_path = FileUtils.process_path_input(path, job_dir)
                    if local_path and local_path.exists():
                        local_video_paths.append(local_path)
                        Logger.info(f"处理视频路径 {i+1}/{len(paths)}: {path} -> {local_path}")
                    else:
                        Logger.warning(f"视频路径 {i+1}/{len(paths)} 处理失败: {path}")
                except Exception as e:
                    Logger.error(f"处理视频路径 {i+1}/{len(paths)} 时出错: {path}, 错误: {e}")

            if not local_video_paths:
                raise ValueError("没有有效的视频文件可供合并")

            # 合并视频
            output_path = job_dir / f"{out_basename}.mp4"

            # 使用 FFmpeg concat demuxer 合并视频
            await self._merge_videos_with_ffmpeg(local_video_paths, output_path)

            # 合并成功后，删除复制到任务目录的子视频文件以节省磁盘空间
            for video_path in local_video_paths:
                try:
                    if video_path.exists() and video_path != output_path:
                        video_path.unlink()
                        Logger.info(f"已删除子视频文件: {video_path}")
                except Exception as e:
                    Logger.warning(f"删除子视频文件失败: {video_path}, 错误: {e}")

            # 构建结果
            result = {
                "success": True,
                "out_basename": out_basename,
                "output_path": str(output_path),
                "input_count": len(local_video_paths),
                "input_paths": [str(p) for p in local_video_paths]
            }

            Logger.info(f"视频合并完成: {output_path}")
            return result

        except Exception as e:
            Logger.error(f"视频合并失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }

    async def _merge_videos_with_ffmpeg(
        self,
        video_paths: List[Path],
        output_path: Path
    ) -> None:
        """
        使用 FFmpeg concat demuxer 合并视频

        Args:
            video_paths: 视频文件路径列表
            output_path: 输出视频文件路径
        """
        from utils.system_utils import SystemUtils

        ffmpeg_path = SystemUtils.get_ffmpeg_path()

        # 标准化所有视频的音频参数（采样率、声道等）
        Logger.info("开始标准化视频音频参数...")
        normalized_paths = await self._normalize_video_audio(video_paths, output_path.parent)
        Logger.info(f"视频标准化完成，共 {len(normalized_paths)} 个文件")

        # 创建 concat 列表文件
        concat_list_file = output_path.parent / "concat_list.txt"

        with open(concat_list_file, 'w', encoding='utf-8') as f:
            for video_path in normalized_paths:
                # 使用绝对路径，并转义特殊字符
                abs_path = str(video_path.resolve())
                # 转义路径中的特殊字符（如单引号、反斜杠等）
                escaped_path = abs_path.replace('\\', '/')
                f.write(f"file '{escaped_path}'\n")

        Logger.info(f"创建 concat 列表文件: {concat_list_file}")

        # 构建合并命令
        cmd = [
            ffmpeg_path, "-y",
            "-f", "concat",
            "-safe", "0",  # 允许使用任意路径
            "-i", str(concat_list_file),
            "-c", "copy",  # 直接复制流，不重新编码
            str(output_path)
        ]

        Logger.info(f"执行视频合并命令: {' '.join(cmd)}")

        # 执行命令
        original_cwd = os.getcwd()
        try:
            output_dir = output_path.parent
            os.chdir(output_dir)

            SystemUtils.run_cmd(cmd)

            Logger.info(f"视频合并成功: {output_path}")

        except Exception as e:
            Logger.error(f"视频合并失败: {e}")
            raise
        finally:
            os.chdir(original_cwd)

            # 删除临时文件
            if concat_list_file.exists():
                concat_list_file.unlink()
                Logger.info(f"删除临时文件: {concat_list_file}")

            # 删除标准化后的临时文件
            for norm_path in normalized_paths:
                if norm_path != output_path and norm_path.exists():
                    norm_path.unlink()
                    Logger.info(f"删除临时标准化文件: {norm_path}")

    async def _normalize_video_audio(
        self,
        video_paths: List[Path],
        output_dir: Path
    ) -> List[Path]:
        """
        标准化所有视频的音频参数

        Args:
            video_paths: 原始视频文件路径列表
            output_dir: 输出目录

        Returns:
            List[Path]: 标准化后的视频文件路径列表
        """
        from utils.system_utils import SystemUtils

        ffmpeg_path = SystemUtils.get_ffmpeg_path()
        normalized_paths = []

        # 标准化参数：使用常见的音频参数
        target_sample_rate = 44100  # 标准采样率
        target_channels = 2  # 立体声

        for i, video_path in enumerate(video_paths):
            try:
                # 检查是否需要标准化
                needs_normalization = await self._needs_audio_normalization(video_path)

                if needs_normalization:
                    Logger.info(f"视频 {i+1}/{len(video_paths)} 需要音频标准化: {video_path.name}")

                    # 创建标准化后的文件路径
                    normalized_path = output_dir / f"normalized_{i}_{video_path.name}"

                    # 构建FFmpeg命令，重新编码音频到标准参数
                    cmd = [
                        ffmpeg_path, "-y",
                        "-i", str(video_path),
                        "-c:v", "copy",  # 视频流直接复制
                        "-c:a", "aac",  # 音频使用AAC编码
                        "-ar", str(target_sample_rate),  # 采样率
                        "-ac", str(target_channels),  # 声道数
                        "-b:a", "192k",  # 音频比特率
                        "-movflags", "+faststart",  # 优化MP4播放
                        str(normalized_path)
                    ]

                    Logger.info(f"执行音频标准化命令: {' '.join(cmd)}")

                    # 执行命令
                    original_cwd = os.getcwd()
                    try:
                        os.chdir(output_dir)
                        SystemUtils.run_cmd(cmd)
                        normalized_paths.append(normalized_path)
                        Logger.info(f"音频标准化完成: {normalized_path}")
                    finally:
                        os.chdir(original_cwd)
                else:
                    Logger.info(f"视频 {i+1}/{len(video_paths)} 不需要标准化: {video_path.name}")
                    normalized_paths.append(video_path)

            except Exception as e:
                Logger.error(f"标准化视频 {video_path} 时出错: {e}")
                # 如果标准化失败，使用原始文件
                normalized_paths.append(video_path)

        return normalized_paths

    async def _needs_audio_normalization(self, video_path: Path) -> bool:
        """
        检查视频是否需要音频标准化

        Args:
            video_path: 视频文件路径

        Returns:
            bool: 是否需要标准化
        """
        from utils.system_utils import SystemUtils

        ffmpeg_path = SystemUtils.get_ffmpeg_path()

        # 标准参数
        target_sample_rate = 44100
        target_channels = 2

        # 使用 ffprobe 获取音频信息
        cmd = [
            ffmpeg_path, "-i", str(video_path),
            "-hide_banner"
        ]

        try:
            # 在 Windows 系统上使用 GBK 编码，在其他系统上使用 UTF-8
            encoding = 'gbk' if os.name == 'nt' else 'utf-8'
            result = SystemUtils.run_cmd(cmd, capture_output=True, text=True, encoding=encoding)

            # 检查音频流
            has_audio = False
            sample_rate = None
            channels = None

            for line in result.get('stderr', '').split('\n'):
                if 'Audio:' in line:
                    has_audio = True
                    # 解析采样率
                    import re
                    rate_match = re.search(r'(\d+) Hz', line)
                    if rate_match:
                        sample_rate = int(rate_match.group(1))

                    # 解析声道数
                    if 'mono' in line.lower():
                        channels = 1
                    elif 'stereo' in line.lower():
                        channels = 2
                    else:
                        # 尝试从其他信息中提取声道数
                        channel_match = re.search(r'(\d+) channels?', line)
                        if channel_match:
                            channels = int(channel_match.group(1))

                    break

            # 如果没有音频流，不需要标准化
            if not has_audio:
                return False

            # 检查是否需要标准化
            if sample_rate and sample_rate != target_sample_rate:
                Logger.info(f"采样率不匹配: {sample_rate} Hz (目标: {target_sample_rate} Hz)")
                return True

            if channels and channels != target_channels:
                Logger.info(f"声道数不匹配: {channels} (目标: {target_channels})")
                return True

            return False

        except Exception as e:
            Logger.warning(f"检查音频标准化需求时出错: {e}")
            # 出错时保守处理，进行标准化
            return True


# 创建全局服务实例
video_merge_module = VideoMergeModule()
