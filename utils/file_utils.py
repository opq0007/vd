"""
文件操作工具类

提供文件路径处理、文件类型判断、文件复制等功能。
"""

import shutil
from pathlib import Path
from datetime import datetime
from typing import List

from config import config


class FileUtils:
    """文件操作工具类"""

    @staticmethod
    def get_output_dir() -> Path:
        """获取输出目录"""
        current_dir = Path(__file__).parent.parent
        output_dir = current_dir / config.OUTPUT_FOLDER
        output_dir.mkdir(exist_ok=True)
        return output_dir

    @staticmethod
    def create_job_dir() -> Path:
        """创建任务目录，使用yyyyMMdd-HHMMSS格式命名"""
        output_dir = FileUtils.get_output_dir()
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M%S")
        job_dir_name = f"job_{date_str}-{time_str}"
        job_dir = output_dir / job_dir_name
        job_dir.mkdir(exist_ok=True)
        return job_dir

    @staticmethod
    def generate_job_id() -> str:
        """生成任务ID，使用yyyyMMdd-HHMMSS格式"""
        now = datetime.now()
        return now.strftime("%Y%m%d-%H%M%S")

    @staticmethod
    def get_file_extension(filename: str) -> str:
        """获取文件扩展名"""
        return Path(filename).suffix.lower()

    @staticmethod
    def is_video_file(filename: str) -> bool:
        """判断是否为视频文件"""
        return FileUtils.get_file_extension(filename) in config.VIDEO_EXTENSIONS

    @staticmethod
    def is_audio_file(filename: str) -> bool:
        """判断是否为音频文件"""
        return FileUtils.get_file_extension(filename) in config.AUDIO_EXTENSIONS

    @staticmethod
    def is_supported_file(filename: str) -> bool:
        """判断是否为支持的文件格式"""
        return FileUtils.is_video_file(filename) or FileUtils.is_audio_file(filename)

    @staticmethod
    def is_url(path: str) -> bool:
        """判断路径是否为URL"""
        return path.startswith(("http://", "https://"))

    @staticmethod
    def process_path_input(path: str, job_dir: Path) -> Path:
        """
        处理统一的路径输入，自动判断是URL还是本地路径

        Args:
            path: 输入路径，可以是URL或本地路径
            job_dir: 任务目录，用于下载URL文件

        Returns:
            处理后的本地文件路径
        """
        from utils.media_processor import MediaProcessor
        from utils.logger import Logger

        if FileUtils.is_url(path):
            # 处理URL
            filename = Path(path.split("?")[0].split("/")[-1] or "downloaded_file")
            local_path = job_dir / filename.name
            MediaProcessor.download_from_url(path, local_path)
            Logger.info(f"下载URL文件: {path} -> {local_path}")
            return local_path
        else:
            # 处理本地路径
            clean_path = path.strip()
            # 移除可能的Unicode方向控制字符
            clean_path = ''.join(char for char in clean_path if ord(char) not in [8234, 8235, 8236, 8237])
            local_path = Path(clean_path).resolve()
            if not local_path.exists():
                raise FileNotFoundError(f"本地文件不存在: {clean_path}")

            # 复制到任务目录
            dest_path = job_dir / local_path.name

            # 检查源文件和目标文件是否相同
            try:
                if local_path.resolve() == dest_path.resolve():
                    # 文件已经在目标目录中，直接返回
                    Logger.info(f"文件已在目标目录中: {local_path}")
                    return local_path
                shutil.copy2(str(local_path), str(dest_path))
                Logger.info(f"复制本地文件: {local_path} -> {dest_path}")
            except shutil.SameFileError:
                # 如果捕获到 SameFileError，直接返回源文件路径
                Logger.info(f"文件已在目标目录中: {local_path}")
                return local_path

            return dest_path

    @staticmethod
    def safe_delete(file_path: Path):
        """安全删除文件"""
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            from utils.logger import Logger
            Logger.error(f"删除文件失败: {file_path}, 错误: {e}")

    @staticmethod
    def get_file_size(file_path: Path) -> int:
        """获取文件大小（字节）"""
        if file_path.exists():
            return file_path.stat().st_size
        return 0

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """格式化文件大小为人类可读格式"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"