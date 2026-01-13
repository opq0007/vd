"""
视频处理工具类

提供视频编码、格式转换等功能。
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional


class VideoUtils:
    """视频处理工具类"""

    @staticmethod
    def get_available_video_codec(width: int, height: int, fps: int) -> Tuple[int, str]:
        """
        获取可用的视频编码器

        Args:
            width: 视频宽度
            height: 视频高度
            fps: 帧率

        Returns:
            Tuple[int, str]: (fourcc 编码器, 编码器名称)
        """
        # 按优先级尝试不同的编码器，避免使用 libopenh264
        # 优先使用系统内置的编码器，避免版本兼容问题
        preferred_codecs = [
            ('mp4v', 'MP4V (MPEG-4 Part 2)'),  # 最稳定的编码器
            ('DIVX', 'DivX'),
            ('XVID', 'XviD'),
            ('MJPG', 'Motion JPEG'),
            ('I420', 'Raw YUV'),
        ]

        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        for codec_name, codec_desc in preferred_codecs:
            try:
                fourcc = cv2.VideoWriter_fourcc(*codec_name)
                # 测试编码器是否可用
                test_path = output_dir / "codec_test.mp4"
                test_writer = cv2.VideoWriter(
                    str(test_path),
                    fourcc,
                    fps,
                    (width, height)
                )

                if test_writer.isOpened():
                    # 尝试写入一帧测试
                    test_frame = np.zeros((height, width, 3), dtype=np.uint8)
                    test_writer.write(test_frame)
                    test_writer.release()
                    # 删除测试文件
                    test_path.unlink(missing_ok=True)
                    return fourcc, codec_desc
            except Exception as e:
                # 忽略错误，继续尝试下一个编码器
                if test_path.exists():
                    test_path.unlink(missing_ok=True)
                continue

        # 如果所有编码器都失败，使用默认的 mp4v
        return cv2.VideoWriter_fourcc(*'mp4v'), 'MP4V (default)'

    @staticmethod
    def create_video_writer(
        output_path: Path,
        width: int,
        height: int,
        fps: int
    ) -> Optional[cv2.VideoWriter]:
        """
        创建视频写入器

        Args:
            output_path: 输出文件路径
            width: 视频宽度
            height: 视频高度
            fps: 帧率

        Returns:
            Optional[cv2.VideoWriter]: 视频写入器，失败返回 None
        """
        try:
            fourcc, codec_desc = VideoUtils.get_available_video_codec(width, height, fps)

            out = cv2.VideoWriter(
                str(output_path),
                fourcc,
                fps,
                (width, height)
            )

            if not out.isOpened():
                raise RuntimeError(f"无法打开视频写入器: {output_path}")

            return out

        except Exception as e:
            print(f"创建视频写入器失败: {e}")
            return None

    @staticmethod
    def convert_to_browser_compatible(input_path: Path, output_path: Optional[Path] = None) -> Optional[Path]:
        """
        转换视频为浏览器兼容格式

        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径（可选）

        Returns:
            Optional[Path]: 转换后的视频路径，失败返回 None
        """
        try:
            from utils.system_utils import SystemUtils

            if output_path is None:
                output_path = input_path.parent / f"{input_path.stem}_converted.mp4"

            ffmpeg_path = SystemUtils.get_ffmpeg_path()

            # 使用 FFmpeg 转换为 H.264 编码的 MP4
            cmd = [
                ffmpeg_path, "-y", "-i", str(input_path),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",
                str(output_path)
            ]

            SystemUtils.run_cmd(cmd)

            return output_path

        except Exception as e:
            print(f"视频转换失败: {e}")
            return None