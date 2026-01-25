"""
媒体处理工具类

提供音频提取、视频合并、文件下载等媒体处理功能。
"""

import os
import re
import requests
import subprocess
from pathlib import Path
from typing import Tuple, Optional

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

        # 首先检查输入文件是否包含音频流
        probe_cmd = [ffmpeg_path, "-i", str(input_path), "-hide_banner"]
        # 在 Windows 系统上使用 GBK 编码，在其他系统上使用 UTF-8
        encoding = 'gbk' if os.name == 'nt' else 'utf-8'
        result = subprocess.run(probe_cmd, capture_output=True, text=True, encoding=encoding, errors='ignore')
        
        # 检查是否有音频流
        has_audio = False
        for line in result.stderr.split('\n'):
            if 'Audio:' in line:
                has_audio = True
                break
        
        if not has_audio:
            Logger.warning(f"输入文件没有音频流: {input_path}")
            # 创建一个静音音频文件
            duration = MediaProcessor.get_media_duration(input_path)
            if duration > 0:
                silence_cmd = [
                    ffmpeg_path, "-y", "-f", "lavfi", "-i", f"anullsrc=r={sample_rate}:cl=mono",
                    "-t", str(duration), str(output_path)
                ]
                SystemUtils.run_cmd(silence_cmd)
                Logger.info(f"创建静音音频文件: {output_path}")
            else:
                # 如果无法获取时长，创建1秒的静音音频
                silence_cmd = [
                    ffmpeg_path, "-y", "-f", "lavfi", "-i", f"anullsrc=r={sample_rate}:cl=mono",
                    "-t", "1", str(output_path)
                ]
                SystemUtils.run_cmd(silence_cmd)
                Logger.info(f"创建1秒静音音频文件: {output_path}")
        else:
            # 提取音频
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

                encoding = 'gbk' if os.name == 'nt' else 'utf-8'
                proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding=encoding, errors='ignore')
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
        video_width = 720

        try:
            # 在 Windows 系统上使用 GBK 编码，在其他系统上使用 UTF-8
            encoding = 'gbk' if os.name == 'nt' else 'utf-8'
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, encoding=encoding, errors='ignore')

            # 检查 probe_result 是否有效
            if probe_result is None or probe_result.stderr is None:
                Logger.warning(f"无法获取视频信息: {video_path}，使用默认宽度 720")
                return video_width

            for line in probe_result.stderr.split('\n'):
                if 'Video:' in line and 'x' in line:
                    match = re.search(r'(\d{3,5})x(\d{3,5})', line)
                    if match:
                        video_width = int(match.group(1))
                    break

        except (UnicodeDecodeError, AttributeError, Exception) as e:
            Logger.warning(f"获取视频宽度时出错: {video_path}, 错误: {e}，使用默认宽度 720")
            video_width = 720

        return video_width

    @staticmethod
    def burn_hardsub(video_path: Path, srt_path: Path, output_path: Path, subtitle_bottom_margin: int = 20):
        """
        生成硬字幕视频（将字幕直接烧录到视频画面中）

        Args:
            video_path: 视频文件路径
            srt_path: SRT字幕文件路径
            output_path: 输出视频文件路径
            subtitle_bottom_margin: 字幕下沿距离（像素），默认为0
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
                srt_path, output_path.parent, video_width, platform_suffix, subtitle_bottom_margin
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

                # 检查视频文件是否在输出目录中
                video_in_output_dir = video_path.parent == output_dir

                if video_in_output_dir:
                    # 视频文件在输出目录中，使用相对路径
                    video_rel = video_path.name
                else:
                    # 视频文件不在输出目录中，使用绝对路径
                    video_rel = str(video_path.resolve())

                output_rel = output_path.name
                temp_ass_rel = temp_ass_path.name

                # 读取 ASS 文件内容进行调试
                with open(temp_ass_path, 'r', encoding='utf-8') as f:
                    ass_content = f.read()
                Logger.info(f"ASS 文件内容（前500字符）:\n{ass_content[:500]}")

                # 使用更兼容的字幕滤镜参数
                cmd = [
                    ffmpeg_path, "-y", "-i", video_rel,
                    "-vf", f"subtitles={temp_ass_rel}",
                    "-c:a", "copy", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-movflags", "+faststart",
                    output_rel
                ]
                Logger.info(f"执行 FFmpeg 命令: {' '.join(cmd)}")
                print(f"执行命令: {' '.join(cmd)}")
                encoding = 'gbk' if os.name == 'nt' else 'utf-8'
                proc = subprocess.run(cmd, capture_output=True, text=True, encoding=encoding, errors='ignore')
                Logger.info(f"FFmpeg stdout: {proc.stdout}")
                if proc.stderr:
                    Logger.info(f"FFmpeg stderr: {proc.stderr}")

                # 如果使用 subtitles 滤镜失败，尝试使用 ass 滤镜
                if proc.returncode != 0:
                    Logger.warning("subtitles 滤镜失败，尝试使用 ass 滤镜")
                    cmd = [
                        ffmpeg_path, "-y", "-i", video_rel,
                        "-vf", f"ass={temp_ass_rel}",
                        "-c:a", "copy", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                        "-movflags", "+faststart",
                        output_rel
                    ]
                    Logger.info(f"执行备用 FFmpeg 命令: {' '.join(cmd)}")
                    proc = subprocess.run(cmd, capture_output=True, text=True, encoding=encoding, errors='ignore')
                    Logger.info(f"备用 FFmpeg stdout: {proc.stdout}")
                    if proc.stderr:
                        Logger.info(f"备用 FFmpeg stderr: {proc.stderr}")
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
            # 在 Windows 系统上使用 GBK 编码，在其他系统上使用 UTF-8
            encoding = 'gbk' if os.name == 'nt' else 'utf-8'
            result = subprocess.run(cmd, capture_output=True, text=True, encoding=encoding, errors='ignore')
            duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})', result.stderr)
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
    def merge_audio_video(video_path: Path, audio_path: Path, output_path: Path, use_shortest: bool = True, audio_volume: float = 1.0, keep_original_audio: bool = True):
        """
        将音频合并到视频中

        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径
            output_path: 输出视频文件路径
            use_shortest: 是否使用最短时长（默认True，兼容旧版本）
            audio_volume: 音频音量倍数（默认1.0，表示原音量；0.5表示降低一半音量；2.0表示提高一倍音量）
            keep_original_audio: 是否保留原视频音频（默认True，保留并混合；False则替换原音频）
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

            # 检查原视频是否有音频流
            probe_cmd = [ffmpeg_path, "-i", str(video_path), "-hide_banner"]
            # 在 Windows 系统上使用 GBK 编码，在其他系统上使用 UTF-8
            encoding = 'gbk' if os.name == 'nt' else 'utf-8'
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, encoding=encoding, errors='ignore')
            has_audio = 'Audio:' in probe_result.stderr

            # 构建命令
            if os.name == 'nt':  # Windows
                if keep_original_audio and has_audio:
                    # 保留原音频并混合
                    Logger.info("保留原视频音频，与新音频混合")
                    # 只调整新音频的音量，然后混合
                    if audio_volume != 1.0:
                        cmd_str = f'{ffmpeg_path} -y -i "{video_rel}" -i "{audio_rel}" -filter_complex "[1:a]volume={audio_volume}[a1_vol];[0:a][a1_vol]amix=inputs=2:duration=first:dropout_transition=2[aout]" -map 0:v:0 -map "[aout]" -c:v copy -c:a aac'
                        Logger.info(f"应用新音频音量调整: {audio_volume}x")
                    else:
                        cmd_str = f'{ffmpeg_path} -y -i "{video_rel}" -i "{audio_rel}" -filter_complex "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2[aout]" -map 0:v:0 -map "[aout]" -c:v copy -c:a aac'
                    if use_shortest:
                        cmd_str += ' -shortest'
                    cmd_str += f' "{output_rel}"'
                else:
                    # 替换原音频
                    if has_audio:
                        Logger.info("使用新音频替换原视频音频")
                    else:
                        Logger.info("原视频无音频，直接添加新音频")
                    cmd_str = f'{ffmpeg_path} -y -i "{video_rel}" -i "{audio_rel}" -c:v copy -c:a aac -map 0:v:0 -map 1:a:0'
                    
                    # 如果音量不是1.0，添加音量滤镜
                    if audio_volume != 1.0:
                        cmd_str += f' -filter:a "volume={audio_volume}"'
                        Logger.info(f"应用音频音量调整: {audio_volume}x")
                    
                    if use_shortest:
                        cmd_str += ' -shortest'
                    cmd_str += f' "{output_rel}"'
                
                # 直接执行命令
                encoding = 'gbk' if os.name == 'nt' else 'utf-8'
                proc = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, encoding=encoding, errors='ignore')
                if proc.returncode != 0:
                    raise RuntimeError(
                        f"Command failed: {cmd_str}\n"
                        f"stdout:\n{proc.stdout}\n"
                        f"stderr:\n{proc.stderr}"
                    )
            else:
                # 在 Linux/Mac 上使用列表命令
                if keep_original_audio and has_audio:
                    # 保留原音频并混合
                    Logger.info("保留原视频音频，与新音频混合")
                    # 只调整新音频的音量，然后混合
                    if audio_volume != 1.0:
                        cmd = [
                            ffmpeg_path, "-y", "-i", video_rel, "-i", audio_rel,
                            "-filter_complex", f"[1:a]volume={audio_volume}[a1_vol];[0:a][a1_vol]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                            "-map", "0:v:0", "-map", "[aout]",
                            "-c:v", "copy", "-c:a", "aac"
                        ]
                        Logger.info(f"应用新音频音量调整: {audio_volume}x")
                    else:
                        cmd = [
                            ffmpeg_path, "-y", "-i", video_rel, "-i", audio_rel,
                            "-filter_complex", f"[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                            "-map", "0:v:0", "-map", "[aout]",
                            "-c:v", "copy", "-c:a", "aac"
                        ]
                    if use_shortest:
                        cmd.append("-shortest")
                    cmd.append(output_rel)
                else:
                    # 替换原音频
                    if has_audio:
                        Logger.info("使用新音频替换原视频音频")
                    else:
                        Logger.info("原视频无音频，直接添加新音频")
                    cmd = [
                        ffmpeg_path, "-y", "-i", video_rel, "-i", audio_rel,
                        "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0"
                    ]
                    
                    # 如果音量不是1.0，添加音量滤镜
                    if audio_volume != 1.0:
                        cmd.extend(["-filter:a", f"volume={audio_volume}"])
                        Logger.info(f"应用音频音量调整: {audio_volume}x")
                    
                    # 根据参数决定是否添加 -shortest
                    if use_shortest:
                        cmd.append("-shortest")
                    
                    cmd.append(output_rel)
                
                SystemUtils.run_cmd(cmd)
            Logger.info(f"音视频合并成功: {output_path}")

        except Exception as e:
            Logger.error(f"音视频合并失败: {e}")
            raise
        finally:
            os.chdir(original_cwd)

    @staticmethod
    def adjust_audio_speed(audio_path: Path, output_path: Path, speed_factor: float) -> Path:
        """
        调整音频语速

        Args:
            audio_path: 输入音频文件路径
            output_path: 输出音频文件路径
            speed_factor: 语速调整倍数（>1加速，<1减速）

        Returns:
            Path: 调整后的音频文件路径
        """
        audio_path = Path(audio_path).resolve()
        output_path = Path(output_path).resolve()

        ffmpeg_path = SystemUtils.get_ffmpeg_path()

        # 使用 atempo 滤镜调整音频速度
        # atempo 滤镜的范围是 0.5 到 100.0
        # 如果需要的倍数超出范围，可以级联多个 atempo 滤镜
        if speed_factor < 0.5 or speed_factor > 2.0:
            Logger.warning(f"语速调整倍数 {speed_factor} 超出推荐范围 (0.5-2.0)，可能影响音质")

        original_cwd = os.getcwd()

        try:
            output_dir = output_path.parent
            os.chdir(output_dir)

            audio_rel = os.path.relpath(audio_path, output_dir)
            output_rel = output_path.name

            audio_rel = audio_rel.replace('\\', '/')

            if os.name == 'nt':  # Windows
                # 构建FFmpeg命令
                cmd_str = f'{ffmpeg_path} -y -i "{audio_rel}" -filter:a "atempo={speed_factor}" "{output_rel}"'

                Logger.info(f"调整音频语速: {speed_factor}x")
                Logger.info(f"执行命令: {cmd_str}")

                # 执行命令
                encoding = 'gbk' if os.name == 'nt' else 'utf-8'
                proc = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, encoding=encoding, errors='ignore')
                if proc.returncode != 0:
                    raise RuntimeError(
                        f"Command failed: {cmd_str}\n"
                        f"stdout:\n{proc.stdout}\n"
                        f"stderr:\n{proc.stderr}"
                    )
            else:
                # Linux/Mac 命令
                cmd = [
                    ffmpeg_path, "-y", "-i", audio_rel,
                    "-filter:a", f"atempo={speed_factor}",
                    output_rel
                ]

                Logger.info(f"调整音频语速: {speed_factor}x")
                SystemUtils.run_cmd(cmd)

            Logger.info(f"音频语速调整成功: {output_path}")
            return output_path

        except Exception as e:
            Logger.error(f"音频语速调整失败: {e}")
            raise
        finally:
            os.chdir(original_cwd)

    @staticmethod
    def normalize_audio(audio_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        标准化音频文件：转换为 44100Hz 采样率、2通道立体声、192k 音频比特率

        Args:
            audio_path: 输入音频文件路径
            output_path: 输出音频文件路径（如果为 None，则覆盖原文件）

        Returns:
            Path: 标准化后的音频文件路径
        """
        audio_path = Path(audio_path).resolve()

        # 如果未指定输出路径，则覆盖原文件
        if output_path is None:
            output_path = audio_path
        else:
            output_path = Path(output_path).resolve()

        ffmpeg_path = SystemUtils.get_ffmpeg_path()

        # 标准参数
        target_sample_rate = 44100  # 44.1kHz
        target_channels = 2  # 立体声
        target_bitrate = "192k"  # 192kbps

        # 检查是否需要使用临时文件（输入和输出相同）
        use_temp_file = (audio_path == output_path)
        temp_output_path = None

        if use_temp_file:
            # 创建临时文件名
            temp_output_path = output_path.parent / f"temp_{output_path.name}"

        original_cwd = os.getcwd()

        try:
            output_dir = output_path.parent
            os.chdir(output_dir)

            audio_rel = os.path.relpath(audio_path, output_dir)
            output_rel = temp_output_path.name if use_temp_file else output_path.name

            audio_rel = audio_rel.replace('\\', '/')

            if os.name == 'nt':  # Windows
                # 构建FFmpeg命令
                cmd_str = f'{ffmpeg_path} -y -i "{audio_rel}" -ar {target_sample_rate} -ac {target_channels} -b:a {target_bitrate} "{output_rel}"'

                Logger.info(f"标准化音频: {audio_path.name}")
                Logger.info(f"  采样率: {target_sample_rate}Hz, 声道: {target_channels}, 比特率: {target_bitrate}")
                Logger.info(f"执行命令: {cmd_str}")

                # 执行命令
                encoding = 'gbk' if os.name == 'nt' else 'utf-8'
                proc = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, encoding=encoding, errors='ignore')
                if proc.returncode != 0:
                    raise RuntimeError(
                        f"Command failed: {cmd_str}\n"
                        f"stdout:\n{proc.stdout}\n"
                        f"stderr:\n{proc.stderr}"
                    )
            else:
                # Linux/Mac 命令
                cmd = [
                    ffmpeg_path, "-y", "-i", audio_rel,
                    "-ar", str(target_sample_rate),
                    "-ac", str(target_channels),
                    "-b:a", target_bitrate,
                    output_rel
                ]

                Logger.info(f"标准化音频: {audio_path.name}")
                Logger.info(f"  采样率: {target_sample_rate}Hz, 声道: {target_channels}, 比特率: {target_bitrate}")
                SystemUtils.run_cmd(cmd)

            # 如果使用了临时文件，替换原文件
            if use_temp_file and temp_output_path and temp_output_path.exists():
                import shutil
                shutil.move(str(temp_output_path), str(output_path))
                Logger.info(f"替换原文件: {output_path}")

            Logger.info(f"音频标准化成功: {output_path}")
            return output_path

        except Exception as e:
            Logger.error(f"音频标准化失败: {e}")
            # 清理临时文件
            if temp_output_path and temp_output_path.exists():
                try:
                    temp_output_path.unlink()
                    Logger.info(f"清理临时文件: {temp_output_path}")
                except Exception as cleanup_error:
                    Logger.warning(f"清理临时文件失败: {cleanup_error}")
            raise
        finally:
            os.chdir(original_cwd)

    @staticmethod
    def merge_audio_video_with_duration(video_path: Path, audio_path: Path, output_path: Path, 
                                       target_duration: float, extend_video: bool = True, audio_volume: float = 1.0, keep_original_audio: bool = True):
        """
        将音频合并到视频中，支持指定目标时长和视频扩展

        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径
            output_path: 输出视频文件路径
            target_duration: 目标时长（秒）
            extend_video: 是否扩展视频长度（以最后一帧补充）
            audio_volume: 音频音量倍数（默认1.0，表示原音量；0.5表示降低一半音量；2.0表示提高一倍音量）
            keep_original_audio: 是否保留原视频音频（默认True，保留并混合；False则替换原音频）
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

            # 检查原视频是否有音频流
            probe_cmd = [ffmpeg_path, "-i", str(video_path), "-hide_banner"]
            # 在 Windows 系统上使用 GBK 编码，在其他系统上使用 UTF-8
            encoding = 'gbk' if os.name == 'nt' else 'utf-8'
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, encoding=encoding, errors='ignore')
            has_audio = 'Audio:' in probe_result.stderr

            if extend_video:
                # 使用 loop 和 duration 参数扩展视频
                if keep_original_audio and has_audio:
                    # 保留原音频并混合
                    Logger.info("保留原视频音频，与新音频混合")
                    # 只调整新音频的音量，然后混合
                    if audio_volume != 1.0:
                        cmd = [
                            ffmpeg_path, "-y",
                            "-stream_loop", "-1", "-i", video_rel,  # 无限循环视频
                            "-i", audio_rel,
                            "-filter_complex", f"[1:a]volume={audio_volume}[a1_vol];[0:a][a1_vol]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                            "-map", "0:v:0", "-map", "[aout]",
                            "-c:v", "copy", "-c:a", "aac",
                            "-t", str(target_duration),  # 指定总时长
                            "-avoid_negative_ts", "make_zero",  # 避免负时间戳
                            output_rel
                        ]
                        Logger.info(f"应用新音频音量调整: {audio_volume}x")
                    else:
                        cmd = [
                            ffmpeg_path, "-y",
                            "-stream_loop", "-1", "-i", video_rel,  # 无限循环视频
                            "-i", audio_rel,
                            "-filter_complex", f"[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                            "-map", "0:v:0", "-map", "[aout]",
                            "-c:v", "copy", "-c:a", "aac",
                            "-t", str(target_duration),  # 指定总时长
                            "-avoid_negative_ts", "make_zero",  # 避免负时间戳
                            output_rel
                        ]
                else:
                    # 替换原音频
                    if has_audio:
                        Logger.info("使用新音频替换原视频音频")
                    else:
                        Logger.info("原视频无音频，直接添加新音频")
                    cmd = [
                        ffmpeg_path, "-y",
                        "-stream_loop", "-1", "-i", video_rel,  # 无限循环视频
                        "-i", audio_rel,
                        "-c:v", "copy", "-c:a", "aac",
                        "-map", "0:v:0", "-map", "1:a:0",
                        "-t", str(target_duration),  # 指定总时长
                        "-avoid_negative_ts", "make_zero",  # 避免负时间戳
                        output_rel
                    ]

                    # 如果音量不是1.0，添加音量滤镜
                    if audio_volume != 1.0:
                        cmd.insert(-1, "-filter:a")
                        cmd.insert(-1, f"volume={audio_volume}")
                        Logger.info(f"应用音频音量调整: {audio_volume}x")

                Logger.info(f"扩展视频到目标时长: {target_duration:.2f}秒")
            else:
                # 标准合并，使用最短时长
                if keep_original_audio and has_audio:
                    # 保留原音频并混合
                    Logger.info("保留原视频音频，与新音频混合")
                    # 只调整新音频的音量，然后混合
                    if audio_volume != 1.0:
                        cmd = [
                            ffmpeg_path, "-y", "-i", video_rel, "-i", audio_rel,
                            "-filter_complex", f"[1:a]volume={audio_volume}[a1_vol];[0:a][a1_vol]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                            "-map", "0:v:0", "-map", "[aout]",
                            "-c:v", "copy", "-c:a", "aac",
                            "-shortest", output_rel
                        ]
                        Logger.info(f"应用新音频音量调整: {audio_volume}x")
                    else:
                        cmd = [
                            ffmpeg_path, "-y", "-i", video_rel, "-i", audio_rel,
                            "-filter_complex", f"[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                            "-map", "0:v:0", "-map", "[aout]",
                            "-c:v", "copy", "-c:a", "aac",
                            "-shortest", output_rel
                        ]
                else:
                    # 替换原音频
                    if has_audio:
                        Logger.info("使用新音频替换原视频音频")
                    else:
                        Logger.info("原视频无音频，直接添加新音频")
                    cmd = [
                        ffmpeg_path, "-y", "-i", video_rel, "-i", audio_rel,
                        "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0",
                        "-shortest", output_rel
                    ]
                    
                    # 如果音量不是1.0，添加音量滤镜
                    if audio_volume != 1.0:
                        cmd.insert(-1, "-filter:a")
                        cmd.insert(-1, f"volume={audio_volume}")
                        Logger.info(f"应用音频音量调整: {audio_volume}x")

            SystemUtils.run_cmd(cmd)
            Logger.info(f"音视频合并成功: {output_path}")

        except Exception as e:
            Logger.error(f"音视频合并失败: {e}")
            raise
        finally:
            os.chdir(original_cwd)
