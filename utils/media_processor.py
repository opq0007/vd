"""
媒体处理工具类

提供音频提取、视频合并、文件下载等媒体处理功能。
"""

import os
import re
import requests
import subprocess
from pathlib import Path
from typing import Tuple

from utils.system_utils import SystemUtils
from utils.logger import Logger


class MediaProcessor:
    """媒体处理工具类"""

    @staticmethod
    def extract_audio(input_path: Path, output_path: Path, sample_rate: int = 16000):
        """
        从视频或音频文件中提取音频

        Args:
            input_path: 输入文件路径
            output_path: 输出音频文件路径
            sample_rate: 采样率
        """
        input_path = Path(input_path).resolve()
        output_path = Path(output_path).resolve()

        ffmpeg_path = SystemUtils.get_ffmpeg_path()

        cmd = [
            ffmpeg_path, "-y", "-i", str(input_path),
            "-ac", "1", "-ar", str(sample_rate),
            "-vn", "-f", "wav", str(output_path)
        ]
        SystemUtils.run_cmd(cmd)

    @staticmethod
    def download_from_url(url: str, output_path: Path, timeout: int = 60):
        """
        从URL下载文件

        Args:
            url: 文件URL
            output_path: 输出文件路径
            timeout: 超时时间（秒）
        """
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        Logger.info(f"Downloading URL: {url} to {output_path}")
        try:
            with requests.get(url, stream=True, timeout=timeout) as r:
                r.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            Logger.info(f"Downloaded successfully: {output_path}")
        except Exception as e:
            Logger.error(f"Failed to download {url}: {e}")
            raise

    @staticmethod
    def mux_softsub(video_path: Path, srt_path: Path, output_path: Path):
        """
        生成软字幕视频（将SRT字幕嵌入到视频文件中）

        Args:
            video_path: 视频文件路径
            srt_path: SRT字幕文件路径
            output_path: 输出视频文件路径
        """
        video_path = Path(video_path).resolve()
        srt_path = Path(srt_path).resolve()
        output_path = Path(output_path).resolve()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_path = SystemUtils.get_ffmpeg_path()

        try:
            original_cwd = os.getcwd()
            output_dir = output_path.parent
            os.chdir(output_dir)

            video_rel = os.path.relpath(video_path, output_dir)
            srt_rel = os.path.relpath(srt_path, output_dir)
            output_rel = output_path.name

            video_rel = video_rel.replace('\\', '/')
            srt_rel = srt_rel.replace('\\', '/')

            video_ext = video_path.suffix.lower()

            if os.name == 'nt':
                if video_ext in ['.mp4', '.mov', '.m4v']:
                    cmd = f'{ffmpeg_path} -y -i "{video_rel}" -i "{srt_rel}" -c:v copy -c:a copy -c:s mov_text -metadata:s:s:0 language=chi -disposition:s:0 default -map 0:v -map 0:a? -map 1:s "{output_rel}"'
                elif video_ext in ['.mkv']:
                    cmd = f'{ffmpeg_path} -y -i "{video_rel}" -i "{srt_rel}" -c:v copy -c:a copy -c:s srt -metadata:s:s:0 language=chi -disposition:s:0 default -map 0:v -map 0:a? -map 1:s "{output_rel}"'
                else:
                    cmd = f'{ffmpeg_path} -y -i "{video_rel}" -i "{srt_rel}" -c:v copy -c:a copy -c:s ass -metadata:s:s:0 language=chi -disposition:s:0 default -map 0:v -map 0:a? -map 1:s "{output_rel}"'

                proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if proc.returncode != 0:
                    raise RuntimeError(
                        f"Command failed: {cmd}\n"
                        f"stdout:\n{proc.stdout}\n"
                        f"stderr:\n{proc.stderr}"
                    )
            else:
                if video_ext in ['.mp4', '.mov', '.m4v']:
                    cmd = [
                        ffmpeg_path, "-y", "-i", video_rel, "-i", srt_rel,
                        "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text",
                        "-metadata:s:s:0", "language=chi",
                        "-disposition:s:0", "default",
                        "-map", "0:v", "-map", "0:a?", "-map", "1:s",
                        output_rel
                    ]
                elif video_ext in ['.mkv']:
                    cmd = [
                        ffmpeg_path, "-y", "-i", video_rel, "-i", srt_rel,
                        "-c:v", "copy", "-c:a", "copy", "-c:s", "srt",
                        "-metadata:s:s:0", "language=chi",
                        "-disposition:s:0", "default",
                        "-map", "0:v", "-map", "0:a?", "-map", "1:s",
                        output_rel
                    ]
                else:
                    cmd = [
                        ffmpeg_path, "-y", "-i", video_rel, "-i", srt_rel,
                        "-c:v", "copy", "-c:a", "copy", "-c:s", "ass",
                        "-metadata:s:s:0", "language=chi",
                        "-disposition:s:0", "default",
                        "-map", "0:v", "-map", "0:a?", "-map", "1:s",
                        output_rel
                    ]

                SystemUtils.run_cmd(cmd)

            Logger.info(f"软字幕视频生成成功: {output_path}")

        except Exception as e:
            Logger.error(f"软字幕视频生成失败: {e}")
            raise
        finally:
            os.chdir(original_cwd)

    @staticmethod
    def get_video_width(ffmpeg_path: str, video_path: str) -> int:
        """
        获取视频宽度

        Args:
            ffmpeg_path: FFmpeg路径
            video_path: 视频文件路径

        Returns:
            int: 视频宽度
        """
        probe_cmd = [ffmpeg_path, "-i", video_path, "-hide_banner"]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        video_width = 720

        for line in probe_result.stderr.split('\n'):
            if 'Video:' in line and 'x' in line:
                match = re.search(r'(\d{3,5})x(\d{3,5})', line)
                if match:
                    video_width = int(match.group(1))
                break

        return video_width

    @staticmethod
    def burn_hardsub(video_path: Path, srt_path: Path, output_path: Path):
        """
        生成硬字幕视频（将字幕直接烧录到视频画面中）

        Args:
            video_path: 视频文件路径
            srt_path: SRT字幕文件路径
            output_path: 输出视频文件路径
        """
        from utils.subtitle_generator import SubtitleGenerator

        video_path = Path(video_path).resolve()
        srt_path = Path(srt_path).resolve()
        output_path = Path(output_path).resolve()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_path = SystemUtils.get_ffmpeg_path()

        try:
            if not srt_path.exists():
                raise RuntimeError(f"字幕文件不存在: {srt_path}")

            video_width = MediaProcessor.get_video_width(ffmpeg_path, str(video_path))
            print(f"video_width: {video_width}")

            platform_suffix = "_windows" if os.name == 'nt' else "_linux"
            temp_ass_path = SubtitleGenerator.create_ass_subtitle(
                srt_path, output_path.parent, video_width, platform_suffix
            )

            if not temp_ass_path.exists():
                raise RuntimeError(f"ASS字幕文件创建失败: {temp_ass_path}")

            video_abs = str(video_path.resolve())
            output_abs = str(output_path.resolve())
            temp_ass_abs = str(temp_ass_path.resolve())

            print(f"输入视频: {video_abs}")
            print(f"ASS字幕: {temp_ass_abs}")
            print(f"输出视频: {output_abs}")

            original_cwd = os.getcwd()

            try:
                output_dir = output_path.parent
                os.chdir(output_dir)

                video_rel = video_path.name
                output_rel = output_path.name
                temp_ass_rel = temp_ass_path.name

                # 读取 ASS 文件内容进行调试
                with open(temp_ass_path, 'r', encoding='utf-8') as f:
                    ass_content = f.read()
                Logger.info(f"ASS 文件内容（前500字符）:\n{ass_content[:500]}")

                cmd = [
                    ffmpeg_path, "-y", "-i", video_rel,
                    "-vf", f"ass={temp_ass_rel}",
                    "-c:a", "copy", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-movflags", "+faststart",
                    output_rel
                ]
                Logger.info(f"执行 FFmpeg 命令: {' '.join(cmd)}")
                print(f"执行命令: {' '.join(cmd)}")
                proc = subprocess.run(cmd, capture_output=True, text=True)
                Logger.info(f"FFmpeg stdout: {proc.stdout}")
                if proc.stderr:
                    Logger.info(f"FFmpeg stderr: {proc.stderr}")
            finally:
                os.chdir(original_cwd)

            if proc.returncode != 0:
                raise RuntimeError(
                    f"Command failed: {' '.join(cmd) if isinstance(cmd, list) else cmd}\n"
                    f"stdout:\n{proc.stdout}\n"
                    f"stderr:\n{proc.stderr}"
                )
        finally:
            if 'temp_ass_path' in locals() and temp_ass_path.exists():
                temp_ass_path.unlink()

            Logger.info(f"硬字幕视频生成成功: {output_path}")

    @staticmethod
    def get_media_duration(file_path: Path) -> float:
        """
        获取媒体文件的时长（秒）

        Args:
            file_path: 媒体文件路径

        Returns:
            float: 媒体时长（秒）
        """
        file_path = Path(file_path).resolve()
        ffmpeg_path = SystemUtils.get_ffmpeg_path()

        cmd = [
            ffmpeg_path, "-i", str(file_path), "-f", "null", "-"
        ]

        try:
            result = SystemUtils.run_cmd(cmd)
            duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})', result)
            if duration_match:
                hours, minutes, seconds = map(float, duration_match.groups())
                return hours * 3600 + minutes * 60 + seconds
            else:
                Logger.warning(f"无法获取媒体时长: {file_path}")
                return 0.0
        except Exception as e:
            Logger.error(f"获取媒体时长失败: {e}")
            return 0.0

    @staticmethod
    def merge_audio_video(video_path: Path, audio_path: Path, output_path: Path):
        """
        将音频合并到视频中（替换原音频）

        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径
            output_path: 输出视频文件路径
        """
        video_path = Path(video_path).resolve()
        audio_path = Path(audio_path).resolve()
        output_path = Path(output_path).resolve()

        ffmpeg_path = SystemUtils.get_ffmpeg_path()

        original_cwd = os.getcwd()

        try:
            output_dir = output_path.parent
            os.chdir(output_dir)

            video_rel = os.path.relpath(video_path, output_dir)
            audio_rel = os.path.relpath(audio_path, output_dir)
            output_rel = output_path.name

            video_rel = video_rel.replace('\\', '/')
            audio_rel = audio_rel.replace('\\', '/')

            cmd = [
                ffmpeg_path, "-y", "-i", video_rel, "-i", audio_rel,
                "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0",
                "-shortest", output_rel
            ]

            SystemUtils.run_cmd(cmd)
            Logger.info(f"音视频合并成功: {output_path}")

        except Exception as e:
            Logger.error(f"音视频合并失败: {e}")
            raise
        finally:
            os.chdir(original_cwd)
