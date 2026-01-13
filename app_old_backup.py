#!/usr/bin/env python3
"""
整合版 Whisper 服务 - 统一 FastAPI + Gradio 界面
- FastAPI REST API with Bearer token auth
- Gradio UI with modern interface
- faster-whisper for ASR
- 统一认证和服务层
- 支持基础转录和高级字幕生成
"""

import os
import io
import sys
import uuid
import shutil
import tempfile
import asyncio
import traceback
import hashlib
import datetime
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import timedelta, datetime

import requests
import subprocess
import jwt
import aiofiles
import json
from faster_whisper import WhisperModel

from fastapi import FastAPI, File, UploadFile, Header, Body, HTTPException, Query, Depends, status, Form
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import gradio as gr
import numpy as np
import torch

# ----------------------------
# 配置和常量
# ----------------------------
class AppConfig:
    """应用配置类 - 统一管理所有配置参数"""
    
    # 服务配置
    API_TOKEN = os.environ.get("API_TOKEN", "whisper-api-key-2024")  # MUST set in production
    SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production")
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", 7860))
    
    # URL 配置
    BASE_HOST = os.environ.get("BASE_HOST", "127.0.0.1")  # 用于生成 URL 的主机地址
    BASE_URL = f"http://{BASE_HOST}:{PORT}"
    API_BASE_URL = f"{BASE_URL}/api"
    GRADIO_URL = f"{BASE_URL}/ui"
    DOCS_URL = f"{BASE_URL}/docs"
    
    # Whisper模型配置
    DEFAULT_MODEL = os.environ.get("FW_MODEL", "small")
    DEFAULT_DEVICE = os.environ.get("FW_DEVICE", "cpu")
    DEFAULT_COMPUTE = os.environ.get("FW_COMPUTE", "int8")  # e.g. "int8", "float16", or None
    CPU_THREADS = 8
    BEAM_SIZE = 5
    
    # 本地模型路径配置
    MODELS_DIR = os.environ.get("FW_MODELS_DIR", "models")
    USE_LOCAL_MODELS = os.environ.get("FW_USE_LOCAL_MODELS", "true").lower() == "true"
    
    # 文件和目录配置
    UPLOAD_FOLDER = 'uploads'
    OUTPUT_FOLDER = 'output'
    DEBUG_FOLDER = 'debug'
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    # 任务配置
    JOB_TIMEOUT = 3600  # 1小时超时
    POLLING_INTERVAL = 2.0  # 轮询间隔（秒）
    
    # FFmpeg配置
    FFMPEG_PATHS = [
        "ffmpeg",
        r"D:\programs\ffmpeg-7.1.1-full_build\bin\ffmpeg.exe"
    ]
    
    # 认证配置
    API_TOKENS = {
        'whisper-api-key-2024': 'automation',
        'test-token': 'test'
    }
    
    USERS = {
        'admin': hashlib.sha256('admin123'.encode()).hexdigest(),
        'user': hashlib.sha256('user123'.encode()).hexdigest()
    }
    
    # 支持的文件格式
    VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
    AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac']
    
    # VoxCPM配置
    # VOXCPM_MODEL_DIR = os.path.join(MODELS_DIR, "OpenBMB__VoxCPM1.5")
    VOXCPM_MODEL_DIR = os.path.join(MODELS_DIR, "OpenBMB__VoxCPM-0.5B")
    VOXCPM_REPO_ID = os.environ.get("VOXCPM_REPO_ID", "OpenBMB/VoxCPM-0.5B")
    VOXCPM_DEFAULT_CFG = 2.0
    VOXCPM_DEFAULT_TIMESTEPS = 10
    # ASR模型配置
    ASR_MODEL_NAME = os.environ.get("ASR_MODEL_NAME", "SenseVoiceSmall")
    ASR_MODEL_DIR = os.path.join(MODELS_DIR, "iic__"+ASR_MODEL_NAME)
    # ModelScope配置
    MODELSCOPE_CACHE_DIR = os.environ.get("MODELSCOPE_CACHE", os.path.join(MODELS_DIR, "modelscope_cache"))
    
    @classmethod
    def init_directories(cls):
        """初始化必要的目录"""
        for folder in [cls.UPLOAD_FOLDER, cls.OUTPUT_FOLDER, cls.DEBUG_FOLDER]:
            os.makedirs(folder, exist_ok=True)
    
    @classmethod
    def get_supported_extensions(cls):
        """获取支持的文件扩展名"""
        return cls.VIDEO_EXTENSIONS + cls.AUDIO_EXTENSIONS
    
    @classmethod
    def get_api_urls(cls, endpoint: str) -> List[str]:
        """获取 API 端点的多个 URL 地址，用于兼容不同的网络环境"""
        return [
            f"http://127.0.0.1:{cls.PORT}{endpoint}",
            f"http://localhost:{cls.PORT}{endpoint}",
            f"http://0.0.0.0:{cls.PORT}{endpoint}",
            f"http://[::1]:{cls.PORT}{endpoint}"  # IPv6 localhost
        ]

# 初始化配置
config = AppConfig()
config.init_directories()

# 全局变量
JOBS: Dict[str, Dict[str, Any]] = {}

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 设置torch精度，避免TensorFloat32警告
try:
    torch.set_float32_matmul_precision('high')
except:
    pass

# ----------------------------
# FastAPI 应用初始化
# ----------------------------
app = FastAPI(title="整合版 Whisper 语音转文字服务", version="2.0.0")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ----------------------------
# 工具类
# ----------------------------
class FileUtils:
    """文件操作工具类"""
    
    @staticmethod
    def get_output_dir() -> Path:
        """获取输出目录"""
        current_dir = Path(__file__).parent
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
        if FileUtils.is_url(path):
            # 处理URL
            filename = Path(path.split("?")[0].split("/")[-1] or "downloaded_file")
            local_path = job_dir / filename.name
            MediaProcessor.download_from_url(path, local_path)
            Logger.info(f"下载URL文件: {path} -> {local_path}")
            return local_path
        else:
            # 处理本地路径
            # 清除路径中的Unicode控制字符（特别是Windows从资源管理器复制时可能添加的字符）
            clean_path = path.strip()
            # 移除可能的Unicode方向控制字符
            clean_path = ''.join(char for char in clean_path if ord(char) not in [8234, 8235, 8236, 8237])
            local_path = Path(clean_path).resolve()
            if not local_path.exists():
                raise FileNotFoundError(f"本地文件不存在: {clean_path}")
            
            # 复制到任务目录
            dest_path = job_dir / local_path.name
            shutil.copy2(str(local_path), str(dest_path))
            Logger.info(f"复制本地文件: {local_path} -> {dest_path}")
            return dest_path

class SystemUtils:
    """系统工具类"""
    
    _ffmpeg_path = None
    
    @classmethod
    def run_cmd(cls, cmd: List[str]) -> str:
        """执行命令并返回输出"""
        if os.name == 'nt':  # Windows
            cmd = [str(c) for c in cmd]
        
        proc = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            shell=os.name == 'nt'
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"Command failed: {' '.join(cmd)}\n"
                f"stdout:\n{proc.stdout}\n"
                f"stderr:\n{proc.stderr}"
            )
        return proc.stdout
    
    @classmethod
    def check_ffmpeg_available(cls) -> bool:
        """检查ffmpeg是否可用"""
        if cls._ffmpeg_path:
            return True
        
        for ffmpeg_path in config.FFMPEG_PATHS:
            try:
                subprocess.run([ffmpeg_path, "-version"], capture_output=True, check=True)
                cls._ffmpeg_path = ffmpeg_path
                logger.info(f"Found ffmpeg at: {ffmpeg_path}")
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        logger.warning("FFmpeg not found in system PATH or configured paths")
        return False
    
    @classmethod
    def get_ffmpeg_path(cls) -> str:
        """获取ffmpeg路径"""
        if not cls.check_ffmpeg_available():
            raise RuntimeError(
                "FFmpeg 未安装或不在 PATH 中。请安装 FFmpeg: https://ffmpeg.org/download.html"
            )
        return cls._ffmpeg_path

class MediaProcessor:
    """媒体处理工具类"""
    
    @staticmethod
    def extract_audio(input_path: Path, output_path: Path, sample_rate: int = 16000):
        """从视频或音频文件中提取音频"""
        input_path = Path(input_path).resolve()
        output_path = Path(output_path).resolve()
        
        # 确保输入文件存在
        if not input_path.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_path}")
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        ffmpeg_path = SystemUtils.get_ffmpeg_path()
        
        cmd = [
            ffmpeg_path, "-y", "-i", str(input_path),
            "-ac", "1", "-ar", str(sample_rate),
            "-vn", "-f", "wav", str(output_path)
        ]
        
        try:
            Logger.info(f"开始提取音频: {input_path} -> {output_path}")
            SystemUtils.run_cmd(cmd)
            
            # 验证输出文件是否成功创建
            if not output_path.exists():
                raise RuntimeError(f"音频提取失败，输出文件未创建: {output_path}")
            
            # 检查文件大小
            if output_path.stat().st_size == 0:
                raise RuntimeError(f"音频提取失败，输出文件为空: {output_path}")
            
            Logger.info(f"音频提取成功: {output_path} (大小: {output_path.stat().st_size} 字节)")
            
        except Exception as e:
            Logger.error(f"音频提取失败: {e}")
            # 清理可能的不完整输出文件
            if output_path.exists():
                output_path.unlink()
            raise
    
    @staticmethod
    def download_from_url(url: str, output_path: Path, timeout: int = 60):
        """从URL下载文件"""
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Downloading URL: {url} to {output_path}")
        try:
            with requests.get(url, stream=True, timeout=timeout) as r:
                r.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            logger.info(f"Downloaded successfully: {output_path}")
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            raise
    
    @staticmethod
    def mux_softsub(video_path: Path, srt_path: Path, output_path: Path):
        """生成软字幕视频（将SRT字幕嵌入到视频文件中）"""
        video_path = Path(video_path).resolve()
        srt_path = Path(srt_path).resolve()
        output_path = Path(output_path).resolve()
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        ffmpeg_path = SystemUtils.get_ffmpeg_path()
        
        try:
            # 在Windows上使用相对路径，避免路径解析问题
            import os
            original_cwd = os.getcwd()
            
            # 切换到输出文件所在目录
            output_dir = output_path.parent
            os.chdir(output_dir)
            
            # 使用相对路径
            video_rel = os.path.relpath(video_path, output_dir)
            srt_rel = os.path.relpath(srt_path, output_dir)
            output_rel = output_path.name
            
            # 确保使用正斜杠
            video_rel = video_rel.replace('\\', '/')
            srt_rel = srt_rel.replace('\\', '/')
            
            # 根据视频格式选择字幕编码
            video_ext = video_path.suffix.lower()
            if os.name == 'nt':
                # Windows 使用 shell=True
                if video_ext in ['.mp4', '.mov', '.m4v']:
                    # MP4/MOV 使用 mov_text 编码
                    cmd = f'{ffmpeg_path} -y -i "{video_rel}" -i "{srt_rel}" -c:v copy -c:a copy -c:s mov_text -metadata:s:s:0 language=chi -disposition:s:0 default -map 0:v -map 0:a? -map 1:s "{output_rel}"'
                elif video_ext in ['.mkv']:
                    # MKV 使用 SRT 编码
                    cmd = f'{ffmpeg_path} -y -i "{video_rel}" -i "{srt_rel}" -c:v copy -c:a copy -c:s srt -metadata:s:s:0 language=chi -disposition:s:0 default -map 0:v -map 0:a? -map 1:s "{output_rel}"'
                else:
                    # 其他格式尝试使用通用字幕编码
                    cmd = f'{ffmpeg_path} -y -i "{video_rel}" -i "{srt_rel}" -c:v copy -c:a copy -c:s ass -metadata:s:s:0 language=chi -disposition:s:0 default -map 0:v -map 0:a? -map 1:s "{output_rel}"'
                
                # Windows 上使用 shell=True
                proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if proc.returncode != 0:
                    raise RuntimeError(
                        f"Command failed: {cmd}\n"
                        f"stdout:\n{proc.stdout}\n"
                        f"stderr:\n{proc.stderr}"
                    )
            else:
                # Linux/Mac 使用列表形式
                if video_ext in ['.mp4', '.mov', '.m4v']:
                    # MP4/MOV 使用 mov_text 编码
                    cmd = [
                        ffmpeg_path, "-y", "-i", video_rel, "-i", srt_rel,
                        "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text",
                        "-metadata:s:s:0", "language=chi",
                        "-disposition:s:0", "default",
                        "-map", "0:v", "-map", "0:a?", "-map", "1:s",
                        output_rel
                    ]
                elif video_ext in ['.mkv']:
                    # MKV 使用 SRT 编码
                    cmd = [
                        ffmpeg_path, "-y", "-i", video_rel, "-i", srt_rel,
                        "-c:v", "copy", "-c:a", "copy", "-c:s", "srt",
                        "-metadata:s:s:0", "language=chi",
                        "-disposition:s:0", "default",
                        "-map", "0:v", "-map", "0:a?", "-map", "1:s",
                        output_rel
                    ]
                else:
                    # 其他格式尝试使用通用字幕编码
                    cmd = [
                        ffmpeg_path, "-y", "-i", video_rel, "-i", srt_rel,
                        "-c:v", "copy", "-c:a", "copy", "-c:s", "ass",
                        "-metadata:s:s:0", "language=chi",
                        "-disposition:s:0", "default",
                        "-map", "0:v", "-map", "0:a?", "-map", "1:s",
                        output_rel
                    ]
                
                # Linux/Mac 上使用 run_cmd
                SystemUtils.run_cmd(cmd)
            
            Logger.info(f"软字幕视频生成成功: {output_path}")
            
        except Exception as e:
            Logger.error(f"软字幕视频生成失败: {e}")
            raise
        finally:
            # 恢复原始工作目录
            os.chdir(original_cwd)
    
    @staticmethod
    def wrap_chinese_text(text: str, video_width: int, font_size: int) -> str:
        """
        处理中文字幕自动换行
        Args:
            text: 原始文本
            video_width: 视频宽度
            font_size: 字体大小
        Returns:
            处理后的文本，包含换行符
        """
        # 计算每行最大字符数（考虑中文字符宽度）
        # 中文字符宽度约为英文字符的2倍
        margin = 40  # 左右边距
        available_width = video_width - margin * 2
        char_per_line = int(available_width / (font_size * 0.6))  # 中文字符平均宽度
        
        # 处理已有换行符
        lines = text.split(r'\N')
        wrapped_lines = []
        
        for line in lines:
            if len(line) <= char_per_line:
                wrapped_lines.append(line)
            else:
                # 需要换行
                current_line = ""
                for char in line:
                    # 检查是否为中文、英文或标点
                    if '\u4e00' <= char <= '\u9fff' or char in '，。！？；：""''（）【】《》':
                        # 中文字符或中文标点
                        if len(current_line) >= char_per_line:
                            wrapped_lines.append(current_line)
                            current_line = char
                        else:
                            current_line += char
                    else:
                        # 英文字符或英文标点
                        if len(current_line) >= char_per_line * 1.5:  # 英文可以稍长
                            wrapped_lines.append(current_line)
                            current_line = char
                        else:
                            current_line += char
                
                if current_line:
                    wrapped_lines.append(current_line)
        
        return r'\N'.join(wrapped_lines)
    
    @staticmethod
    def get_subtitle_style_config(video_width: int) -> dict:
        """
        根据视频宽度获取统一的字幕样式配置
        Args:
            video_width: 视频宽度
        Returns:
            字幕样式配置字典
        """
        # 根据视频宽度动态调整字幕样式
        if video_width <= 640:
            font_size = 10
            margin = 5
        elif video_width <= 1280:
            font_size = 16
            margin = 10
        else:
            font_size = 20
            margin = 15
        
        return {
            'font_size': font_size,
            'margin': margin,
            'font_name': 'Arial',
            'primary_color': '&H00ffffff',
            'secondary_color': '&H000000FF',
            'outline_color': '&H00000000',
            'back_color': '&H80000000',
            'bold': 1,
            'italic': 0,
            'border_style': 1,
            'outline': 2,
            'shadow': 0,
            'alignment': 2,
            'encoding': 1
        }
    
    @staticmethod
    def create_ass_subtitle(srt_path: Path, output_dir: Path, video_width: int, platform_suffix: str = "") -> Path:
        """
        创建ASS字幕文件，支持中文自动换行
        Args:
            srt_path: SRT文件路径
            output_dir: 输出目录
            video_width: 视频宽度
            platform_suffix: 平台后缀（用于区分临时文件）
        Returns:
            ASS文件路径
        """
        style_config = MediaProcessor.get_subtitle_style_config(video_width)
        
        # 创建ASS字幕样式
        style_content = f"""[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style_config['font_name']},{style_config['font_size']},{style_config['primary_color']},{style_config['secondary_color']},{style_config['outline_color']},{style_config['back_color']},{style_config['bold']},{style_config['italic']},0,0,100,100,0,0,{style_config['border_style']},{style_config['outline']},{style_config['shadow']},{style_config['alignment']},{style_config['margin']},{style_config['margin']},5,{style_config['encoding']}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""
        
        # 将SRT转换为ASS格式
        ass_content = []
        ass_content.append(style_content)
        
        # 读取SRT文件并转换
        with open(srt_path, 'r', encoding='utf-8') as f:
            srt_content = f.read()
        
        # 简单的SRT到ASS转换
        import re
        srt_blocks = re.split(r'\n\s*\n', srt_content.strip())
        
        for block in srt_blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                # 解析时间
                time_match = re.match(r'(\d{1,2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{1,2}):(\d{2}):(\d{2}),(\d{3})', lines[1])
                if time_match:
                    h1, m1, s1, ms1, h2, m2, s2, ms2 = time_match.groups()
                    start_time = f"{int(h1):01d}:{m1}:{s1}.{ms1}0"
                    end_time = f"{int(h2):01d}:{m2}:{s2}.{ms2}0"
                    
                    # 合并文本行
                    text = r'\N'.join(lines[2:])
                    # 替换特殊字符
                    text = text.replace('<', '&lt;').replace('>', '&gt;')
                    
                    # 处理中文自动换行
                    text = MediaProcessor.wrap_chinese_text(text, video_width, style_config['font_size'])
                    
                    ass_content.append(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}")
        
        # 写入临时ASS文件
        temp_ass_path = output_dir / f"{srt_path.stem}_temp{platform_suffix}.ass"
        with open(temp_ass_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(ass_content))
        
        return temp_ass_path
    
    @staticmethod
    def get_video_width(ffmpeg_path: str, video_path: str) -> int:
        """
        获取视频宽度
        Args:
            ffmpeg_path: FFmpeg路径
            video_path: 视频文件路径
        Returns:
            视频宽度
        """
        probe_cmd = [ffmpeg_path, "-i", video_path, "-hide_banner"]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        video_width = 720  # 默认宽度
        
        for line in probe_result.stderr.split('\n'):
            if 'Video:' in line and 'x' in line:
                # 解析视频分辨率，例如: 1920x1080
                import re
                match = re.search(r'(\d{3,5})x(\d{3,5})', line)
                if match:
                    video_width = int(match.group(1))
                break
        
        return video_width
    
    @staticmethod
    def burn_hardsub(video_path: Path, srt_path: Path, output_path: Path):
        """生成硬字幕视频（将字幕直接烧录到视频画面中）"""
        import os
        
        video_path = Path(video_path).resolve()
        srt_path = Path(srt_path).resolve()
        output_path = Path(output_path).resolve()
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        ffmpeg_path = SystemUtils.get_ffmpeg_path()
        
        try:
            # 确保输入文件存在
            
            if not srt_path.exists():
                raise RuntimeError(f"字幕文件不存在: {srt_path}")
            
            # 获取视频宽度信息
            video_width = MediaProcessor.get_video_width(ffmpeg_path, str(video_path))
            print(f"video_width: {video_width}")
            
            # 创建统一的ASS字幕文件
            platform_suffix = "_windows" if os.name == 'nt' else "_linux"
            temp_ass_path = MediaProcessor.create_ass_subtitle(
                srt_path, output_path.parent, video_width, platform_suffix
            )
            
            # 确保ASS文件存在
            if not temp_ass_path.exists():
                raise RuntimeError(f"ASS字幕文件创建失败: {temp_ass_path}")
            
            # 使用绝对路径，确保文件存在
            video_abs = str(video_path.resolve())
            output_abs = str(output_path.resolve())
            temp_ass_abs = str(temp_ass_path.resolve())
            
            print(f"输入视频: {video_abs}")
            print(f"ASS字幕: {temp_ass_abs}")
            print(f"输出视频: {output_abs}")
            
            # 使用工作目录切换和相对路径，避免Windows路径问题
            import os
            original_cwd = os.getcwd()
            
            try:
                # 切换到输出目录
                output_dir = output_path.parent
                os.chdir(output_dir)
                
                # 使用相对路径
                video_rel = video_path.name
                output_rel = output_path.name
                temp_ass_rel = temp_ass_path.name
                
                # 简化命令，使用相对路径
                cmd = [
                    ffmpeg_path, "-y", "-i", video_rel,
                    "-vf", f"ass={temp_ass_rel}",
                    "-c:a", "copy", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-movflags", "+faststart",
                    output_rel
                ]
                print(f"执行命令: {' '.join(cmd)}")
                proc = subprocess.run(cmd, capture_output=True, text=True)
            finally:
                # 恢复工作目录
                os.chdir(original_cwd)
            
            if proc.returncode != 0:
                raise RuntimeError(
                    f"Command failed: {' '.join(cmd) if isinstance(cmd, list) else cmd}\n"
                    f"stdout:\n{proc.stdout}\n"
                    f"stderr:\n{proc.stderr}"
                )
        finally:
            # 清理临时文件
            if 'temp_ass_path' in locals() and temp_ass_path.exists():
                temp_ass_path.unlink()
            
            Logger.info(f"硬字幕视频生成成功: {output_path}")
    
    @staticmethod
    def get_media_duration(file_path: Path) -> float:
        """获取媒体文件的时长（秒）"""
        file_path = Path(file_path).resolve()
        ffmpeg_path = SystemUtils.get_ffmpeg_path()
        
        cmd = [
            ffmpeg_path, "-i", str(file_path), "-f", "null", "-"
        ]
        
        try:
            result = SystemUtils.run_cmd(cmd)
            # 从FFmpeg输出中解析时长信息
            import re
            duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})', result)
            if duration_match:
                hours, minutes, seconds = map(float, duration_match.groups())
                return hours * 3600 + minutes * 60 + seconds
            else:
                logger.warning(f"无法获取媒体时长: {file_path}")
                return 0.0
        except Exception as e:
            Logger.error(f"获取媒体时长失败: {e}")
            return 0.0
    
    @staticmethod
    def merge_audio_video(video_path: Path, audio_path: Path, output_path: Path):
        """将音频合并到视频中（替换原音频）"""
        video_path = Path(video_path).resolve()
        audio_path = Path(audio_path).resolve()
        output_path = Path(output_path).resolve()
        
        ffmpeg_path = SystemUtils.get_ffmpeg_path()
        
        # 使用相对路径避免Windows路径解析问题
        import os
        original_cwd = os.getcwd()
        
        try:
            # 切换到输出文件所在目录
            output_dir = output_path.parent
            os.chdir(output_dir)
            
            # 使用相对路径
            video_rel = os.path.relpath(video_path, output_dir)
            audio_rel = os.path.relpath(audio_path, output_dir)
            output_rel = output_path.name
            
            # 确保使用正斜杠
            video_rel = video_rel.replace('\\', '/')
            audio_rel = audio_rel.replace('\\', '/')
            
            cmd = [
                ffmpeg_path, "-y", "-i", video_rel, "-i", audio_rel,
                "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0",
                "-shortest", output_rel  # 以较短的流为准
            ]
            
            SystemUtils.run_cmd(cmd)
            Logger.info(f"音视频合并成功: {output_path}")
            
        except Exception as e:
            Logger.error(f"音视频合并失败: {e}")
            raise
        finally:
            # 恢复原始工作目录
            os.chdir(original_cwd)

class SubtitleGenerator:
    """字幕生成工具类"""
    
    @staticmethod
    def format_timestamp(seconds: float) -> str:
        """格式化时间戳为SRT格式"""
        td = timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        milliseconds = int((td.total_seconds() - int(td.total_seconds())) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    @staticmethod
    def write_srt(segments, output_path: Path, bilingual: bool = False, translated_segments=None):
        """写入SRT字幕文件"""
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, start=1):
                start = SubtitleGenerator.format_timestamp(seg.start)
                end = SubtitleGenerator.format_timestamp(seg.end)
                orig = seg.text.strip()
                
                if bilingual and translated_segments:
                    trans = translated_segments[i-1].text.strip() if i-1 < len(translated_segments) else ""
                    text_block = (orig + "\n" + trans).strip()
                else:
                    text_block = orig
                
                f.write(f"{i}\n{start} --> {end}\n{text_block}\n\n")

class VideoEffectsProcessor:
    """视频效果处理类 - 使用OpenCV+Pillow处理花字、插图、水印等效果"""
    
    @staticmethod
    def parse_color(color_input) -> tuple:
        """
        解析各种格式的颜色输入
        Args:
            color_input: 颜色输入，可以是：
                        - 十六进制字符串: "#FF0000"
                        - RGBA字符串: "rgba(255, 0, 0, 1)"
                        - RGB字符串: "rgb(255, 0, 0)"
                        - RGB元组: (255, 0, 0)
                        - RGBA元组: (255, 0, 0, 1)
        
        Returns:
            RGB元组: (R, G, B)
        """
        try:
            if color_input is None:
                return (255, 255, 255)  # 默认白色
            
            # 如果已经是元组
            if isinstance(color_input, (tuple, list)):
                if len(color_input) >= 3:
                    return tuple(int(c) for c in color_input[:3])
            
            # 如果是字符串
            if isinstance(color_input, str):
                color_str = color_input.strip().lower()
                
                # 十六进制格式
                if color_str.startswith('#'):
                    hex_color = color_str.lstrip('#')
                    if len(hex_color) == 3:
                        # 短格式 #RGB
                        hex_color = ''.join([c*2 for c in hex_color])
                    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                
                # RGBA格式
                elif color_str.startswith('rgba'):
                    import re
                    match = re.match(r'rgba\(\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*,\s*([\d.]+)\s*\)', color_str)
                    if match:
                        r, g, b, a = match.groups()
                        return (int(float(r)), int(float(g)), int(float(b)))
                
                # RGB格式
                elif color_str.startswith('rgb'):
                    import re
                    match = re.match(r'rgb\(\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\)', color_str)
                    if match:
                        r, g, b = match.groups()
                        return (int(float(r)), int(float(g)), int(float(b)))
            
            # 默认返回白色
            return (255, 255, 255)
            
        except Exception as e:
            Logger.warning(f"Failed to parse color '{color_input}': {e}, using white instead")
            return (255, 255, 255)
    
    @staticmethod
    def time_to_seconds(time_str: str) -> float:
        """将时间字符串转换为秒数"""
        try:
            parts = time_str.split(':')
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + float(s)
            return 0.0
        except:
            return 0.0
    
    @staticmethod
    def parse_timing_config(timing_type: str, start_frame: int, end_frame: int, 
                           start_time: str, end_time: str, fps: float = 30.0) -> tuple:
        """
        解析时机配置，返回开始和结束时间（秒）
        Args:
            timing_type: "帧数范围" 或 "时间戳范围"
            start_frame: 起始帧
            end_frame: 结束帧
            start_time: 起始时间字符串
            end_time: 结束时间字符串
            fps: 帧率
            
        Returns:
            (start_seconds, end_seconds)
        """
        if timing_type == "帧数范围":
            start_seconds = start_frame / fps
            end_seconds = end_frame / fps
        else:  # 时间戳范围
            start_seconds = VideoEffectsProcessor.time_to_seconds(start_time)
            end_seconds = VideoEffectsProcessor.time_to_seconds(end_time)
        
        return start_seconds, end_seconds
    
    @staticmethod
    def create_text_image(text: str, font_size: int, font_name: str = None, 
                         text_color: tuple = (255, 255, 255), 
                         bg_color: tuple = None,
                         stroke_enabled: bool = False,
                         stroke_color: tuple = (0, 0, 0),
                         stroke_width: int = 2) -> np.ndarray:
        """
        使用Pillow创建文字图像
        Args:
            text: 要显示的文字
            font_size: 字体大小
            font_name: 字体名称
            text_color: 文字颜色 (R, G, B)
            bg_color: 背景颜色 (R, G, B)，None表示透明
            stroke_enabled: 是否启用描边
            stroke_color: 描边颜色 (R, G, B)
            stroke_width: 描边宽度
            
        Returns:
            文字图像数组
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # 确保文本是字符串类型
            if not isinstance(text, str):
                text = str(text)
            
            # 尝试加载字体
            font = None
            try:
                if font_name:
                    # 尝试常见的中文字体
                    common_fonts = [
                        font_name,
                        "simhei.ttf",
                        "msyh.ttc",
                        "simsun.ttc",
                        "arial.ttf"
                    ]
                    for font_path in common_fonts:
                        try:
                            font = ImageFont.truetype(font_path, font_size)
                            break
                        except:
                            continue
                
                if font is None:
                    # 使用默认字体
                    font = ImageFont.load_default()
            except:
                # 字体加载失败，使用默认字体
                font = ImageFont.load_default()
            
            # 计算文字尺寸
            temp_img = Image.new('RGBA', (1, 1))
            temp_draw = ImageDraw.Draw(temp_img)
            bbox = temp_draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # 确保最小尺寸
            text_width = max(text_width, len(text) * font_size // 2)
            text_height = max(text_height, font_size)
            
            # 创建图像
            if bg_color:
                img = Image.new('RGB', (text_width + 20, text_height + 20), bg_color)
            else:
                img = Image.new('RGBA', (text_width + 20, text_height + 20), (0, 0, 0, 0))
            
            draw = ImageDraw.Draw(img)
            
            # 绘制文字
            position = (10, 10)
            try:
                if stroke_enabled and stroke_width > 0:
                    # 绘制描边
                    stroke_positions = []
                    for dx in range(-stroke_width, stroke_width + 1):
                        for dy in range(-stroke_width, stroke_width + 1):
                            if dx == 0 and dy == 0:
                                continue  # 跳过中心位置
                            if abs(dx) + abs(dy) <= stroke_width:
                                stroke_positions.append((position[0] + dx, position[1] + dy))
                    
                    # 先绘制所有描边位置
                    for stroke_pos in stroke_positions:
                        draw.text(stroke_pos, text, font=font, fill=stroke_color, encoding="utf-8")
                    
                    # 再绘制主文字
                    draw.text(position, text, font=font, fill=text_color, encoding="utf-8")
                else:
                    # 不使用描边，直接绘制文字
                    draw.text(position, text, font=font, fill=text_color, encoding="utf-8")
            except:
                # 如果UTF-8编码失败，尝试不指定编码
                if stroke_enabled and stroke_width > 0:
                    # 绘制描边
                    stroke_positions = []
                    for dx in range(-stroke_width, stroke_width + 1):
                        for dy in range(-stroke_width, stroke_width + 1):
                            if dx == 0 and dy == 0:
                                continue
                            if abs(dx) + abs(dy) <= stroke_width:
                                stroke_positions.append((position[0] + dx, position[1] + dy))
                    
                    for stroke_pos in stroke_positions:
                        draw.text(stroke_pos, text, font=font, fill=stroke_color)
                    
                    draw.text(position, text, font=font, fill=text_color)
                else:
                    draw.text(position, text, font=font, fill=text_color)
            
            # 转换为numpy数组
            return np.array(img)
            
        except ImportError:
            Logger.error("PIL not installed. Please install it with: pip install Pillow")
            # 返回一个简单的文字图像
            height, width = font_size * 2, max(len(text) * font_size // 2, font_size)
            return np.full((height, width, 3), text_color, dtype=np.uint8)
        except Exception as e:
            Logger.error(f"Failed to create text image: {e}")
            # 返回一个简单的文字图像
            height, width = font_size * 2, max(len(text) * font_size // 2, font_size)
            return np.full((height, width, 3), text_color, dtype=np.uint8)
    
    @staticmethod
    def load_image(image_path: str, target_size: tuple = None, remove_bg: bool = False) -> np.ndarray:
        """
        加载图片
        Args:
            image_path: 图片路径或URL
            target_size: 目标尺寸 (width, height)
            remove_bg: 是否移除背景
            
        Returns:
            图片数组
        """
        try:
            from PIL import Image
            import cv2
            
            # 如果是URL，先下载
            if FileUtils.is_url(image_path):
                temp_dir = Path(tempfile.gettempdir()) / "video_effects"
                temp_dir.mkdir(exist_ok=True)
                temp_image = temp_dir / f"temp_image_{int(time.time())}.jpg"
                MediaProcessor.download_from_url(image_path, temp_image)
                image_path = str(temp_image)
            
            # 如果需要移除背景
            if remove_bg:
                try:
                    processed_path = VideoEffectsProcessor._remove_background(image_path)
                    image_path = str(processed_path)
                    Logger.info(f"Background removed, using processed image: {image_path}")
                except Exception as e:
                    Logger.warning(f"Background removal failed, using original image: {e}")
            
            # 使用OpenCV加载图片以保持颜色一致性
            # 对于移除背景的PNG图片，需要使用IMREAD_UNCHANGED来保留透明通道
            if remove_bg and image_path.endswith('.png'):
                img_array = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
            else:
                img_array = cv2.imread(image_path)
                
            if img_array is None:
                # 如果OpenCV失败，尝试使用PIL
                img = Image.open(image_path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img_array = np.array(img)
                # PIL加载的是RGB，OpenCV需要BGR
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            # 调整尺寸（使用OpenCV以保持颜色）
            if target_size:
                img_array = cv2.resize(img_array, target_size, interpolation=cv2.INTER_AREA)
            
            # 确保正确的颜色格式
            if len(img_array.shape) == 3:
                if img_array.shape[2] == 3:
                    # 已经是BGR格式，直接返回
                    return img_array
                elif img_array.shape[2] == 4:
                    # BGRA格式，保持透明通道
                    # 保持BGRA格式，在后续处理中正确转换颜色
                    return img_array
            else:
                # 转换为3通道BGR
                if len(img_array.shape) == 2:
                    # 灰度图转为BGR
                    return cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
            
            return img_array
            
        except ImportError:
            Logger.error("OpenCV or PIL not installed")
            return None
        except Exception as e:
            Logger.error(f"Failed to load image: {e}")
            return None
    
    @staticmethod
    def _remove_background(image_path: str) -> Path:
        """
        移除图片背景（基于rmbg.py实现，优化版本）
        Args:
            image_path: 图片路径
            
        Returns:
            处理后的图片路径
        """
        try:
            from PIL import Image
            # 检查rmbg模型是否存在
            rmbg_model_path = os.path.join(os.path.dirname(__file__), "models", "rmbg-1.4.onnx")
            if not os.path.exists(rmbg_model_path):
                Logger.warning("rmbg model not found, skipping background removal")
                return Path(image_path)
            
            import onnxruntime as ort
            
            # 加载模型
            sess = ort.InferenceSession(rmbg_model_path, providers=["CPUExecutionProvider"])
            
            # 加载原始图片
            original_img = Image.open(image_path)
            
            # 预处理 - 缩放到1024x1024用于模型处理
            size = 1024
            processed_img = original_img.convert("RGB")
            processed_img = processed_img.resize((size, size))
            arr = np.array(processed_img).astype(np.float32) / 255.0
            arr = np.transpose(arr, (2, 0, 1))   # HWC → CHW
            arr = np.expand_dims(arr, 0)
            
            # 运行模型
            outputs = sess.run(None, {"input": arr})
            mask = outputs[0]
            
            # 后处理 - 将mask调整回原始尺寸并应用到原始图片
            mask = mask.squeeze()
            mask = (mask * 255).astype(np.uint8)
            mask = Image.fromarray(mask).resize(original_img.size)
            
            # 创建带透明度的图像
            rgba = original_img.convert("RGBA")
            rgba.putalpha(mask)
            
            # 保存处理后的图片
            temp_dir = Path(tempfile.gettempdir()) / "video_effects"
            temp_dir.mkdir(exist_ok=True)
            processed_path = temp_dir / f"processed_{int(time.time())}.png"
            rgba.save(processed_path)
            
            Logger.info(f"Background removed: {processed_path}")
            return processed_path
            
        except Exception as e:
            Logger.error(f"Failed to remove background: {e}")
            return Path(image_path)
    
    @staticmethod
    def apply_watermark_effect(frame: np.ndarray, watermark_img: np.ndarray, 
                              position: str, frame_index: int, total_frames: int) -> np.ndarray:
        """
        应用水印效果
        Args:
            frame: 当前帧
            watermark_img: 水印图像
            position: 位置类型
            frame_index: 当前帧索引
            total_frames: 总帧数
            
        Returns:
            处理后的帧
        """
        h, w = frame.shape[:2]
        wh, ww = watermark_img.shape[:2]
        
        # 计算位置
        if position == "半透明浮动":
            # 半透明浮动效果
            import math
            # 水平浮动
            x = int((w - ww) // 2 + math.sin(frame_index * 0.05) * (w - ww) // 3)
            # 垂直浮动
            y = int((h - wh) // 2 + math.cos(frame_index * 0.03) * (h - wh) // 4)
        elif position == "斜向移动":
            # 斜向移动效果
            progress = (frame_index % 200) / 200.0  # 200帧一个循环
            x = int(progress * (w + ww) - ww)
            y = int(progress * (h + wh) - wh)
        
        else:
            # 默认位置
            x, y = w - ww - 20, h - wh - 20
        
        # 确保位置在有效范围内
        x = max(0, min(x, w - ww))
        y = max(0, min(y, h - wh))
        
        # 叠加水印
        try:
            if watermark_img.shape[2] == 4:  # RGBA
                # 处理透明度
                alpha = watermark_img[:, :, 3] / 255.0
                
                # 根据效果类型调整透明度
                if position == "半透明浮动":
                    alpha *= 0.5  # 降低透明度
                
                for c in range(3):
                    frame[y:y+wh, x:x+ww, c] = (
                        alpha * watermark_img[:, :, c] + 
                        (1 - alpha) * frame[y:y+wh, x:x+ww, c]
                    )
            else:
                # 如果没有alpha通道，创建一个半透明的版本
                alpha = 0.6
                frame[y:y+wh, x:x+ww] = (
                    alpha * watermark_img + 
                    (1 - alpha) * frame[y:y+wh, x:x+ww]
                ).astype(np.uint8)
        except:
            # 如果叠加失败，跳过
            pass
        
        return frame
    
    @staticmethod
    def apply_video_effects(input_path: Path, output_path: Path, 
                           flower_config: dict = None, 
                           image_config: dict = None,
                           watermark_config: dict = None) -> bool:
        """
        使用OpenCV应用视频效果
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            flower_config: 花字配置
            image_config: 插图配置
            watermark_config: 水印配置
            
        Returns:
            是否成功
        """
        try:
            import cv2
            
            # 检查是否有效果需要应用
            has_effects = flower_config or image_config or watermark_config
            if not has_effects:
                shutil.copy2(input_path, output_path)
                return True
            
            # 打开视频
            cap = cv2.VideoCapture(str(input_path))
            if not cap.isOpened():
                raise Exception(f"Cannot open video: {input_path}")
            
            # 获取视频信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # 创建视频写入器 - 尝试多个编码器以确保兼容性
            encoders_to_try = [
                ('XVID', 'XVID'),  # XVID编码器，兼容性好
                ('MP4V', 'MP4V'),  # MP4编码器
                ('MJPG', 'MJPG'),  # MJPEG编码器
                ('avc1', 'avc1'),  # AVC/H.264编码器
            ]
            
            out = None
            successful_encoder = None
            for encoder_name, fourcc_code in encoders_to_try:
                try:
                    fourcc = cv2.VideoWriter_fourcc(*fourcc_code)
                    test_out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
                    if test_out.isOpened():
                        test_out.release()
                        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
                        successful_encoder = encoder_name
                        Logger.info(f"Using video encoder: {encoder_name}")
                        break
                except Exception as e:
                    Logger.warning(f"Failed to use encoder {encoder_name}: {e}")
                    continue
            
            if out is None:
                # 如果所有编码器都失败，尝试使用默认编码器
                try:
                    out = cv2.VideoWriter(str(output_path), -1, fps, (width, height))
                    successful_encoder = "default"
                    Logger.info("Using default video encoder")
                except Exception as e:
                    Logger.error(f"Failed to initialize any video encoder: {e}")
                    raise Exception("无法初始化视频编码器")
            
            # 预处理效果资源
            flower_img = None
            if flower_config and flower_config.get('text'):
                # 获取文字颜色，支持多种格式
                raw_text_color = flower_config.get('color', (255, 255, 255))
                text_color = VideoEffectsProcessor.parse_color(raw_text_color)
                Logger.info(f"花字文字颜色: {raw_text_color} -> {text_color}")
                
                # 获取描边设置
                stroke_enabled = flower_config.get('stroke_enabled', False)
                raw_stroke_color = flower_config.get('stroke_color', (0, 0, 0))
                stroke_color = VideoEffectsProcessor.parse_color(raw_stroke_color)
                Logger.info(f"花字描边颜色: {raw_stroke_color} -> {stroke_color}")
                stroke_width = flower_config.get('stroke_width', 2)
                
                flower_img = VideoEffectsProcessor.create_text_image(
                    flower_config['text'],
                    flower_config['size'],
                    flower_config['font'],
                    text_color,
                    None,  # 透明背景
                    stroke_enabled,
                    stroke_color,
                    stroke_width
                )
            
            overlay_img = None
            if image_config and image_config.get('path'):
                overlay_img = VideoEffectsProcessor.load_image(
                    image_config['path'],
                    (image_config['width'], image_config['height']),
                    image_config.get('remove_bg', False)
                )
            
            watermark_img = None
            if watermark_config and watermark_config.get('text'):
                # 获取文字颜色，支持多种格式
                raw_watermark_color = watermark_config.get('color', (255, 255, 255))
                text_color = VideoEffectsProcessor.parse_color(raw_watermark_color)
                Logger.info(f"水印文字颜色: {raw_watermark_color} -> {text_color}")
                watermark_img = VideoEffectsProcessor.create_text_image(
                    watermark_config['text'],
                    watermark_config['size'],
                    watermark_config['font'],
                    text_color,
                    None  # 透明背景
                )
            
            # 解析时机配置
            flower_start, flower_end = (0, 0)
            if flower_config:
                flower_start, flower_end = VideoEffectsProcessor.parse_timing_config(
                    flower_config['timing_type'],
                    flower_config['start_frame'],
                    flower_config['end_frame'],
                    flower_config['start_time'],
                    flower_config['end_time'],
                    fps
                )
            
            overlay_start, overlay_end = (0, 0)
            if image_config:
                overlay_start, overlay_end = VideoEffectsProcessor.parse_timing_config(
                    image_config['timing_type'],
                    image_config['start_frame'],
                    image_config['end_frame'],
                    image_config['start_time'],
                    image_config['end_time'],
                    fps
                )
            
            watermark_start, watermark_end = (0, 0)
            if watermark_config:
                watermark_start, watermark_end = VideoEffectsProcessor.parse_timing_config(
                    watermark_config['timing_type'],
                    watermark_config['start_frame'],
                    watermark_config['end_frame'],
                    watermark_config['start_time'],
                    watermark_config['end_time'],
                    fps
                )
            
            # 处理每一帧
            frame_index = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                current_time = frame_index / fps
                
                # 应用花字效果
                if flower_img is not None and flower_start <= current_time <= flower_end:
                    try:
                        fh, fw = flower_img.shape[:2]
                        fx, fy = flower_config['x'], flower_config['y']
                        if fx + fw <= width and fy + fh <= height:
                            # 处理透明背景
                            if flower_img.shape[2] == 4:  # RGBA
                                alpha = flower_img[:, :, 3] / 255.0
                                for c in range(3):
                                    frame[fy:fy+fh, fx:fx+fw, c] = (
                                        alpha * flower_img[:, :, c] + 
                                        (1 - alpha) * frame[fy:fy+fh, fx:fx+fw, c]
                                    )
                            else:
                                frame[fy:fy+fh, fx:fx+fw] = flower_img
                    except:
                        pass
                
                # 应用插图效果
                if overlay_img is not None and overlay_start <= current_time <= overlay_end:
                    try:
                        oh, ow = overlay_img.shape[:2]
                        ox, oy = image_config['x'], image_config['y']
                        if ox + ow <= width and oy + oh <= height:
                            # 确保颜色空间一致
                            if overlay_img.shape[2] == 3:
                                # BGR图像，直接叠加
                                frame[oy:oy+oh, ox:ox+ow] = overlay_img
                            elif overlay_img.shape[2] == 4:
                                # BGRA图像，处理透明度
                                alpha = overlay_img[:, :, 3] / 255.0
                                # 只在非透明区域叠加，注意BGRA到BGR的通道顺序
                                for c in range(3):
                                    frame[oy:oy+oh, ox:ox+ow, c] = (
                                        alpha * overlay_img[:, :, c] + 
                                        (1 - alpha) * frame[oy:oy+oh, ox:ox+ow, c]
                                    )
                    except Exception as e:
                        Logger.error(f"Failed to apply overlay: {e}")
                        pass
                
                # 应用水印效果
                if watermark_img is not None and watermark_start <= current_time <= watermark_end:
                    frame = VideoEffectsProcessor.apply_watermark_effect(
                        frame, watermark_img, 
                        watermark_config['style'], 
                        frame_index, total_frames
                    )
                
                # 写入帧
                out.write(frame)
                frame_index += 1
            
            # 释放资源
            cap.release()
            out.release()
            
            Logger.info(f"Video effects applied successfully: {output_path}")
            return True
            
        except ImportError:
            Logger.error("OpenCV not installed. Please install it with: pip install opencv-python")
            return False
        except Exception as e:
            Logger.error(f"Failed to apply video effects: {e}")
            return False

class Logger:
    """日志工具类"""
    
    @staticmethod
    def debug(message: str, job_id: str = None):
        """写入调试日志"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_file = Path(__file__).parent / config.DEBUG_FOLDER / "asr_debug.log"
        
        with open(log_file, "a", encoding="utf-8") as f:
            if job_id:
                f.write(f"[{timestamp}] [JOB:{job_id}] {message}\n")
            else:
                f.write(f"[{timestamp}] {message}\n")
    
    @staticmethod
    def info(message: str, job_id: str = None):
        """写入信息日志"""
        if job_id:
            logger.info(f"[JOB:{job_id}] {message}")
        else:
            logger.info(message)
    
    @staticmethod
    def error(message: str, job_id: str = None):
        """写入错误日志"""
        if job_id:
            logger.error(f"[JOB:{job_id}] {message}")
        else:

            logger.error(message)

# ----------------------------
# Whisper 服务类（重构版）
# ----------------------------
class WhisperService:
    """Whisper 语音转文字服务类，支持模型复用和多种转录模式"""
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.config = config
            self.model_cache = {}
            self.initialized = True
    
    async def _load_model(self, model_name: str = None, device: str = None, compute_type: str = None):
        """加载 Whisper 模型（带缓存和本地模型支持）"""
        model_name = model_name or self.config.DEFAULT_MODEL
        device = device or self.config.DEFAULT_DEVICE
        compute_type = compute_type or self.config.DEFAULT_COMPUTE
        
        cache_key = (model_name, device, compute_type)
        
        if cache_key in self.model_cache:
            Logger.info(f"Using cached model: {model_name}")
            return self.model_cache[cache_key]
        
        # 尝试从本地目录加载模型
        model_path = None
        if self.config.USE_LOCAL_MODELS:
            local_model_path = os.path.join(os.path.dirname(__file__), self.config.MODELS_DIR, model_name)
            Logger.info(f"local_model_path: {local_model_path}")
            if os.path.exists(local_model_path) and os.path.isdir(local_model_path):
                model_path = local_model_path
                Logger.info(f"Found local model at: {model_path}")
        
        try:
            # 使用本地模型路径或模型名称
            actual_model = model_path if model_path else model_name
            Logger.info(f"Loading Whisper model: {actual_model}")
            
            loop = asyncio.get_event_loop()
            model = await loop.run_in_executor(
                None, 
                lambda: WhisperModel(
                    actual_model, 
                    device=device, 
                    compute_type=compute_type,
                    cpu_threads=self.config.CPU_THREADS,
                    local_files_only=bool(model_path)  # 只有在使用本地模型时才限制为本地文件
                )
            )
            self.model_cache[cache_key] = model
            Logger.info(f"Whisper model loaded successfully: {actual_model}")
            return model
        except Exception as e:
            Logger.error(f"Failed to load Whisper model: {e}")
            # 如果本地模型加载失败，尝试从网络下载
            if model_path:
                Logger.info(f"Failed to load local model, trying to download from network...")
                try:
                    loop = asyncio.get_event_loop()
                    model = await loop.run_in_executor(
                        None, 
                        lambda: WhisperModel(
                            model_name,  # 使用模型名称而不是路径
                            device=device, 
                            compute_type=compute_type,
                            cpu_threads=self.config.CPU_THREADS,
                            local_files_only=False  # 允许从网络下载
                        )
                    )
                    self.model_cache[cache_key] = model
                    Logger.info(f"Whisper model downloaded and loaded successfully: {model_name}")
                    return model
                except Exception as download_error:
                    Logger.error(f"Failed to download model: {download_error}")
                    raise Exception(f"无法加载本地模型且无法从网络下载: {e}\n网络下载错误: {download_error}")
            else:
                raise
    
    async def transcribe_basic(self, audio_path: str, beam_size: int = None, model_name: str = None) -> Dict[str, Any]:
        """
        基础语音转文字
        
        Args:
            audio_path: 音频文件路径
            beam_size: beam search 大小
            model_name: 模型名称
            
        Returns:
            包含转录结果的字典
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        beam_size = beam_size or self.config.BEAM_SIZE
        
        try:
            model = await self._load_model(model_name)
            
            loop = asyncio.get_event_loop()
            segments, info = await loop.run_in_executor(
                None, 
                lambda: model.transcribe(audio_path, beam_size=beam_size)
            )
            
            result = {
                "language": info.language,
                "language_probability": info.language_probability,
                "segments": [
                    {
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text
                    }
                    for segment in segments
                ]
            }
            
            Logger.info(f"Basic transcription completed: {len(result['segments'])} segments")
            return result
            
        except Exception as e:
            Logger.error(f"Basic transcription error: {e}")
            raise
    
    async def transcribe_advanced(
        self, 
        audio_path: Path, 
        model_name: str = None, 
        device: str = None, 
        compute_type: Optional[str] = None, 
        beam_size: int = None, 
        task: Optional[str] = None, 
        word_timestamps: bool = False
    ) -> List:
        """
        高级语音转文字
        
        Args:
            audio_path: 音频文件路径
            model_name: 模型名称
            device: 设备
            compute_type: 计算类型
            beam_size: beam search 大小
            task: 任务类型
            word_timestamps: 是否包含词级时间戳
            
        Returns:
            转录片段列表
        """
        beam_size = beam_size or self.config.BEAM_SIZE
        task = task or "transcribe"
        
        model = await self._load_model(model_name, device, compute_type)
        
        try:
            loop = asyncio.get_event_loop()
            segments, info = await loop.run_in_executor(
                None, 
                lambda: model.transcribe(
                    str(audio_path), 
                    beam_size=beam_size, 
                    task=task, 
                    word_timestamps=word_timestamps
                )
            )
            
            # 立即将segments转换为列表，避免生成器被消耗
            segments_list = list(segments)
            Logger.info(f"Advanced transcription completed: {len(segments_list)} segments")
            return segments_list
            
        except Exception as e:
            # 记录详细的错误信息
            import traceback
            error_details = traceback.format_exc()
            Logger.error(f"Advanced transcription error: {e}")
            Logger.error(f"Audio path: {audio_path}")
            Logger.error(f"Model: {model_name}, Device: {device}, Task: {task}")
            Logger.error(f"Error traceback: {error_details}")
            raise Exception(f"转录失败: {str(e)}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        # 检查本地可用模型
        local_models = []
        if self.config.USE_LOCAL_MODELS:
            models_dir = os.path.join(os.path.dirname(__file__), self.config.MODELS_DIR)
            if os.path.exists(models_dir):
                local_models = [d for d in os.listdir(models_dir) 
                              if os.path.isdir(os.path.join(models_dir, d))]
        
        return {
            "default_model": self.config.DEFAULT_MODEL,
            "default_device": self.config.DEFAULT_DEVICE,
            "default_compute_type": self.config.DEFAULT_COMPUTE,
            "cpu_threads": self.config.CPU_THREADS,
            "cached_models": list(self.model_cache.keys()),
            "available_models": list(self.model_cache.keys()) if self.model_cache else [],
            "local_models": local_models,
            "models_dir": os.path.join(os.path.dirname(__file__), self.config.MODELS_DIR),
            "use_local_models": self.config.USE_LOCAL_MODELS
        }
    
    def clear_cache(self):
        """清除模型缓存"""
        self.model_cache.clear()
        Logger.info("Model cache cleared")

# 创建全局服务实例
whisper_service = WhisperService()

# ----------------------------
# 任务管理类
# ----------------------------
class JobManager:
    """任务管理器 - 处理异步转录任务"""
    
    def __init__(self):
        self.jobs = JOBS
    
    def create_job(self, input_type: str, **kwargs) -> str:
        """创建新任务"""
        job_id = FileUtils.generate_job_id()
        job_dir = FileUtils.create_job_dir()
        
        self.jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "input_type": input_type,
            "created_at": datetime.now(),
            "job_dir": str(job_dir),
            "files": {},
            "result": None,
            "error": None,
            **kwargs
        }
        
        Logger.info(f"Created job {job_id} with input_type: {input_type}")
        return job_id
    
    def update_job_status(self, job_id: str, status: str, **kwargs):
        """更新任务状态"""
        if job_id in self.jobs:
            self.jobs[job_id]["status"] = status
            self.jobs[job_id].update(kwargs)
            Logger.info(f"Updated job {job_id} status to: {status}")
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        return self.jobs.get(job_id)
    
    def add_file(self, job_id: str, file_type: str, file_path: str):
        """添加文件到任务"""
        if job_id in self.jobs:
            self.jobs[job_id]["files"][file_type] = file_path
    
    def set_result(self, job_id: str, result: Dict[str, Any]):
        """设置任务结果"""
        if job_id in self.jobs:
            self.jobs[job_id]["result"] = result
    
    def set_error(self, job_id: str, error: str):
        """设置任务错误"""
        if job_id in self.jobs:
            self.jobs[job_id]["error"] = error
            self.update_job_status(job_id, "failed")

# 创建全局任务管理器
job_manager = JobManager()

# ----------------------------
# VoxCPM 语音合成服务类
# ----------------------------
class VoxCPMService:
    """VoxCPM 语音合成服务类"""
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.config = config
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.asr_model = None
            self.voxcpm_model = None
            self.initialized = True
    
    def _resolve_model_dir(self) -> str:
        """解析模型目录路径"""
        if os.path.isdir(self.config.VOXCPM_MODEL_DIR):
            return self.config.VOXCPM_MODEL_DIR
        
        # 如果本地模型不存在，尝试从ModelScope下载
        repo_id = self.config.VOXCPM_REPO_ID
        target_dir = os.path.join(self.config.MODELS_DIR, repo_id.replace("/", "__"))
        
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir, exist_ok=True)
            
            # 优先尝试ModelScope下载
            try:
                logger.info("Trying to download VoxCPM model from ModelScope...")
                self._download_from_modelscope(repo_id, target_dir)
                logger.info("Model downloaded successfully from ModelScope")
                return target_dir
            except Exception as e:
                logger.warning(f"ModelScope download failed: {e}")
            
            # 如果ModelScope失败，尝试HF镜像
            try:
                logger.info("Trying to download VoxCPM model from HF mirror...")
                self._download_from_hf_mirror(repo_id, target_dir)
                logger.info("Model downloaded successfully from HF mirror")
                return target_dir
            except Exception as e:
                logger.warning(f"HF mirror download failed: {e}")
            
            # 最后尝试原始HF
            try:
                logger.info("Trying to download VoxCPM model from original HF...")
                self._download_from_hf_original(repo_id, target_dir)
                logger.info("Model downloaded successfully from original HF")
                return target_dir
            except Exception as e:
                logger.error(f"All download methods failed: {e}")
                return self.config.MODELS_DIR
        
        return target_dir
    
    def _download_from_modelscope(self, repo_id: str, target_dir: str):
        """从ModelScope下载模型"""
        try:
            from modelscope import snapshot_download
            # 设置ModelScope缓存目录
            os.environ['MODELSCOPE_CACHE'] = self.config.MODELSCOPE_CACHE_DIR
            os.makedirs(self.config.MODELSCOPE_CACHE_DIR, exist_ok=True)
            
            # 转换HF repo_id到ModelScope格式
            ms_repo_id = repo_id
            logger.info(f"Downloading from ModelScope: {ms_repo_id}")
            
            snapshot_download(
                model_id=ms_repo_id,
                local_dir=target_dir,
                cache_dir=self.config.MODELSCOPE_CACHE_DIR
            )
        except ImportError:
            raise ImportError("modelscope not installed. Please install it with: pip install modelscope")
        except Exception as e:
            raise Exception(f"ModelScope download error: {e}")
    
    def _download_from_hf_mirror(self, repo_id: str, target_dir: str):
        """从HF镜像下载模型"""
        try:
            from huggingface_hub import snapshot_download
            # 设置HF镜像地址
            original_endpoint = os.environ.get('HF_ENDPOINT')
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            
            try:
                snapshot_download(
                    repo_id=repo_id,
                    local_dir=target_dir,
                    local_dir_use_symlinks=False
                )
            finally:
                # 恢复原始endpoint设置
                if original_endpoint:
                    os.environ['HF_ENDPOINT'] = original_endpoint
                else:
                    os.environ.pop('HF_ENDPOINT', None)
        except ImportError:
            raise ImportError("huggingface_hub not installed. Please install it with: pip install huggingface_hub")
        except Exception as e:
            raise Exception(f"HF mirror download error: {e}")
    
    def _download_from_hf_original(self, repo_id: str, target_dir: str):
        """从原始HF下载模型"""
        try:
            from huggingface_hub import snapshot_download
            snapshot_download(
                repo_id=repo_id,
                local_dir=target_dir,
                local_dir_use_symlinks=False
            )
        except ImportError:
            raise ImportError("huggingface_hub not installed. Please install it with: pip install huggingface_hub")
        except Exception as e:
            raise Exception(f"Original HF download error: {e}")
    
    async def _load_asr_model(self):
        """加载ASR模型"""
        if self.asr_model is not None:
            return self.asr_model
        
        # 使用配置中的ASR模型目录
        asr_model_dir = self.config.ASR_MODEL_DIR
        
        try:
            # 尝试从本地加载
            if os.path.isdir(asr_model_dir):
                logger.info(f"Loading ASR model from local directory: {asr_model_dir}")
                self._load_asr_from_local(asr_model_dir)
            else:
                logger.info(f"ASR model not found locally, downloading from ModelScope...")
                # 尝试从ModelScope下载
                self._download_asr_from_modelscope(asr_model_dir)
                self._load_asr_from_local(asr_model_dir)
            
            logger.info("ASR model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load ASR model: {e}")
            # 使用占位符
            class MockASRModel:
                def generate(self, input, language="auto", use_itn=True):
                    return [{"text": f"recognized text |> mock recognition for {input}"}]
            self.asr_model = MockASRModel()
        
        return self.asr_model
    
    def _load_asr_from_local(self, model_dir: str):
        """从本地目录加载ASR模型"""
        try:
            # 加载真实的ASR模型
            from funasr import AutoModel
            self.asr_model = AutoModel(
                model=model_dir,
                disable_update=True,
                log_level='DEBUG',
                device=self.device
            )
        except Exception as e:
            raise Exception(f"Failed to load ASR model from local: {e}")
    
    def _download_asr_from_modelscope(self, target_dir: str):
        """从ModelScope下载ASR模型"""
        try:
            from modelscope import snapshot_download
            # 设置ModelScope缓存目录
            os.environ['MODELSCOPE_CACHE'] = self.config.MODELSCOPE_CACHE_DIR
            os.makedirs(self.config.MODELSCOPE_CACHE_DIR, exist_ok=True)
            
            # ModelScope上的ASR模型ID
            ms_repo_id = f"iic/{self.config.ASR_MODEL_NAME}"
            logger.info(f"Downloading ASR model from ModelScope: {ms_repo_id}")
            
            snapshot_download(
                model_id=ms_repo_id,
                local_dir=target_dir,
                cache_dir=self.config.MODELSCOPE_CACHE_DIR
            )
            logger.info(f"ASR model downloaded to: {target_dir}")
        except ImportError:
            raise ImportError("modelscope not installed. Please install it with: pip install modelscope")
        except Exception as e:
            raise Exception(f"ModelScope ASR download error: {e}")
    
    async def _load_voxcpm_model(self):
        """加载VoxCPM模型"""
        if self.voxcpm_model is not None:
            return self.voxcpm_model
        
        model_dir = self._resolve_model_dir()
        logger.info(f"Loading VoxCPM model from: {model_dir}")
        
        # 配置torch环境以避免编译问题
        import torch._dynamo
        torch._dynamo.config.suppress_errors = True
        # 设置使用eager模式而不是编译模式
        os.environ['TORCH_COMPILE'] = '0'
        os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'
        
        # 首先尝试加载真实模型
        model_loaded = False
        try:
            # 加载真实的VoxCPM模型
            import voxcpm
            
            # 尝试不同的加载方式
            try:
                # 首先尝试使用CPU模式避免编译问题
                self.voxcpm_model = voxcpm.VoxCPM.from_pretrained(
                    hf_model_id=model_dir, optimize=False)
                model_loaded = True
                logger.info("VoxCPM model loaded successfully in CPU mode")
            except Exception as e1:
                logger.warning(f"CPU mode failed: {e1}, trying without device specification...")
                try:
                    # 尝试不指定设备
                    self.voxcpm_model = voxcpm.VoxCPM(voxcpm_model_path=model_dir, optimize=False)
                    model_loaded = True
                    logger.info("VoxCPM model loaded successfully")
                except Exception as e2:
                    logger.error(f"Both loading methods failed. Last error: {e2}")
                    
        except ImportError as e:
            logger.error(f"VoxCPM not installed: {e}")
            logger.warning("Please install voxcpm: pip install voxcpm")
        except Exception as e:
            logger.error(f"Failed to load VoxCPM model: {e}")
            # 提供更详细的错误信息
            if "Failed to find C compiler" in str(e):
                logger.warning(
                    "C compiler not found. Please install Microsoft Visual Studio Build Tools or Visual Studio with C++ development tools.\n"
                    "Or try setting environment variable CC to point to your C compiler."
                )
        
        # 如果真实模型加载失败，使用Mock模型作为备用
        if not model_loaded:
            logger.warning("Using Mock VoxCPM model as fallback")
            class MockVoxCPMModel:
                def __init__(self, model_path):
                    self.model_path = model_path
                    self.is_mock = True
                def generate(self, text, prompt_text=None, prompt_wav_path=None, cfg_value=2.0,
                           inference_timesteps=10, normalize=True, denoise=True):
                    # 生成一个简单的正弦波作为占位符
                    sr = 16000
                    duration = len(text) * 0.1  # 根据文本长度估算时长
                    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
                    wav = 0.2 * np.sin(2 * np.pi * 220 * t)
                    logger.warning(f"Using mock audio generation for text: {text[:50]}...")
                    return wav
            
            self.voxcpm_model = MockVoxCPMModel(model_dir)
        
        return self.voxcpm_model
    
    def _normalize_model_output_to_waveform(self, model_out: Any, expected_sr: int = 16000) -> np.ndarray:
        """将模型输出标准化为波形数组"""
        # 处理元组 (sr, wav)
        if isinstance(model_out, (tuple, list)) and len(model_out) >= 2:
            sr, wav = model_out[0], model_out[1]
            try:
                wav = np.asarray(wav, dtype=np.float32)
            except Exception:
                wav = np.array(wav, dtype=np.float32)
            return wav.astype(np.float32)
        
        # 处理numpy数组
        if isinstance(model_out, np.ndarray):
            return model_out.astype(np.float32)
        
        # 处理文件路径
        if isinstance(model_out, str) and os.path.isfile(model_out):
            try:
                import soundfile as sf
                wav, sr = sf.read(model_out, dtype='float32')
                if sr != expected_sr:
                    try:
                        import librosa
                        wav = librosa.resample(wav.astype(np.float32), orig_sr=sr, target_sr=expected_sr)
                    except Exception:
                        logger.warning("Sample rate mismatch and librosa not available")
                return np.asarray(wav, dtype=np.float32)
            except Exception as e:
                logger.error(f"Failed to read audio file: {e}")
        
        # 尝试强制转换
        try:
            return np.asarray(model_out, dtype=np.float32)
        except Exception:
            raise ValueError("Unsupported model output type")
    
    async def prompt_wav_recognition(self, prompt_wav: Optional[str]) -> str:
        """识别提示音频的文本"""
        if prompt_wav is None:
            return ""
        
        try:
            asr_model = await self._load_asr_model()
            res = asr_model.generate(input=prompt_wav, language="auto", use_itn=True)
            text = res[0]["text"].split('|>')[-1]
            return text
        except Exception as e:
            logger.error(f"ASR error: {e}")
            return ""
    
    async def generate_tts_audio(
        self,
        text_input: str,
        prompt_wav_path_input: Optional[str] = None,
        prompt_text_input: Optional[str] = None,
        cfg_value_input: float = 2.0,
        inference_timesteps_input: int = 10,
        do_normalize: bool = True,
        denoise: bool = True,
    ) -> np.ndarray:
        """生成语音"""
        voxcpm_model = await self._load_voxcpm_model()
        
        text = (text_input or "").strip()
        if len(text) == 0:
            raise ValueError("Please input text to synthesize")
        
        # 处理参考音频路径（支持URL和本地路径）
        processed_prompt_wav_path = None
        if prompt_wav_path_input:
            processed_prompt_wav_path = await self._process_reference_audio(prompt_wav_path_input)
        
        logger.info(f"Generating audio for text: '{text[:60]}...'")
        if processed_prompt_wav_path:
            logger.info(f"Using reference audio: {processed_prompt_wav_path}")
        
        model_out = voxcpm_model.generate(
            text=text,
            prompt_text=prompt_text_input,
            prompt_wav_path=processed_prompt_wav_path,
            cfg_value=float(cfg_value_input),
            inference_timesteps=int(inference_timesteps_input),
            normalize=bool(do_normalize),
            denoise=bool(denoise),
        )
        
        wav = self._normalize_model_output_to_waveform(model_out, expected_sr=16000)
        
        # 确保是一维数组
        if wav.ndim > 1:
            wav = wav.mean(axis=1)
        wav = wav.astype(np.float32)
        
        return wav
    
    async def _process_reference_audio(self, audio_path: str) -> Optional[str]:
        """
        处理参考音频路径，支持URL和本地路径
        Args:
            audio_path: 音频路径，可以是URL或本地路径
            
        Returns:
            处理后的本地音频文件路径
        """
        if not audio_path:
            return None
        
        try:
            # 创建临时目录用于存储处理后的音频
            temp_dir = Path(tempfile.gettempdir()) / "voxcpm_reference_audio"
            temp_dir.mkdir(exist_ok=True)
            
            # 生成唯一的文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            hash_suffix = hashlib.md5(audio_path.encode()).hexdigest()[:8]
            temp_filename = f"ref_audio_{timestamp}_{hash_suffix}.wav"
            temp_path = temp_dir / temp_filename
            
            if FileUtils.is_url(audio_path):
                # 处理URL
                logger.info(f"Downloading reference audio from URL: {audio_path}")
                MediaProcessor.download_from_url(audio_path, temp_path)
            else:
                # 处理本地路径
                clean_path = audio_path.strip()
                # 移除可能的Unicode方向控制字符
                clean_path = ''.join(char for char in clean_path if ord(char) not in [8234, 8235, 8236, 8237])
                local_path = Path(clean_path).resolve()
                
                if not local_path.exists():
                    raise FileNotFoundError(f"参考音频文件不存在: {clean_path}")
                
                # 如果是本地文件，需要转换为WAV格式
                if local_path.suffix.lower() != '.wav':
                    logger.info(f"Converting reference audio to WAV: {local_path}")
                    MediaProcessor.extract_audio(local_path, temp_path)
                else:
                    # 直接复制WAV文件
                    shutil.copy2(str(local_path), str(temp_path))
                    logger.info(f"Copied reference audio: {local_path} -> {temp_path}")
            
            # 验证文件是否成功创建
            if not temp_path.exists():
                raise RuntimeError(f"参考音频处理失败: {temp_path}")
            
            return str(temp_path)
            
        except Exception as e:
            logger.error(f"处理参考音频失败: {e}")
            raise

# ----------------------------
# 认证服务类
# ----------------------------
class AuthService:
    """认证服务类"""
    
    @staticmethod
    def create_access_token(data: dict) -> str:
        """创建 JWT token"""
        to_encode = data.copy()
        expire = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, config.SECRET_KEY, algorithm="HS256")
    
    @staticmethod
    def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
        """验证 JWT token 或固定 API token"""
        token = credentials.credentials
        
        # 检查固定API token
        if token in config.API_TOKENS:
            return f"api_user_{config.API_TOKENS[token]}"
        
        # 验证JWT token
        try:
            payload = jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"])
            username: str = payload.get("user")
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return username
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> bool:
        """验证用户名密码"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return config.USERS.get(username) == password_hash

# ----------------------------
# Pydantic 模型
# ----------------------------
class LoginRequest(BaseModel):
    username: str
    password: str

class TranscribeRequest(BaseModel):
    input_type: str  # upload | path | separate_audio
    path: Optional[str] = None  # 统一的路径输入，可以是URL或本地路径
    model_name: Optional[str] = None
    device: Optional[str] = None
    compute_type: Optional[str] = None
    bilingual: Optional[bool] = True
    beam_size: Optional[int] = None
    word_timestamps: Optional[bool] = False
    burn: Optional[str] = "none"  # none|hard|soft
    out_basename: Optional[str] = None
    # For separate_audio mode
    video_path: Optional[str] = None  # 统一的视频路径输入
    audio_path: Optional[str] = None  # 统一的音频路径输入
    
    def __init__(self, **data):
        # 设置默认值
        if 'model_name' not in data or data['model_name'] is None:
            data['model_name'] = config.DEFAULT_MODEL
        if 'device' not in data or data['device'] is None:
            data['device'] = config.DEFAULT_DEVICE
        if 'beam_size' not in data or data['beam_size'] is None:
            data['beam_size'] = config.BEAM_SIZE
        super().__init__(**data)



# ----------------------------
# FastAPI 路由 - 认证
# ----------------------------
@app.post("/api/login")
async def login(request: LoginRequest):
    """用户登录接口"""
    if AuthService.authenticate_user(request.username, request.password):
        access_token = AuthService.create_access_token(data={"user": request.username})
        return {
            "token": access_token,
            "user": request.username,
            "token_type": "bearer"
        }
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )

# ----------------------------
# FastAPI 路由 - 基础API
# ----------------------------
@app.get("/api/model/info")
async def get_model_info(current_user: str = Depends(AuthService.verify_token)):
    """获取模型信息"""
    try:
        info = whisper_service.get_model_info()
        return info
    except Exception as e:
        Logger.error(f"Failed to get model info: {e}")
        raise HTTPException(status_code=500, detail=str(e))





@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    ffmpeg_available = SystemUtils.check_ffmpeg_available()
    ffmpeg_path = SystemUtils._ffmpeg_path if ffmpeg_available else None
    
    return {
        "status": "healthy", 
        "service": "integrated-whisper-api", 
        "version": "2.0.0",
        "ffmpeg_available": ffmpeg_available,
        "ffmpeg_path": ffmpeg_path,
        "dependencies": {
            "faster_whisper": True,
            "fastapi": True,
            "ffmpeg": ffmpeg_available
        },
        "config": {
            "default_model": config.DEFAULT_MODEL,
            "default_device": config.DEFAULT_DEVICE,
            "max_file_size": config.MAX_FILE_SIZE,
            "supported_formats": config.get_supported_extensions()
        }
    }

# ----------------------------
# FastAPI 路由 - 高级API（兼容原app.py）
# ----------------------------
@app.post("/api/transcribe/advanced-json")
async def api_transcribe_advanced_json(
    req: TranscribeRequest = Body(...), 
    authorization: Optional[str] = Header(None)
):
    """
    高级转录接口，仅支持JSON请求（用于path类型）
    """
    # 验证token
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    token = parts[1]
    if token != config.API_TOKEN and token not in config.API_TOKENS:
        raise HTTPException(status_code=403, detail="Invalid token")

    # 只支持 path 类型
    if req.input_type not in ["path"]:
        raise HTTPException(status_code=400, detail="This endpoint only supports 'path' input type")

    # 创建任务
    job_id = job_manager.create_job(req.input_type, **req.dict())
    job_dir = Path(job_manager.get_job(job_id)["job_dir"])

    # 后台任务处理
    async def _do_job():
        try:
            job_manager.update_job_status(job_id, "running")
            
            # 准备输入文件
            if not req.path:
                raise RuntimeError("path required for input_type 'path'")
            
            # 使用统一的路径处理函数
            local_input = FileUtils.process_path_input(req.path, job_dir)
            job_manager.add_file(job_id, "input", str(local_input))

            # 准备音频文件
            audio_path = job_dir / "audio.wav"
            MediaProcessor.extract_audio(local_input, audio_path)

            # 转录
            segments = await whisper_service.transcribe_advanced(
                audio_path, req.model_name, req.device, req.compute_type, 
                req.beam_size, "transcribe", req.word_timestamps
            )

            # 生成输出文件
            out_basename = req.out_basename or f"output_{job_id}"
            
            # 生成SRT字幕
            srt_path = job_dir / f"{out_basename}.srt"
            SubtitleGenerator.write_srt(segments, srt_path, bilingual=False)
            job_manager.add_file(job_id, "srt", str(srt_path))

            # 生成双语字幕
            if req.bilingual:
                translated_segments = await whisper_service.transcribe_advanced(
                    audio_path, req.model_name, req.device, req.compute_type, 
                    req.beam_size, "translate", req.word_timestamps
                )
                bilingual_srt_path = job_dir / f"{out_basename}_bilingual.srt"
                SubtitleGenerator.write_srt(segments, bilingual_srt_path, bilingual=True, translated_segments=translated_segments)
                job_manager.add_file(job_id, "srt_bilingual", str(bilingual_srt_path))

            # 处理视频输出
            if local_input and FileUtils.is_video_file(str(local_input)):
                if req.burn == "hard":
                    out_video = job_dir / f"{out_basename}_hardsub{local_input.suffix}"
                    try:
                        MediaProcessor.burn_hardsub(local_input, srt_path, out_video)
                        job_manager.add_file(job_id, "video_hardsub", str(out_video))
                        Logger.info(f"硬字幕视频生成成功: {out_video}")
                    except Exception as e:
                        Logger.error(f"硬字幕视频生成失败: {e}")
                        # 不失败整个任务，只是不生成视频文件

            # 保存转录结果
            result = {
                "segments": [
                    {"start": seg.start, "end": seg.end, "text": seg.text}
                    for seg in segments
                ],
                "transcript_text": "\n".join([seg.text for seg in segments])
            }
            job_manager.set_result(job_id, result)
            job_manager.update_job_status(job_id, "completed")

        except Exception as e:
            Logger.error(f"Job {job_id} failed: {e}", job_id)
            job_manager.set_error(job_id, str(e))

    # 启动后台任务
    asyncio.create_task(_do_job())

    return {"job_id": job_id, "status": "queued"}

@app.post("/api/transcribe/advanced")
async def api_transcribe_advanced(
    req: TranscribeRequest = Body(...), 
    authorization: Optional[str] = Header(None), 
    upload_file: Optional[UploadFile] = File(None), 
    video_file: Optional[UploadFile] = File(None),
    audio_file: Optional[UploadFile] = File(None)
):
    """
    高级转录接口，支持视频处理和字幕生成
    - For input_type == "upload": include multipart file upload_file
    - For input_type == "path": provide path in req.path (URL or local path)
    - For input_type == "separate_audio": provide video_file/audio_file or video_path/audio_path
    """
    # 验证token
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    token = parts[1]
    if token != config.API_TOKEN and token not in config.API_TOKENS:
        raise HTTPException(status_code=403, detail="Invalid token")

    job_id = str(uuid.uuid4())
    job_tmp = FileUtils.create_job_dir()
    JOBS[job_id] = {"tmp": str(job_tmp), "status": "queued", "files": {}}

    # Run transcription in background
    async def _do_job():
        try:
            JOBS[job_id]["status"] = "running"
            local_input = None
            audio_input = None
            
            # prepare input
            if req.input_type == "upload":
                if upload_file is None:
                    raise RuntimeError("upload_file required for input_type 'upload'")
                local_input = await ensure_local_file_async(upload_file, tmpdir=job_tmp)
            elif req.input_type == "path":
                if not req.path:
                    raise RuntimeError("path required for input_type 'path'")
                # 使用统一的路径处理函数
                local_input = FileUtils.process_path_input(req.path, job_tmp)
            elif req.input_type == "separate_audio":
                # Handle video file
                if video_file is not None:
                    local_input = await ensure_local_file_async(video_file, tmpdir=job_tmp)
                elif req.video_path:
                    # 使用统一的路径处理函数
                    local_input = FileUtils.process_path_input(req.video_path, job_tmp)
                else:
                    raise RuntimeError("video file required for input_type 'separate_audio'")
                
                # Handle audio file
                if audio_file is not None:
                    audio_input = await ensure_local_file_async(audio_file, tmpdir=job_tmp)
                elif req.audio_path:
                    # 使用统一的路径处理函数
                    audio_input = FileUtils.process_path_input(req.audio_path, job_tmp)
                else:
                    raise RuntimeError("audio file required for input_type 'separate_audio'")
                
                JOBS[job_id]["files"]["video_input"] = str(local_input)
                JOBS[job_id]["files"]["audio_input"] = str(audio_input)
            else:
                raise RuntimeError("input_type must be upload|path|separate_audio")

            if local_input:
                JOBS[job_id]["files"]["input"] = str(local_input)

            # Prepare audio for transcription
            audio_path = job_tmp / "audio.wav"
            if req.input_type == "separate_audio":
                # Use provided audio file directly
                shutil.copy2(str(audio_input), str(audio_path))
            else:
                # Extract audio from video or use audio file directly
                MediaProcessor.extract_audio(local_input, audio_path)

            # Transcribe
            segments = await whisper_service.transcribe_advanced(
                audio_path, req.model_name, req.device, req.compute_type, 
                req.beam_size, "transcribe", req.word_timestamps
            )

            # Generate outputs
            out_basename = req.out_basename or f"output_{job_id}"
            
            # Always generate SRT
            srt_path = job_tmp / f"{out_basename}.srt"
            SubtitleGenerator.write_srt(segments, srt_path, bilingual=False)
            JOBS[job_id]["files"]["srt"] = str(srt_path)

            # Generate bilingual SRT if requested
            if req.bilingual:
                # Translate segments
                translated_segments = await whisper_service.transcribe_advanced(
                    audio_path, req.model_name, req.device, req.compute_type, 
                    req.beam_size, "translate", req.word_timestamps
                )
                bilingual_srt_path = job_tmp / f"{out_basename}_bilingual.srt"
                SubtitleGenerator.write_srt(segments, bilingual_srt_path, bilingual=True, translated_segments=translated_segments)
                JOBS[job_id]["files"]["srt_bilingual"] = str(bilingual_srt_path)

            # Process video output if requested
            if req.input_type != "separate_audio" and local_input and local_input.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
                if req.burn == "soft":
                    # Hard subtitles
                    if req.burn == "hard":
                        out_video = job_tmp / f"{out_basename}_hardsub{local_input.suffix}"
                    try:
                        MediaProcessor.burn_hardsub(local_input, srt_path, out_video)
                        JOBS[job_id]["files"]["video_hardsub"] = str(out_video)
                        Logger.info(f"硬字幕视频生成成功: {out_video}")
                    except Exception as e:
                        Logger.error(f"硬字幕视频生成失败: {e}")
                        # 不失败整个任务，只是不生成视频文件

            # Store transcription result
            JOBS[job_id]["result"] = {
                "segments": [
                    {"start": seg.start, "end": seg.end, "text": seg.text}
                    for seg in segments
                ]
            }

            JOBS[job_id]["status"] = "completed"

        except Exception as e:
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = str(e)
            logger.error(f"Job {job_id} failed: {e}")

    # Start background job
    asyncio.create_task(_do_job())

    return {"job_id": job_id, "status": "queued"}

@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str, authorization: Optional[str] = Header(None)):
    """获取任务状态"""
    # 验证token
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    token = parts[1]
    if token != config.API_TOKEN and token not in config.API_TOKENS:
        raise HTTPException(status_code=403, detail="Invalid token")

    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    response = {
        "job_id": job_id,
        "status": job["status"],
        "files": job.get("files", {}),
        "created_at": job["created_at"].isoformat() if job.get("created_at") else None
    }

    if job["status"] == "completed":
        response["result"] = job.get("result")
    elif job["status"] == "failed":
        response["error"] = job.get("error")

    return response

@app.get("/api/download/{job_id}")
async def download_file(job_id: str, file: str = Query(...), authorization: Optional[str] = Header(None)):
    """下载生成的文件"""
    # 验证token
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    token = parts[1]
    if token != config.API_TOKEN and token not in config.API_TOKENS:
        raise HTTPException(status_code=403, detail="Invalid token")

    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    file_path_str = job.get("files", {}).get(file)
    if not file_path_str:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = Path(file_path_str)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(str(file_path), filename=file_path.name)

# ----------------------------
# 辅助函数
# ----------------------------
async def ensure_local_file_async(obj, tmpdir: Optional[Path]=None) -> Path:
    """
    异步版本的 ensure_local_file
    Convert various input types (Gradio NamedString, path string, UploadFile, bytes, io.BytesIO)
    into a local Path (copied into a temp directory).
    """
    Logger.debug(f"ensure_local_file called with object type: {type(obj)}")
    
    if tmpdir is None:
        tmpdir = FileUtils.create_job_dir()
    else:
        tmpdir = Path(tmpdir)
        tmpdir.mkdir(parents=True, exist_ok=True)
    
    Logger.debug(f"Using temp directory: {tmpdir}")

    # UploadFile from FastAPI (has .file and .filename)
    if hasattr(obj, "file") and hasattr(obj, "filename"):
        filename = getattr(obj, "filename")
        if not filename:
            filename = "upload.bin"
        dst = tmpdir / Path(filename).name
        async with aiofiles.open(dst, "wb") as f:
            # obj.file might be async object; attempt to read bytes
            try:
                content = await obj.file.read()
            except Exception:
                # Try .readable -> iterate
                await obj.file.seek(0)
                content = await obj.file.read()
            if isinstance(content, str):
                content = content.encode()
            await f.write(content)
        return dst

    # If it's a plain str that points to a file path:
    if isinstance(obj, str):
        p = Path(obj).resolve()  # Get absolute path
        if p.exists():
            dst = tmpdir / p.name
            shutil.copy2(str(p), str(dst))
            return dst
        # If it's a base64 data URL or raw base64, try to handle? (not implemented)
        raise RuntimeError(f"String provided but file not found: {obj}")

    # If it's a Path object
    if isinstance(obj, Path):
        p = obj.resolve()  # Get absolute path
        if p.exists():
            dst = tmpdir / p.name
            shutil.copy2(str(p), str(dst))
            return dst
        raise RuntimeError(f"Path object points to non-existent file: {obj}")

    # If nothing matched
    raise RuntimeError(f"Unsupported uploaded object type: {type(obj)}")

def mux_softsub(input_video: Path, srt_file: Path, out_video: Path):
    """混合软字幕到视频文件"""
    # Ensure paths are absolute
    input_video = Path(input_video).resolve()
    srt_file = Path(srt_file).resolve()
    out_video = Path(out_video).resolve()
    
    # Ensure output directory exists
    out_video.parent.mkdir(parents=True, exist_ok=True)
    
    # 使用找到的 ffmpeg 路径
    ffmpeg_path = globals().get('FFMPEG_PATH', 'ffmpeg')
    
    ext = out_video.suffix.lower()
    if ext in (".mp4", ".mov", ".m4v"):
        cmd = [ffmpeg_path, "-y", "-i", str(input_video), "-i", str(srt_file),
               "-map", "0", "-map", "1", "-c", "copy", "-c:s", "mov_text", str(out_video)]
    else:
        cmd = [ffmpeg_path, "-y", "-i", str(input_video), "-i", str(srt_file),
               "-map", "0", "-map", "1", "-c", "copy", "-c:s", "srt", str(out_video)]
    SystemUtils.run_cmd(cmd)

# ----------------------------
# Gradio 界面 - 整合版
# ----------------------------
def create_gradio_interface():
    """创建整合版 Gradio 界面"""
    
    # 自定义CSS
    custom_css = """
    .container {
        max-width: 1200px;
        margin: 0 auto;
    }
    .upload-area {
        border: 2px dashed #ccc;
        border-radius: 10px;
        padding: 40px;
        text-align: center;
        margin: 20px 0;
        transition: border-color 0.3s;
    }
    .upload-area:hover {
        border-color: #007bff;
    }
    .result-area {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin-top: 20px;
    }
    .segment {
        background-color: white;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 10px;
        border-left: 4px solid #007bff;
    }
    
    /* 字体回退处理 - 避免字体文件404错误影响界面 */
    @font-face {
        font-family: 'ui-monospace';
        src: local('Consolas'), local('Monaco'), local('Courier New'), monospace;
        font-display: swap;
    }
    
    body, pre, code {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 
                     'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', 
                     sans-serif, 'ui-monospace', 'Consolas', 'Monaco', 'Courier New', monospace !important;
    }
    
    /* 隐藏字体加载错误 */
    @font-face {
        font-family: 'ui-monospace';
        src: url('about:blank');
        unicode-range: U+0-10FFFF;
    }
    """
    
    with gr.Blocks(
        css=custom_css, 
        title="整合版 Whisper 语音转文字服务",
        theme=gr.themes.Soft(),
        analytics_enabled=False,
        delete_cache=(1800, 1800)  # 30分钟清理缓存
    ) as demo:
        gr.Markdown("# 🎙️ 整合版 Whisper 语音转文字服务")
        
        # 定义状态变量
        job_completed = gr.State(value=False)
        
        with gr.Tabs():
            
            # VoxCPM语音合成标签页
            with gr.TabItem("🎤 语音合成"):
                gr.Markdown("## 🎤 VoxCPM 语音合成")
                gr.Markdown("使用VoxCPM模型进行高质量语音合成，支持参考音频克隆声音")
                
                # 初始化VoxCPM服务
                voxcpm_service = VoxCPMService()
                
                with gr.Row():
                    with gr.Column():
                        # 输入区域
                        gr.Markdown("### 📝 输入文本")
                        text_input = gr.Textbox(
                            value="VoxCPM is an innovative end-to-end TTS model...",
                            label="目标文本",
                            placeholder="请输入要合成的文本...",
                            lines=3
                        )
                        
                        gr.Markdown("### 🎵 参考音频（可选）")
                        
                        # 添加参考音频输入方式选择
                        with gr.Row():
                            ref_input_type = gr.Radio(
                                choices=["上传文件", "路径方式"],
                                value="上传文件",
                                label="参考音频输入方式"
                            )
                        
                        # 上传文件选项
                        with gr.Column(visible=True) as upload_col:
                            prompt_wav_upload = gr.Audio(
                                sources=["upload", "microphone"],
                                type="filepath",
                                label="参考音频 - 上传或录制一段音频作为声音参考"
                            )
                        
                        # 路径方式选项（兼容URL和本地路径）
                        with gr.Column(visible=False) as path_col:
                            prompt_wav_path = gr.Textbox(
                                label="参考音频路径",
                                placeholder="请输入音频文件路径或URL，例如: D:/audio/reference.wav 或 https://example.com/reference.wav"
                            )
                        
                        with gr.Row():
                            prompt_text = gr.Textbox(
                                value="",
                                label="参考文本 - 可选：参考音频对应的文本内容",
                                placeholder="如果上传了参考音频，可以输入对应的文本..."
                            )
                        
                        generate_btn = gr.Button("🎬 生成语音", variant="primary")
                    
                    with gr.Column():
                        # 参数配置区域
                        gr.Markdown("### ⚙️ 参数配置")
                        
                        cfg_value = gr.Slider(
                            minimum=1.0,
                            maximum=3.0,
                            value=config.VOXCPM_DEFAULT_CFG,
                            step=0.1,
                            label="CFG值（引导强度）- 控制生成语音与目标文本的匹配程度"
                        )
                        
                        inference_timesteps = gr.Slider(
                            minimum=4,
                            maximum=30,
                            value=config.VOXCPM_DEFAULT_TIMESTEPS,
                            step=1,
                            label="推理步数 - 影响生成质量和速度的平衡"
                        )
                        
                        with gr.Row():
                            do_normalize = gr.Checkbox(
                                value=True,
                                label="文本标准化 - 自动处理文本中的特殊字符和格式"
                            )
                            
                            denoise = gr.Checkbox(
                                value=True,
                                label="音频降噪 - 对生成的音频进行降噪处理"
                            )
                        
                        # 输出区域
                        gr.Markdown("### 📤 输出音频")
                        audio_output = gr.Audio(
                            label="生成的语音",
                            type="numpy"
                        )
                        
                        # 状态显示
                        status_text = gr.Textbox(
                            label="状态",
                            interactive=False,
                            visible=True
                        )
                        
                        # 下载按钮
                        download_audio = gr.File(
                            label="下载音频",
                            visible=False
                        )
                
                # 事件处理
                async def voxcpm_generate_handler(
                    text,
                    ref_input_type,
                    prompt_wav_upload,
                    prompt_wav_path,
                    prompt_text,
                    cfg,
                    timesteps,
                    normalize,
                    denoise
                ):
                    """VoxCPM语音生成处理函数"""
                    try:
                        if not text or not text.strip():
                            return None, gr.File(visible=False), "请输入要合成的文本"
                        
                        # 根据输入方式确定参考音频路径
                        prompt_wav_path_input = None
                        if ref_input_type == "上传文件" and prompt_wav_upload:
                            prompt_wav_path_input = prompt_wav_upload
                        elif ref_input_type == "路径方式" and prompt_wav_path:
                            prompt_wav_path_input = prompt_wav_path
                        
                        # 生成语音
                        wav = await voxcpm_service.generate_tts_audio(
                            text_input=text,
                            prompt_wav_path_input=prompt_wav_path_input,
                            prompt_text_input=prompt_text,
                            cfg_value_input=cfg,
                            inference_timesteps_input=timesteps,
                            do_normalize=normalize,
                            denoise=denoise
                        )
                        
                        # 保存音频文件
                        from datetime import datetime
                        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                        output_dir = Path(config.OUTPUT_FOLDER)
                        output_dir.mkdir(exist_ok=True)
                        output_path = output_dir / f"voxcpm_{timestamp}.wav"
                        
                        # 保存为wav文件
                        try:
                            import soundfile as sf
                            sf.write(str(output_path), wav, 16000)
                        except ImportError:
                            # 如果soundfile不可用，使用scipy保存
                            from scipy.io import wavfile
                            wav_int = (wav * 32767).astype(np.int16)
                            wavfile.write(str(output_path), 16000, wav_int)
                        
                        # 确保返回正确的格式：采样率 + 波形数据
                        return (16000, wav), gr.File(value=str(output_path), visible=True), "语音生成成功！"
                    
                    except Exception as e:
                        logger.error(f"VoxCPM generation failed: {e}")
                        return None, gr.File(visible=False), f"生成失败: {str(e)}"
                
                # 输入方式切换事件
                def update_ref_input_visibility(input_type):
                    """根据选择的输入方式显示/隐藏相应的输入组件"""
                    upload_visible = input_type == "上传文件"
                    path_visible = input_type == "路径方式"
                    return (
                        gr.Column(visible=upload_visible),
                        gr.Column(visible=path_visible)
                    )
                
                ref_input_type.change(
                    fn=update_ref_input_visibility,
                    inputs=[ref_input_type],
                    outputs=[upload_col, path_col]
                )
                
                # 绑定事件
                generate_btn.click(
                    fn=voxcpm_generate_handler,
                    inputs=[
                        text_input,
                        ref_input_type,
                        prompt_wav_upload,
                        prompt_wav_path,
                        prompt_text,
                        cfg_value,
                        inference_timesteps,
                        do_normalize,
                        denoise
                    ],
                    outputs=[audio_output, download_audio, status_text]
                )
                
                # 自动识别参考音频的文本
                def auto_recognize_reference_audio(upload_file, path_input, input_type):
                    """根据输入类型自动识别参考音频的文本"""
                    audio_path = None
                    if input_type == "上传文件" and upload_file:
                        audio_path = upload_file
                    elif input_type == "路径方式" and path_input:
                        audio_path = path_input
                    
                    if audio_path:
                        return voxcpm_service.prompt_wav_recognition(audio_path)
                    return ""
                
                # 为输入方式添加变化事件
                prompt_wav_upload.change(
                    fn=auto_recognize_reference_audio,
                    inputs=[prompt_wav_upload, prompt_wav_path, ref_input_type],
                    outputs=[prompt_text]
                )
                
                prompt_wav_path.change(
                    fn=auto_recognize_reference_audio,
                    inputs=[prompt_wav_upload, prompt_wav_path, ref_input_type],
                    outputs=[prompt_text]
                )
            
            # 高级字幕生成标签页
            with gr.TabItem("高级字幕生成"):
                # 轮询状态控制
                polling_active = gr.State(value=False)
                
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 📤 上传文件")
                        input_type = gr.Radio(
                            choices=["upload", "path", "separate_audio"],
                            value="upload",
                            label="输入类型"
                        )
                        
                        with gr.Group(visible=True) as upload_group:
                            video_input = gr.Video(label="上传视频文件")
                            audio_input_adv = gr.Audio(label="上传音频文件")
                        
                        with gr.Group(visible=False) as path_group:
                            gr.Markdown("#### 📹 视频文件")
                            video_path_input = gr.Textbox(label="视频文件路径", placeholder="输入视频文件的URL或本地路径", info="支持http/https URL或本地文件路径")
                            gr.Markdown("#### 🎵 音频文件")
                            audio_path_input = gr.Textbox(label="音频文件路径", placeholder="输入音频文件的URL或本地路径", info="支持http/https URL或本地文件路径")
                            gr.Markdown("*提示：可以同时提供视频和音频文件，或只提供其中一个*")
                        
                        with gr.Group(visible=False) as separate_audio_group:
                            gr.Markdown("#### 📹 视频文件")
                            video_separate_input = gr.Video(label="上传视频文件")
                            video_separate_path_input = gr.Textbox(label="视频文件路径", placeholder="输入视频文件的URL或本地路径", info="支持http/https URL或本地文件路径")
                            
                            gr.Markdown("#### 🎵 音频文件")
                            audio_separate_input = gr.Audio(label="上传音频文件")
                            audio_separate_path_input = gr.Textbox(label="音频文件路径", placeholder="输入音频文件的URL或本地路径", info="支持http/https URL或本地文件路径")
                            
                            gr.Markdown("*提示：separate_audio模式需要同时提供视频和音频文件*")
                        
                        gr.Markdown("### ⚙️ 高级选项")
                        
                        with gr.Row():
                            model_choice_adv = gr.Dropdown(
                                choices=["tiny", "base", "small", "medium", "large"],
                                value="small",
                                label="模型选择"
                            )
                            device_choice = gr.Dropdown(
                                choices=["cpu", "cuda"],
                                value="cpu",
                                label="设备选择"
                            )
                        
                        with gr.Row():
                            generate_subtitle = gr.Checkbox(label="生成字幕", value=True, info="取消勾选则仅进行视频效果处理")
                            bilingual = gr.Checkbox(label="双语字幕", value=True)
                            word_timestamps = gr.Checkbox(label="词级时间戳", value=False)
                        
                        with gr.Row():
                            burn_type = gr.Radio(
                                choices=["none", "hard"],
                                value="none",
                                label="字幕类型"
                            )
                            beam_size_adv = gr.Slider(
                                minimum=1,
                                maximum=10,
                                value=5,
                                step=1,
                                label="Beam Size"
                            )
                        
                        # 高级视频效果配置
                        with gr.Accordion("🎨 高级视频效果", open=False):
                            # 花字配置
                            with gr.Group():
                                gr.Markdown("#### 🌟 花字配置")
                                with gr.Row():
                                    flower_text = gr.Textbox(label="花字内容", placeholder="输入要显示的花字文字")
                                    flower_font = gr.Dropdown(
                                        choices=["Arial", "SimHei", "Microsoft YaHei", "KaiTi", "FangSong"],
                                        value="Microsoft YaHei",
                                        label="字体"
                                    )
                                    flower_size = gr.Slider(
                                        minimum=20, maximum=100, value=40, step=5,
                                        label="字体大小"
                                    )
                                with gr.Row():
                                    flower_color = gr.ColorPicker(
                                        label="文字颜色",
                                        value="#FFFFFF",
                                        info="选择花字的文字颜色",
                                        show_label=True
                                    )
                                with gr.Row():
                                    flower_x = gr.Slider(
                                        minimum=0, maximum=1920, value=100, step=10,
                                        label="X坐标"
                                    )
                                    flower_y = gr.Slider(
                                        minimum=0, maximum=1080, value=100, step=10,
                                        label="Y坐标"
                                    )
                                with gr.Accordion("🖌️ 描边设置", open=False):
                                    with gr.Row():
                                        flower_stroke_enabled = gr.Checkbox(
                                            label="启用描边",
                                            value=False,
                                            info="为文字添加描边效果"
                                        )
                                    with gr.Row():
                                        flower_stroke_color = gr.ColorPicker(
                                            label="描边颜色",
                                            value="#000000",
                                            info="选择描边的颜色"
                                        )
                                        flower_stroke_width = gr.Slider(
                                            minimum=1, maximum=10, value=2, step=1,
                                            label="描边宽度",
                                            info="描边的粗细程度"
                                        )
                                with gr.Row():
                                    flower_timing_type = gr.Radio(
                                        choices=["帧数范围", "时间戳范围"],
                                        value="时间戳范围",
                                        label="插入时机类型"
                                    )
                                with gr.Group():
                                    with gr.Row(visible=True) as flower_frame_group:
                                        flower_start_frame = gr.Number(
                                            label="起始帧", value=0, minimum=0, precision=0
                                        )
                                        flower_end_frame = gr.Number(
                                            label="结束帧", value=100, minimum=0, precision=0
                                        )
                                    with gr.Row(visible=False) as flower_time_group:
                                        flower_start_time = gr.Textbox(
                                            label="起始时间", value="00:00:00", placeholder="格式: HH:MM:SS"
                                        )
                                        flower_end_time = gr.Textbox(
                                            label="结束时间", value="00:00:05", placeholder="格式: HH:MM:SS"
                                        )
                            
                            # 插图配置
                            with gr.Group():
                                gr.Markdown("#### 🖼️ 插图配置")
                                with gr.Row():
                                    image_path = gr.Textbox(
                                        label="图片路径", 
                                        placeholder="输入图片文件路径或URL",
                                        info="支持本地路径或URL"
                                    )
                                    image_remove_bg = gr.Checkbox(
                                        label="移除背景", 
                                        value=True,
                                        info="自动移除图片背景，只保留主体内容"
                                    )
                                with gr.Row():
                                    image_x = gr.Slider(
                                        minimum=0, maximum=1920, value=200, step=10,
                                        label="X坐标"
                                    )
                                    image_y = gr.Slider(
                                        minimum=0, maximum=1080, value=200, step=10,
                                        label="Y坐标"
                                    )
                                with gr.Row():
                                    image_width = gr.Slider(
                                        minimum=50, maximum=800, value=200, step=10,
                                        label="宽度"
                                    )
                                    image_height = gr.Slider(
                                        minimum=50, maximum=600, value=150, step=10,
                                        label="高度"
                                    )
                                with gr.Row():
                                    image_timing_type = gr.Radio(
                                        choices=["帧数范围", "时间戳范围"],
                                        value="时间戳范围",
                                        label="插入时机类型"
                                    )
                                with gr.Group():
                                    with gr.Row(visible=True) as image_frame_group:
                                        image_start_frame = gr.Number(
                                            label="起始帧", value=0, minimum=0, precision=0
                                        )
                                        image_end_frame = gr.Number(
                                            label="结束帧", value=100, minimum=0, precision=0
                                        )
                                    with gr.Row(visible=False) as image_time_group:
                                        image_start_time = gr.Textbox(
                                            label="起始时间", value="00:00:00", placeholder="格式: HH:MM:SS"
                                        )
                                        image_end_time = gr.Textbox(
                                            label="结束时间", value="00:00:05", placeholder="格式: HH:MM:SS"
                                        )
                            
                            # 水印配置
                            with gr.Group():
                                gr.Markdown("#### 🔒 水印配置")
                                with gr.Row():
                                    watermark_text = gr.Textbox(
                                        label="水印文字", placeholder="输入水印文字内容"
                                    )
                                    watermark_font = gr.Dropdown(
                                        choices=["Arial", "SimHei", "Microsoft YaHei", "KaiTi", "FangSong"],
                                        value="Arial",
                                        label="字体"
                                    )
                                    watermark_size = gr.Slider(
                                        minimum=12, maximum=60, value=20, step=2,
                                        label="字体大小"
                                    )
                                with gr.Row():
                                    watermark_color = gr.ColorPicker(
                                        label="文字颜色",
                                        value="#FFFFFF",
                                        info="选择水印文字的颜色",
                                        show_label=True
                                    )
                                with gr.Row():
                                    watermark_timing_type = gr.Radio(
                                        choices=["帧数范围", "时间戳范围"],
                                        value="时间戳范围",
                                        label="插入时机类型"
                                    )
                                    watermark_style = gr.Radio(
                                        choices=["半透明浮动", "斜向移动"],
                                        value="半透明浮动",
                                        label="水印效果"
                                    )
                                with gr.Group():
                                    with gr.Row(visible=True) as watermark_frame_group:
                                        watermark_start_frame = gr.Number(
                                            label="起始帧", value=0, minimum=0, precision=0
                                        )
                                        watermark_end_frame = gr.Number(
                                            label="结束帧", value=999999, minimum=0, precision=0
                                        )
                                    with gr.Row(visible=False) as watermark_time_group:
                                        watermark_start_time = gr.Textbox(
                                            label="起始时间", value="00:00:00", placeholder="格式: HH:MM:SS"
                                        )
                                        watermark_end_time = gr.Textbox(
                                            label="结束时间", value="99:59:59", placeholder="格式: HH:MM:SS"
                                        )
                        
                        transcribe_adv_btn = gr.Button("开始高级转录", variant="primary")
                        
                        # 花字配置交互逻辑
                        def update_flower_timing_visibility(timing_type):
                            frame_visible = timing_type == "帧数范围"
                            time_visible = timing_type == "时间戳范围"
                            return (
                                gr.Row(visible=frame_visible),
                                gr.Row(visible=time_visible)
                            )
                        
                        flower_timing_type.change(
                            fn=update_flower_timing_visibility,
                            inputs=[flower_timing_type],
                            outputs=[flower_frame_group, flower_time_group]
                        )
                        
                        # 插图配置交互逻辑
                        def update_image_timing_visibility(timing_type):
                            frame_visible = timing_type == "帧数范围"
                            time_visible = timing_type == "时间戳范围"
                            return (
                                gr.Row(visible=frame_visible),
                                gr.Row(visible=time_visible)
                            )
                        
                        image_timing_type.change(
                            fn=update_image_timing_visibility,
                            inputs=[image_timing_type],
                            outputs=[image_frame_group, image_time_group]
                        )
                        
                        # 水印配置交互逻辑
                        def update_watermark_timing_visibility(timing_type):
                            frame_visible = timing_type == "帧数范围"
                            time_visible = timing_type == "时间戳范围"
                            return (
                                gr.Row(visible=frame_visible),
                                gr.Row(visible=time_visible)
                            )
                        
                        watermark_timing_type.change(
                            fn=update_watermark_timing_visibility,
                            inputs=[watermark_timing_type],
                            outputs=[watermark_frame_group, watermark_time_group]
                        )
                    
                    with gr.Column():
                        gr.Markdown("### 📝 转录结果")
                        job_id_display = gr.Textbox(label="任务ID", interactive=False)
                        
                        # 简化状态显示
                        status_info = gr.HTML("<div>等待提交任务...</div>")
                        
                        result_status = gr.JSON(label="详细状态", visible=False)
                        
                        # 转录文本显示
                        transcript_display = gr.Textbox(
                            label="转录文本", 
                            lines=10, 
                            interactive=False,
                            visible=False
                        )
                        
                        # 下载文件组件
                        srt_download = gr.File(label="下载SRT字幕文件", visible=False)
                        bilingual_srt_download = gr.File(label="下载双语SRT字幕文件", visible=False)
                        video_download = gr.File(label="下载字幕视频文件", visible=False)
            
            # 视频转场特效标签页
            with gr.TabItem("视频转场特效"):
                try:
                    # 导入转场UI模块
                    from video_transitions.ui import VideoTransitionUI
                    transition_ui = VideoTransitionUI()
                    
                    # 创建转场界面组件
                    gr.Markdown("# 🎬 视频转场特效")
                    gr.Markdown("为图片或视频之间添加专业的转场效果")
                    
                    # 输入文件选择（带预览功能）
                    gr.Markdown("### 📁 输入文件")
                    with gr.Row():
                        with gr.Column():
                            video1_input = gr.File(
                                label="第一个视频/图片",
                                file_types=[".mp4", ".avi", ".mov", ".png", ".jpg", ".jpeg"]
                            )
                            video1_preview = gr.Image(label="预览1", type="numpy", visible=False)
                            
                        with gr.Column():
                            video2_input = gr.File(
                                label="第二个视频/图片", 
                                file_types=[".mp4", ".avi", ".mov", ".png", ".jpg", ".jpeg"]
                            )
                            video2_preview = gr.Image(label="预览2", type="numpy", visible=False)
                    
                    # 转场效果和参数配置（紧凑布局）
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### 🎨 转场效果")
                            
                            # 获取转场效果分类
                            categories = {"Basic": ["crossfade", "checkerboard", "blink"], "3D": ["blinds", "flip3d"], "Effects": ["explosion", "shake", "warp", "page_turn"]}
                            category_dropdown = gr.Dropdown(
                                label="效果分类",
                                choices=list(categories.keys()),
                                value="Basic"
                            )
                            
                            transition_dropdown = gr.Dropdown(
                                label="转场效果",
                                choices=categories["Basic"],
                                value="crossfade"
                            )
                            
                        with gr.Column(scale=1):
                            gr.Markdown("### ⚙️ 参数配置")
                            
                            # 基础参数（紧凑布局）
                            with gr.Row():
                                total_frames = gr.Slider(
                                    label="转场帧数",
                                    minimum=4,
                                    maximum=300,
                                    value=30,
                                    step=1
                                )
                                fps = gr.Slider(
                                    label="帧率 (FPS)",
                                    minimum=15,
                                    maximum=60,
                                    value=30,
                                    step=1
                                )
                            
                            with gr.Row():
                                width = gr.Slider(
                                    label="输出宽度",
                                    minimum=320,
                                    maximum=1920,
                                    value=1024,
                                    step=32
                                )
                                height = gr.Slider(
                                    label="输出高度", 
                                    minimum=240,
                                    maximum=1080,
                                    value=1024,
                                    step=32
                                )
                            
                            # 特效参数配置区域（动态显示）
                            with gr.Group(visible=False) as effect_params_group:
                                gr.Markdown("### 🎛️ 特效参数")
                                
                                # Warp参数
                                with gr.Group(visible=False) as warp_params_row:
                                    warp_type = gr.Dropdown(
                                        label="扭曲类型",
                                        choices=["swirl", "squeeze_h", "squeeze_v", "liquid", "wave"],
                                        value="swirl",
                                        info="选择不同的扭曲效果类型"
                                    )
                                    with gr.Row():
                                        warp_intensity = gr.Slider(
                                            label="扭曲强度",
                                            minimum=0.1,
                                            maximum=2.0,
                                            value=0.5,
                                            step=0.1
                                        )
                                        warp_speed = gr.Slider(
                                            label="扭曲速度",
                                            minimum=0.1,
                                            maximum=3.0,
                                            value=1.0,
                                            step=0.1
                                        )
                                
                                # Shake参数
                                with gr.Group(visible=False) as shake_params_row:
                                    shake_type = gr.Dropdown(
                                        label="抖动类型",
                                        choices=["random", "horizontal", "vertical", "rotation", "zoom"],
                                        value="random",
                                        info="选择不同的抖动效果类型"
                                    )
                                    shake_intensity = gr.Slider(
                                        label="抖动强度",
                                        minimum=0.1,
                                        maximum=3.0,
                                        value=1.0,
                                        step=0.1
                                    )
                                
                                # Explosion参数
                                with gr.Group(visible=False) as explosion_params_row:
                                    explosion_strength = gr.Slider(
                                        label="爆炸强度",
                                        minimum=0.5,
                                        maximum=2.0,
                                        value=1.0,
                                        step=0.1
                                    )
                                
                                
                                
                                # Flip3D参数
                                with gr.Group(visible=False) as flip3d_params_row:
                                    flip3d_direction = gr.Dropdown(
                                        label="翻转方向",
                                        choices=["horizontal", "vertical", "diagonal"],
                                        value="horizontal"
                                    )
                                    perspective_strength = gr.Slider(
                                        label="透视强度",
                                        minimum=0.5,
                                        maximum=2.0,
                                        value=1.0,
                                        step=0.1
                                    )
                                
                                # Blinds参数
                                with gr.Group(visible=False) as blinds_params_row:
                                    blinds_direction = gr.Dropdown(
                                        label="百叶窗方向",
                                        choices=["horizontal", "vertical", "diagonal"],
                                        value="horizontal"
                                    )
                                    slat_count = gr.Slider(
                                        label="百叶窗数量",
                                        minimum=5,
                                        maximum=20,
                                        value=10,
                                        step=1
                                    )
                                
                                # Page Turn参数
                                with gr.Group(visible=False) as page_turn_params_row:
                                    page_turn_direction = gr.Dropdown(
                                        label="翻页方向",
                                        choices=["right", "left", "up", "down"],
                                        value="right"
                                    )
                                    with gr.Row():
                                        curl_strength = gr.Slider(
                                            label="卷曲强度",
                                            minimum=0.5,
                                            maximum=2.0,
                                            value=1.0,
                                            step=0.1
                                        )
                                        shadow_intensity = gr.Slider(
                                            label="阴影强度",
                                            minimum=0.0,
                                            maximum=1.0,
                                            value=0.6,
                                            step=0.1
                                        )
                                
                                
                    
                    # 生成按钮和进度
                    with gr.Row():
                        generate_btn = gr.Button("🎬 生成转场视频", variant="primary")
                        status_text = gr.Textbox(label="状态", interactive=False)
                    
                    # 输出区域
                    gr.Markdown("### 📤 输出结果")
                    with gr.Row():
                        output_video = gr.Video(label="转场视频")
                        download_file = gr.File(label="下载视频", visible=False)
                    
                    # 绑定事件
                    def update_transitions(category):
                        return gr.Dropdown(choices=categories.get(category, []), 
                                        value=categories.get(category, [])[0] if categories.get(category) else None)
                    
                    def update_effect_params(transition_name):
                        """根据选择的转场效果显示相应的参数配置"""
                        # 默认所有参数组都隐藏
                        effect_params_visible = False
                        warp_params_visible = False
                        shake_params_visible = False
                        explosion_params_visible = False
                        
                        flip3d_params_visible = False
                        blinds_params_visible = False
                        page_turn_params_visible = False
                        
                        
                        # 根据转场效果显示相应参数
                        if transition_name == "warp":
                            effect_params_visible = True
                            warp_params_visible = True
                        elif transition_name == "shake":
                            effect_params_visible = True
                            shake_params_visible = True
                        elif transition_name == "explosion":
                            effect_params_visible = True
                            explosion_params_visible = True
                        
                        elif transition_name == "flip3d":
                            effect_params_visible = True
                            flip3d_params_visible = True
                        elif transition_name == "blinds":
                            effect_params_visible = True
                            blinds_params_visible = True
                        elif transition_name == "page_turn":
                            effect_params_visible = True
                            page_turn_params_visible = True
                        
                        
                        return (
                            gr.Group(visible=effect_params_visible),
                            gr.Group(visible=warp_params_visible),
                            gr.Group(visible=shake_params_visible),
                            gr.Group(visible=explosion_params_visible),
                            
                            gr.Group(visible=flip3d_params_visible),
                            gr.Group(visible=blinds_params_visible),
                            gr.Group(visible=page_turn_params_visible),
                            
                        )
                    
                    def resize_preview_image(image_path):
                        """调整预览图片尺寸，最长边不超过400像素"""
                        from PIL import Image
                        try:
                            img = Image.open(image_path)
                            width, height = img.size
                            
                            # 计算缩放比例
                            max_size = 400
                            if width > height:
                                if width > max_size:
                                    scale = max_size / width
                                    new_width = max_size
                                    new_height = int(height * scale)
                                else:
                                    return image_path  # 不需要调整
                            else:
                                if height > max_size:
                                    scale = max_size / height
                                    new_height = max_size
                                    new_width = int(width * scale)
                                else:
                                    return image_path  # 不需要调整
                            
                            # 调整图片尺寸
                            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                            
                            # 保存调整后的图片到临时文件
                            import tempfile
                            import os
                            temp_dir = tempfile.gettempdir()
                            temp_filename = f"preview_{os.path.basename(image_path)}"
                            temp_path = os.path.join(temp_dir, temp_filename)
                            img_resized.save(temp_path)
                            
                            return temp_path
                        except Exception as e:
                            print(f"Error resizing preview image: {e}")
                            return image_path  # 出错时返回原图路径
                    
                    def update_preview1(file):
                        if file is None:
                            return gr.Image(visible=False)
                        # 检查文件类型
                        if file.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                            resized_path = resize_preview_image(file.name)
                            return gr.Image(value=resized_path, visible=True)
                        else:
                            # 视频文件不显示预览
                            return gr.Image(visible=False)
                    
                    def update_preview2(file):
                        if file is None:
                            return gr.Image(visible=False)
                        # 检查文件类型
                        if file.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                            resized_path = resize_preview_image(file.name)
                            return gr.Image(value=resized_path, visible=True)
                        else:
                            # 视频文件不显示预览
                            return gr.Image(visible=False)
                    
                    category_dropdown.change(
                        fn=update_transitions,
                        inputs=[category_dropdown],
                        outputs=[transition_dropdown]
                    )
                    
                    transition_dropdown.change(
                        fn=update_effect_params,
                        inputs=[transition_dropdown],
                        outputs=[
                            effect_params_group,
                            warp_params_row,
                            shake_params_row,
                            explosion_params_row,
                            
                            flip3d_params_row,
                            blinds_params_row,
                            page_turn_params_row,
                            
                        ]
                    )
                    
                    video1_input.change(
                        fn=update_preview1,
                        inputs=[video1_input],
                        outputs=[video1_preview]
                    )
                    
                    video2_input.change(
                        fn=update_preview2,
                        inputs=[video2_input],
                        outputs=[video2_preview]
                    )
                    
                    # 生成转场视频的函数
                    def generate_transition_wrapper(
                        video1_path, video2_path, transition_name, total_frames, fps, width, height,
                        warp_type="swirl", warp_intensity=0.5, warp_speed=1.0,
                        shake_type="random", shake_intensity=1.0,
                        explosion_strength=1.0,
                        
                        flip3d_direction="horizontal", perspective_strength=1.0,
                        blinds_direction="horizontal", slat_count=10,
                        page_turn_direction="right", curl_strength=1.0, shadow_intensity=0.6,
                        
                    ):
                        try:
                            if not video1_path or not video2_path:
                                return None, gr.File(visible=False), "请选择两个输入文件"
                            
                            # 使用转场处理器
                            from video_transitions import transition_processor
                            
                            # 同步调用异步函数
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            try:
                                # 基础参数
                                transition_params = {
                                    "total_frames": total_frames,
                                    "fps": fps,
                                    "width": width,
                                    "height": height
                                }
                                
                                # 根据转场效果添加特定参数
                                if transition_name == "warp":
                                    transition_params.update({
                                        "warp_type": warp_type,
                                        "warp_intensity": warp_intensity,
                                        "warp_speed": warp_speed,
                                        "max_scale": 1.3,
                                        "scale_recovery": True
                                    })
                                elif transition_name == "shake":
                                    transition_params.update({
                                        "shake_type": shake_type,
                                        "shake_intensity": shake_intensity
                                    })
                                elif transition_name == "explosion":
                                    transition_params.update({
                                        "explosion_strength": explosion_strength
                                    })
                                
                                elif transition_name == "flip3d":
                                    transition_params.update({
                                        "flip_direction": flip3d_direction,
                                        "perspective_strength": perspective_strength
                                    })
                                elif transition_name == "blinds":
                                    transition_params.update({
                                        "direction": blinds_direction,
                                        "slat_count": slat_count
                                    })
                                elif transition_name == "page_turn":
                                    transition_params.update({
                                        "direction": page_turn_direction,
                                        "curl_strength": curl_strength,
                                        "shadow_intensity": shadow_intensity
                                    })
                                
                                
                                output_path, status = loop.run_until_complete(
                                    transition_processor.process_transition(
                                        video1_path=video1_path,
                                        video2_path=video2_path,
                                        transition_name=transition_name,
                                        **transition_params
                                    )
                                )
                                
                                if output_path:
                                    return output_path, gr.File(value=output_path, visible=True), status
                                else:
                                    return None, gr.File(visible=False), status
                                    
                            finally:
                                loop.close()
                            
                        except Exception as e:
                            return None, gr.File(visible=False), f"生成失败: {str(e)}"
                    
                    generate_btn.click(
                        fn=generate_transition_wrapper,
                        inputs=[
                            video1_input,
                            video2_input,
                            transition_dropdown,
                            total_frames,
                            fps,
                            width,
                            height,
                            warp_type, warp_intensity, warp_speed,
                            shake_type, shake_intensity,
                            explosion_strength,
                            
                            flip3d_direction, perspective_strength,
                            blinds_direction, slat_count,
                            page_turn_direction, curl_strength, shadow_intensity,
                            
                        ],
                        outputs=[output_video, download_file, status_text]
                    )
                    
                except ImportError as e:
                    gr.Markdown(f"⚠️ 转场特效模块加载失败: {e}")
                    gr.Markdown("请确保已安装所需依赖：`pip install playwright`")
                except Exception as e:
                    gr.Markdown(f"⚠️ 转场特效界面初始化失败: {e}")
                    gr.Markdown("请检查模块配置")
            
            # API文档标签页
            with gr.TabItem("API文档"):
                gr.Markdown("""
                ## 📚 API 接口文档
                
                ### 认证
                所有API请求都需要在Header中包含Authorization token：
                ```
                Authorization: Bearer <token>
                ```
                
                可用tokens：
                - `whisper-api-key-2024` - 自动化调用
                - `test-token` - 测试用途
                
                ### 基础接口
                
                #### 1. 用户登录
                ```
                POST /api/login
                Content-Type: application/json
                
                {
                    "username": "admin",
                    "password": "admin123"
                }
                ```
                
                #### 2. 获取模型信息
                ```
                GET /api/model/info
                Authorization: Bearer <token>
                ```
                
                #### 3. 基础转录
                ```
                POST /api/transcribe
                Authorization: Bearer <token>
                Content-Type: multipart/form-data
                
                audio: <音频文件>
                beam_size: 5 (可选)
                model_name: small (可选)
                ```
                
                #### 4. 高级转录
                ```
                POST /api/transcribe/advanced
                Authorization: Bearer <token>
                Content-Type: application/json
                
                {
                    "input_type": "path",
                    "path": "https://example.com/video.mp4",  # 可以是URL或本地路径
                    "model_name": "small",
                    "bilingual": true,
                    "burn": "none"
                }
                ```
                
                #### 5. 查询任务状态
                ```
                GET /api/job/{job_id}
                Authorization: Bearer <token>
                ```
                
                #### 6. 下载文件
                ```
                GET /api/download/{job_id}?file=srt
                Authorization: Bearer <token>
                ```
                
                #### 7. 健康检查
                ```
                GET /api/health
                ```
                """)
        
        # 事件处理
        def update_input_visibility(input_type):
            return (
                gr.update(visible=(input_type == "upload")),
                gr.update(visible=(input_type == "path")),
                gr.update(visible=(input_type == "separate_audio"))
            )
        
        input_type.change(
            update_input_visibility,
            inputs=[input_type],
            outputs=[upload_group, path_group, separate_audio_group]
        )
        
        # 高级转录处理
        async def transcribe_advanced_handler(*args):
            """
            高级转录处理函数 - 重构版，直接调用本地方法，无需HTTP请求
            """
            try:
                # 解包参数（包含视频效果配置）
                (input_type, video_file, audio_file, video_path, audio_path, 
                 model_name, device, 
                 generate_subtitle, bilingual, word_timestamps, burn_type, beam_size,
                 # 花字配置
                 flower_text, flower_font, flower_size, flower_color, flower_x, flower_y,
                 flower_timing_type, flower_start_frame, flower_end_frame,
                 flower_start_time, flower_end_time,
                 flower_stroke_enabled, flower_stroke_color, flower_stroke_width,
                 # 插图配置
                 image_path, image_x, image_y, image_width, image_height,
                 image_timing_type, image_start_frame, image_end_frame,
                 image_start_time, image_end_time, image_remove_bg,
                 # 水印配置
                 watermark_text, watermark_font, watermark_size, watermark_color,
                 watermark_timing_type, watermark_start_frame, watermark_end_frame,
                 watermark_start_time, watermark_end_time, watermark_style) = args
                
                # 准备视频效果配置
                flower_config = None
                if flower_text and flower_text.strip():
                    flower_config = {
                        'text': flower_text,
                        'font': flower_font,
                        'size': int(flower_size),
                        'color': flower_color,
                        'x': int(flower_x),
                        'y': int(flower_y),
                        'timing_type': flower_timing_type,
                        'start_frame': int(flower_start_frame),
                        'end_frame': int(flower_end_frame),
                        'start_time': flower_start_time,
                        'end_time': flower_end_time,
                        'stroke_enabled': flower_stroke_enabled,
                        'stroke_color': flower_stroke_color,
                        'stroke_width': int(flower_stroke_width)
                    }
                
                image_config = None
                if image_path and image_path.strip():
                    image_config = {
                        'path': image_path,
                        'x': int(image_x),
                        'y': int(image_y),
                        'width': int(image_width),
                        'height': int(image_height),
                        'remove_bg': image_remove_bg,  # 添加移除背景选项
                        'timing_type': image_timing_type,
                        'start_frame': int(image_start_frame),
                        'end_frame': int(image_end_frame),
                        'start_time': image_start_time,
                        'end_time': image_end_time
                    }
                
                watermark_config = None
                if watermark_text and watermark_text.strip():
                    watermark_config = {
                        'text': watermark_text,
                        'font': watermark_font,
                        'size': int(watermark_size),
                        'color': watermark_color,  # 存储原始值，在处理时解析
                        'timing_type': watermark_timing_type,
                        'start_frame': int(watermark_start_frame),
                        'end_frame': int(watermark_end_frame),
                        'start_time': watermark_start_time,
                        'end_time': watermark_end_time,
                        'style': watermark_style
                    }
                
                # 智能检测：如果用户同时提供了视频和音频文件，自动切换到separate_audio模式
                has_video = bool(video_file or video_path)
                has_audio = bool(audio_file or audio_path)
                
                # 处理upload模式的智能检测
                if input_type == "upload" and has_video and has_audio:
                    Logger.info("检测到upload模式下同时提供视频和音频文件，切换到separate_audio模式")
                    input_type = "separate_audio"
                elif input_type != "separate_audio" and has_video and has_audio:
                    Logger.info("检测到同时提供视频和音频文件，自动切换到separate_audio模式")
                    input_type = "separate_audio"
                
                # 创建任务
                job_id = job_manager.create_job(input_type, **{
                    "model_name": model_name,
                    "device": device,
                    "bilingual": bilingual,
                    "word_timestamps": word_timestamps,
                    "burn": burn_type,
                    "beam_size": beam_size
                })
                
                job_dir = Path(job_manager.get_job(job_id)["job_dir"])
                
                # 直接处理文件，无需HTTP请求
                local_input = None  # 主输入文件（通常是视频）
                audio_input = None  # 音频输入文件
                
                # 根据输入类型处理文件
                local_input = None
                audio_input = None
                
                try:
                    if input_type == "upload":
                        # 处理上传文件
                        if video_file:
                            local_input = job_dir / Path(video_file).name
                            shutil.copy2(video_file, local_input)
                            job_manager.add_file(job_id, "video_input", str(local_input))
                        elif audio_file:
                            local_input = job_dir / Path(audio_file).name
                            shutil.copy2(audio_file, local_input)
                            job_manager.add_file(job_id, "audio_input", str(local_input))
                            
                    elif input_type == "path":
                        # 处理统一路径输入
                        if video_path and not audio_path:
                            local_input = FileUtils.process_path_input(video_path, job_dir)
                            job_manager.add_file(job_id, "video_input", str(local_input))
                        elif audio_path and not video_path:
                            local_input = FileUtils.process_path_input(audio_path, job_dir)
                            job_manager.add_file(job_id, "audio_input", str(local_input))
                                
                    elif input_type == "separate_audio":
                        # 处理分离音视频模式
                        video_file_path = None
                        audio_file_path = None
                        
                        # 处理视频文件
                        if video_file:
                            video_file_path = job_dir / Path(video_file).name
                            shutil.copy2(video_file, video_file_path)
                            job_manager.add_file(job_id, "video_input", str(video_file_path))
                        elif video_path:
                            video_file_path = FileUtils.process_path_input(video_path, job_dir)
                            job_manager.add_file(job_id, "video_input", str(video_file_path))
                        
                        # 处理音频文件
                        if audio_file:
                            audio_file_path = job_dir / Path(audio_file).name
                            shutil.copy2(audio_file, audio_file_path)
                            job_manager.add_file(job_id, "audio_input", str(audio_file_path))
                        elif audio_path:
                            audio_file_path = FileUtils.process_path_input(audio_path, job_dir)
                            job_manager.add_file(job_id, "audio_input", str(audio_file_path))
                        
                        # 设置主输入文件为视频文件（用于输出）
                        if video_file_path:
                            local_input = video_file_path
                        if audio_file_path:
                            audio_input = audio_file_path
                    
                    # 更新任务状态为运行中
                    job_manager.update_job_status(job_id, "running")
                    
                    # 生成输出文件
                    out_basename = f"output_{job_id}"
                    
                    # 根据用户选择决定是否生成字幕
                    segments = None
                    srt_path = None
                    bilingual_srt_path = None
                    audio_for_transcription = None  # 用于转录的音频文件路径
                    
                    if generate_subtitle:
                        # 只有在需要生成字幕时才准备音频文件
                        Logger.info("准备音频文件用于转录")
                        
                        # 准备音频文件用于转录 - 使用与基础转录相同的处理方式
                        if audio_input:
                            # 直接使用上传的音频文件，让faster-whisper处理格式
                            audio_for_transcription = audio_input
                            Logger.info(f"使用上传的音频文件: {audio_for_transcription}")
                        elif local_input:
                            # 检查是否为视频文件，如果是则提取音频
                            if FileUtils.is_video_file(str(local_input)):
                                # 从视频中提取音频
                                audio_for_transcription = job_dir / "extracted_audio.wav"
                                try:
                                    MediaProcessor.extract_audio(local_input, audio_for_transcription)
                                    Logger.info(f"从视频中提取音频: {audio_for_transcription}")
                                except Exception as e:
                                    Logger.error(f"提取音频失败: {e}")
                                    raise Exception(f"无法从视频文件中提取音频: {e}")
                            else:
                                # 直接使用音频文件
                                audio_for_transcription = local_input
                                Logger.info(f"使用本地音频文件: {audio_for_transcription}")
                        else:
                            # 在separate_audio模式下，如果没有audio_input或local_input，检查job中的文件
                            job = job_manager.get_job(job_id)
                            if job and "audio_input" in job.get("files", {}):
                                audio_for_transcription = Path(job["files"]["audio_input"])
                                Logger.info(f"使用job中的音频文件: {audio_for_transcription}")
                            elif job and "video_input" in job.get("files", {}):
                                # 从视频中提取音频
                                video_path = Path(job["files"]["video_input"])
                                audio_for_transcription = job_dir / "extracted_audio.wav"
                                try:
                                    MediaProcessor.extract_audio(video_path, audio_for_transcription)
                                    Logger.info(f"从job中的视频提取音频: {audio_for_transcription}")
                                except Exception as e:
                                    Logger.error(f"提取音频失败: {e}")
                                    raise Exception(f"无法从视频文件中提取音频: {e}")
                            else:
                                raise Exception("无法找到有效的输入文件")
                    else:
                        Logger.info("跳过音频提取，不生成字幕")
                    
                    if generate_subtitle:
                        # 确保音频文件存在
                        if not audio_for_transcription or not Path(audio_for_transcription).exists():
                            raise Exception(f"音频文件不存在: {audio_for_transcription}")
                        
                        # 转录音频
                        segments = await whisper_service.transcribe_advanced(
                            str(audio_for_transcription), model_name, device, None, beam_size, "transcribe", word_timestamps
                        )
                        
                        # 调试：检查转录结果
                        Logger.info(f"转录完成，获得 {len(segments)} 个片段")
                        if segments:
                            Logger.info(f"第一个片段内容: {segments[0].text}")
                        else:
                            logger.warning("转录结果为空！")
                        
                        # 生成SRT字幕
                        srt_path = job_dir / f"{out_basename}.srt"
                        SubtitleGenerator.write_srt(segments, srt_path, bilingual=False)
                        job_manager.add_file(job_id, "srt", str(srt_path))
                        
                        # 生成双语字幕
                        if bilingual:
                            translated_segments = await whisper_service.transcribe_advanced(
                                str(audio_for_transcription), model_name, device, None, beam_size, "translate", word_timestamps
                            )
                            bilingual_srt_path = job_dir / f"{out_basename}_bilingual.srt"
                            SubtitleGenerator.write_srt(segments, bilingual_srt_path, bilingual=True, translated_segments=translated_segments)
                            job_manager.add_file(job_id, "srt_bilingual", str(bilingual_srt_path))
                    else:
                        Logger.info("跳过字幕生成，仅进行视频效果处理")
                    
                    # 处理视频输出（如果有视频输入）
                    video_output = None
                    base_video = local_input  # 基础视频文件
                    
                    # 处理分离音视频的场景：如果有独立的音频文件，需要将其合并到视频中
                    if audio_input and local_input:
                        # 合并音视频
                        merged_video_path = job_dir / f"{out_basename}_merged{local_input.suffix}"
                        try:
                            MediaProcessor.merge_audio_video(local_input, audio_input, merged_video_path)
                            base_video = merged_video_path
                            job_manager.add_file(job_id, "video_merged", str(merged_video_path))
                            Logger.info(f"音视频合并成功: {merged_video_path}")
                        except Exception as e:
                            Logger.error(f"音视频合并失败: {e}")
                            base_video = local_input  # 合并失败，使用原视频
                    
                    # 如果有视频文件，生成字幕视频
                    if base_video and FileUtils.is_video_file(str(base_video)):
                        # 获取视频时长信息（仅用于日志）
                        video_duration = MediaProcessor.get_media_duration(base_video)
                        if generate_subtitle and segments and len(segments) > 0:
                            audio_duration = max(seg.end for seg in segments)
                            Logger.info(f"视频时长: {video_duration:.2f}秒, 音频时长: {audio_duration:.2f}秒")
                        else:
                            Logger.info(f"视频时长: {video_duration:.2f}秒")
                        
                        # 根据用户选择和配置决定处理流程
                        has_effects = flower_config or image_config or watermark_config
                        
                        if generate_subtitle and burn_type == "hard" and srt_path:
                            # 需要生成硬字幕
                            # 选择要使用的SRT文件
                            srt_to_use = bilingual_srt_path if bilingual else srt_path
                            
                            # 第一步：生成硬字幕视频
                            hardsub_video = job_dir / f"{out_basename}_temp_hardsub{base_video.suffix}"
                            try:
                                MediaProcessor.burn_hardsub(base_video, srt_to_use, hardsub_video)
                                Logger.info(f"硬字幕视频生成成功: {hardsub_video}")
                                base_for_effects = hardsub_video
                            except Exception as e:
                                Logger.error(f"硬字幕视频生成失败: {e}")
                                base_for_effects = base_video  # 使用原视频作为基础
                        else:
                            # 不需要硬字幕，直接使用原视频
                            base_for_effects = base_video
                            if generate_subtitle:
                                Logger.info("跳过硬字幕生成")
                            else:
                                Logger.info("跳过字幕生成和硬字幕处理")
                        
                        # 第二步：应用视频效果（如果有配置）
                        if has_effects:
                            # 创建临时视频文件用于效果处理
                            temp_effects_video = job_dir / f"{out_basename}_temp_effects{base_video.suffix}"
                            video_output = job_dir / f"{out_basename}_effects{base_video.suffix}"
                            try:
                                # 设置job_id到VideoEffectsProcessor，用于弹跳反弹状态管理
                                VideoEffectsProcessor._current_job_id = job_id
                                success = VideoEffectsProcessor.apply_video_effects(
                                    base_for_effects, temp_effects_video,
                                    flower_config, image_config, watermark_config
                                )
                                # 清理job_id
                                VideoEffectsProcessor._current_job_id = None
                                
                                if success:
                                    # 使用FFmpeg将原始视频的音频合并到处理后的视频中
                                    try:
                                        ffmpeg_path = SystemUtils.get_ffmpeg_path()
                                        import os
                                        original_cwd = os.getcwd()
                                        
                                        # 切换到输出目录
                                        output_dir = video_output.parent
                                        os.chdir(output_dir)
                                        
                                        # 使用相对路径
                                        base_video_rel = os.path.relpath(base_for_effects, output_dir).replace('\\', '/')
                                        temp_video_rel = temp_effects_video.name
                                        output_rel = video_output.name
                                        
                                        # 使用FFmpeg合并视频流和音频流
                                        # -i base_video: 原始视频（包含音频）
                                        # -i temp_effects_video: 处理后的视频（只有视频）
                                        # -map 0:a:0 -map 1:v:0: 使用原始视频的音频和处理后的视频
                                        cmd = [
                                            ffmpeg_path, "-y",
                                            "-i", base_video_rel,
                                            "-i", temp_video_rel,
                                            "-map", "0:a:0",  # 使用第一个输入的音频
                                            "-map", "1:v:0",  # 使用第二个输入的视频
                                            "-c:a", "copy",  # 直接复制音频
                                            "-c:v", "copy",  # 直接复制视频
                                            output_rel
                                        ]
                                        
                                        # 如果是硬字幕模式，可能不需要保留音频
                                        if generate_subtitle and burn_type == "hard":
                                            # 硬字幕模式：直接使用处理后的视频
                                            shutil.copy2(temp_effects_video, video_output)
                                            Logger.info(f"视频效果应用成功（硬字幕模式，无音频）: {video_output}")
                                        else:
                                            # 非硬字幕模式：保留原始音频
                                            SystemUtils.run_cmd(cmd)
                                            Logger.info(f"视频效果应用成功，已保留原始音频: {video_output}")
                                        
                                        # 恢复工作目录
                                        os.chdir(original_cwd)
                                        
                                    except Exception as merge_error:
                                        Logger.error(f"音频合并失败: {merge_error}")
                                        # 合并失败，直接使用处理后的视频
                                        shutil.copy2(temp_effects_video, video_output)
                                        Logger.warning(f"使用无音频版本: {video_output}")
                                    
                                    job_manager.add_file(job_id, "video_effects", str(video_output))
                                else:
                                    video_output = base_for_effects
                                    if generate_subtitle and burn_type == "hard":
                                        job_manager.add_file(job_id, "video_hardsub", str(video_output))
                                    else:
                                        job_manager.add_file(job_id, "video_processed", str(video_output))
                                    logger.warning("视频效果应用失败，使用基础视频")
                            except Exception as e:
                                Logger.error(f"视频效果应用失败: {e}")
                                video_output = base_for_effects
                                if generate_subtitle and burn_type == "hard":
                                    job_manager.add_file(job_id, "video_hardsub", str(video_output))
                                else:
                                    job_manager.add_file(job_id, "video_processed", str(video_output))
                            finally:
                                # 清理临时文件
                                if temp_effects_video.exists():
                                    temp_effects_video.unlink()
                        else:
                            # 没有视频效果
                            video_output = base_for_effects
                            if generate_subtitle and burn_type == "hard":
                                job_manager.add_file(job_id, "video_hardsub", str(video_output))
                            elif has_effects is False and generate_subtitle is False:
                                # 用户明确不要字幕和效果，但仍需要输出视频
                                job_manager.add_file(job_id, "video_original", str(video_output))
                    
                    # 保存转录结果
                    if generate_subtitle and segments:
                        result = {
                            "segments": [
                                {"start": seg.start, "end": seg.end, "text": seg.text}
                                for seg in segments
                            ],
                            "transcript_text": "\n".join([seg.text for seg in segments])
                        }
                    else:
                        # 没有生成字幕，创建空结果
                        result = {
                            "segments": [],
                            "transcript_text": "未生成字幕（仅视频效果处理）"
                        }
                    job_manager.set_result(job_id, result)
                    job_manager.update_job_status(job_id, "completed")
                    
                    # 准备最终结果
                    final_job_data = job_manager.get_job(job_id)
                    transcript_text = result.get("transcript_text", "")
                    
                    # 准备文件路径而不是URL
                    srt_path = str(srt_path) if 'srt_path' in locals() and srt_path else None
                    bilingual_srt_path = str(bilingual_srt_path) if 'bilingual_srt_path' in locals() and bilingual_srt_path and bilingual else None
                    
                    # 确保video_path有效
                    if video_output and video_output.exists():
                        video_path = str(video_output)
                    elif base_video and base_video.exists():
                        # 如果没有生成新视频，返回原始视频路径
                        video_path = str(base_video)
                    else:
                        video_path = None
                    
                    # 返回最终完成的结果
                    status_html = '<div style="color: #28a745;">✅ 转录完成！</div>'
                    Logger.info(f"高级转录任务完成: {job_id}")
                    
                    return job_id, status_html, final_job_data, transcript_text, True, srt_path, bilingual_srt_path, video_path
                    
                except Exception as processing_error:
                    Logger.error(f"高级转录处理错误: {processing_error}")
                    job_manager.set_error(job_id, str(processing_error))
                    status_html = f'<div style="color: #dc3545;">❌ 处理失败: {str(processing_error)}</div>'
                    return None, status_html, {"error": str(processing_error)}, "", True, None, None, None
                    
            except Exception as e:
                # 记录详细的错误堆栈信息
                import traceback
                error_details = traceback.format_exc()
                Logger.error(f"高级转录处理异常: {e}")
                Logger.error(f"错误堆栈: {error_details}")
                status_html = f'<div style="color: #dc3545;">❌ 提交失败: {str(e)}</div>'
                return None, status_html, {"error": str(e), "traceback": error_details}, "", True, None, None, None
        
        def check_job_status(job_id):
            if not job_id:
                return {}, None, None, None
            
            try:
                # 尝试多种连接方式，确保至少一种能工作
                urls_to_try = config.get_api_urls(f"/api/job/{job_id}")
                
                response = None
                successful_url = None
                
                for url in urls_to_try:
                    try:
                        print(f"尝试连接URL: {url}")  # 调试信息
                        response = requests.get(
                            url,
                            headers={"Authorization": f"Bearer {AppConfig.API_TOKEN}"},
                            timeout=3,  # 更短的超时
                            verify=False
                        )
                        if response.status_code == 200:
                            successful_url = url
                            print(f"成功连接到: {successful_url}")  # 调试信息
                            break
                    except Exception as e:
                        print(f"连接 {url} 失败: {str(e)}")  # 调试信息
                        continue
                
                if not response or response.status_code != 200:
                    raise Exception(f"所有连接尝试都失败了，最后状态码: {response.status_code if response else 'None'}")
                
                print(f"API响应状态码: {response.status_code}")  # 调试信息
                
                if response.status_code == 200:
                    job_data = response.json()
                    status = job_data.get("status", "unknown")
                    
                    # 准备下载链接
                    srt_url = None
                    bilingual_srt_url = None
                    video_url = None
                    
                    if job_data.get("status") == "completed":
                        files = job_data.get("files", {})
                        # 生成多个下载链接，让浏览器选择可用的
                        download_hosts = ["127.0.0.1", "localhost"]
                        
                        if "srt" in files:
                            srt_url = f"http://{download_hosts[0]}:{AppConfig.PORT}/api/download/{job_id}?file=srt"
                        if "srt_bilingual" in files:
                            bilingual_srt_url = f"http://{download_hosts[0]}:{AppConfig.PORT}/api/download/{job_id}?file=srt_bilingual"
                        if "video_hardsub" in files:
                            video_url = f"http://{download_hosts[0]}:{AppConfig.PORT}/api/download/{job_id}?file=video_hardsub"
                        elif "video_softsub" in files:
                            video_url = f"http://{download_hosts[0]}:{AppConfig.PORT}/api/download/{job_id}?file=video_softsub"
                        
                        # 添加转录结果文本
                        if "result" in job_data:
                            segments = job_data["result"].get("segments", [])
                            transcript_text = "\n".join([seg["text"] for seg in segments])
                            job_data["transcript_text"] = transcript_text
                    
                    elif status == "failed":
                        # 添加错误信息
                        error_msg = job_data.get("error", "未知错误")
                        job_data["error_message"] = f"任务失败: {error_msg}"
                    
                    return job_data, srt_url, bilingual_srt_url, video_url
                else:
                    return {"error": f"API调用失败 (状态码: {response.status_code})", "details": response.text}, None, None, None
                    
            except Exception as e:
                return {"error": "连接失败", "details": str(e)}, None, None, None
        
        # 高级转录事件
        def submit_and_start_polling(*args):
            """直接执行高级转录并返回最终结果"""
            import asyncio
            import threading
            import queue
            
            try:
                # 使用线程和队列来处理异步调用
                result_queue = queue.Queue()
                
                def run_async_in_thread():
                    """在新线程中运行异步函数"""
                    try:
                        # 创建新的事件循环
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        
                        # 运行异步函数
                        result = new_loop.run_until_complete(transcribe_advanced_handler(*args))
                        result_queue.put(("success", result))
                    except Exception as e:
                        result_queue.put(("error", e))
                    finally:
                        new_loop.close()
                
                # 启动线程
                thread = threading.Thread(target=run_async_in_thread)
                thread.start()
                thread.join()  # 等待线程完成
                
                # 获取结果
                status, result = result_queue.get()
                
                if status == "error":
                    raise result
                
                # 解包结果
                job_id, status_html, job_data, transcript_text, completed, srt_path, bilingual_srt_path, video_path = result
                
                # 直接返回最终结果，无需轮询
                return (job_id, status_html, job_data, 
                       transcript_text if transcript_text else "", completed, False,
                       srt_path, bilingual_srt_path, video_path)
                
            except Exception as e:
                Logger.error(f"高级转录执行失败: {e}")
                error_html = f'<div style="color: #dc3545;">❌ 转录失败: {str(e)}</div>'
                return (None, error_html, {"error": str(e)}, "", True, False, None, None, None)
        
        transcribe_adv_btn.click(
            submit_and_start_polling,
            inputs=[input_type, video_input, audio_input_adv, video_path_input, audio_path_input,
                   model_choice_adv, device_choice, 
                   generate_subtitle, bilingual, word_timestamps, burn_type, beam_size_adv,
                   # 花字配置
                   flower_text, flower_font, flower_size, flower_color, flower_x, flower_y,
                   flower_timing_type, flower_start_frame, flower_end_frame,
                   flower_start_time, flower_end_time,
                   flower_stroke_enabled, flower_stroke_color, flower_stroke_width,
                   # 插图配置
                   image_path, image_x, image_y, image_width, image_height,
                   image_timing_type, image_start_frame, image_end_frame,
                   image_start_time, image_end_time, image_remove_bg,
                   # 水印配置
                   watermark_text, watermark_font, watermark_size, watermark_color,
                   watermark_timing_type, watermark_start_frame, watermark_end_frame,
                   watermark_start_time, watermark_end_time, watermark_style],
            outputs=[job_id_display, status_info, result_status, 
                    transcript_display, job_completed, polling_active,
                    srt_download, bilingual_srt_download, video_download]  # 添加下载文件输出
        )
        
        # 轮询机制已移除，现在直接返回最终结果
        
        def update_job_display(job_id):
            """更新任务显示的包装函数"""
            print(f"=== update_job_display 被调用，job_id: {job_id} ===")  # 调试信息
            
            if not job_id:
                print("job_id为空，返回默认值")
                return "<div>等待提交任务...</div>", {}, "", None, None, None, gr.update(visible=False)
            
            print(f"开始轮询任务状态: {job_id}")  # 调试信息
            job_data, srt_url, bilingual_srt_url, video_url = check_job_status(job_id)
            print(f"任务状态响应: {job_data.get('status', 'unknown')}")  # 调试信息
            print(f"完整响应数据: {job_data}")  # 调试信息
            
            # 提取状态信息
            status = job_data.get("status", "unknown")
            
            # 状态显示HTML
            status_html = ""
            download_links_html = ""
            
            if status == "queued":
                status_html = '<div style="color: #6c757d;">⏳ 任务排队中，请稍候...</div>'
            elif status == "running":
                status_html = '<div style="color: #007bff;">🔄 正在处理音频，请耐心等待...</div>'
            elif status == "completed":
                status_html = '<div style="color: #28a745;">✅ 任务完成！</div>'
                # 生成下载链接HTML而不是返回URL对象
                links = []
                if srt_url:
                    links.append(f'<a href="{srt_url}" download>📄 SRT字幕</a>')
                if bilingual_srt_url:
                    links.append(f'<a href="{bilingual_srt_url}" download>📄 双语SRT</a>')
                if video_url:
                    links.append(f'<a href="{video_url}" download>🎬 处理后的视频</a>')
                if links:
                    download_links_html = '<div style="margin-top: 10px;">📥 下载文件: ' + ' | '.join(links) + '</div>'
            elif status == "failed":
                error_msg = job_data.get("error_message", "处理失败")
                status_html = f'<div style="color: #dc3545;">❌ {error_msg}</div>'
            else:
                status_html = f'<div style="color: #6c757d;">📊 状态: {status}</div>'
            
            # 转录文本
            transcript_text = job_data.get("transcript_text", "")
            show_transcript = bool(transcript_text)
            
            # 将下载链接添加到状态HTML中
            if download_links_html:
                status_html += download_links_html
            
            print(f"返回状态HTML: {status_html[:50]}..., 显示转录: {show_transcript}")  # 调试信息
            
            # 返回状态HTML、job_data、转录文本，但不返回URL对象（避免Gradio尝试下载）
            return (status_html, job_data, transcript_text, 
                   None, None, None,  # 不返回URL对象
                   gr.update(visible=show_transcript))
        
        # 当job_id改变时立即更新一次
        def job_id_change_handler(job_id):
            print(f"=== job_id_display.change 被触发，job_id: {job_id} ===")
            if not job_id:
                print("job_id为空，停止轮询")
                return "<div>等待提交任务...</div>", {}, "", gr.update(visible=False), False
            
            try:
                # 立即检查一次状态，但不启动轮询
                job_data, srt_url, bilingual_srt_url, video_url = check_job_status(job_id)
                status = job_data.get("status", "unknown")
                
                # 状态显示HTML
                status_html = ""
                download_links_html = ""
                
                if status == "queued":
                    status_html = '<div style="color: #6c757d;">⏳ 任务排队中，请稍候...</div>'
                elif status == "running":
                    status_html = '<div style="color: #007bff;">🔄 正在处理音频，请耐心等待...</div>'
                elif status == "completed":
                    status_html = '<div style="color: #28a745;">✅ 任务完成！</div>'
                    links = []
                    if srt_url:
                        links.append(f'<a href="{srt_url}" download>📄 SRT字幕</a>')
                    if bilingual_srt_url:
                        links.append(f'<a href="{bilingual_srt_url}" download>📄 双语SRT</a>')
                    if video_url:
                        links.append(f'<a href="{video_url}" download>🎬 处理后的视频</a>')
                    if links:
                        download_links_html = '<div style="margin-top: 10px;">📥 下载文件: ' + ' | '.join(links) + '</div>'
                elif status == "failed":
                    error_msg = job_data.get("error_message", job_data.get("error", "处理失败"))
                    status_html = f'<div style="color: #dc3545;">❌ {error_msg}</div>'
                else:
                    status_html = f'<div style="color: #6c757d;">📊 状态: {status}</div>'
                
                transcript_text = job_data.get("transcript_text", "")
                show_transcript = bool(transcript_text)
                
                if download_links_html:
                    status_html += download_links_html
                
                return (status_html, job_data, transcript_text, 
                       gr.update(visible=show_transcript), False)
                
            except Exception as e:
                print(f"job_id_change_handler 错误: {e}")
                error_status_html = f'<div style="color: #dc3545;">❌ 状态检查失败: {str(e)}</div>'
                return (error_status_html, {}, "", gr.update(visible=False), False)
        
        job_id_display.change(
            job_id_change_handler,
            inputs=[job_id_display],
            outputs=[status_info, result_status, transcript_display, transcript_display, polling_active]
        )
        
        # 自动轮询任务状态 - 智能轮询，完成后停止
        
        def timer_tick_handler(job_id, is_polling_active):
            """定时器处理函数 - 直接处理轮询逻辑"""
            print(f"=== job_timer.tick 被触发，job_id: {job_id}, is_polling_active: {is_polling_active} ===")
            
            # 如果轮询不活跃或没有job_id，返回空值
            if not is_polling_active or not job_id:
                print("轮询不活跃或无job_id，跳过处理")
                return gr.skip()
            
            print(f"开始轮询任务状态: {job_id}")
            try:
                job_data, srt_url, bilingual_srt_url, video_url = check_job_status(job_id)
                status = job_data.get("status", "unknown")
                
                # 检查任务是否完成
                is_completed = status in ["completed", "failed"]
                print(f"任务状态: {status}, 是否完成: {is_completed}")
                
                # 状态显示HTML
                status_html = ""
                download_links_html = ""
                
                if status == "queued":
                    status_html = '<div style="color: #6c757d;">⏳ 任务排队中，请稍候...</div>'
                elif status == "running":
                    status_html = '<div style="color: #007bff;">🔄 正在处理音频，请耐心等待...</div>'
                elif status == "completed":
                    status_html = '<div style="color: #28a745;">✅ 任务完成！</div>'
                    # 生成下载链接HTML
                    links = []
                    if srt_url:
                        links.append(f'<a href="{srt_url}" download>📄 SRT字幕</a>')
                    if bilingual_srt_url:
                        links.append(f'<a href="{bilingual_srt_url}" download>📄 双语SRT</a>')
                    if video_url:
                        links.append(f'<a href="{video_url}" download>🎬 处理后的视频</a>')
                    if links:
                        download_links_html = '<div style="margin-top: 10px;">📥 下载文件: ' + ' | '.join(links) + '</div>'
                elif status == "failed":
                    error_msg = job_data.get("error_message", job_data.get("error", "处理失败"))
                    status_html = f'<div style="color: #dc3545;">❌ {error_msg}</div>'
                else:
                    status_html = f'<div style="color: #6c757d;">📊 状态: {status}</div>'
                
                # 转录文本
                transcript_text = job_data.get("transcript_text", "")
                show_transcript = bool(transcript_text)
                
                # 将下载链接添加到状态HTML中
                if download_links_html:
                    status_html += download_links_html
                
                print(f"返回状态HTML: {status_html[:50]}..., 显示转录: {show_transcript}")
                
                # 返回结果和更新后的轮询状态
                return (status_html, job_data, transcript_text, 
                       gr.update(visible=show_transcript), 
                       not is_completed)  # 如果任务完成，停止轮询
                
            except Exception as e:
                print(f"轮询过程中发生错误: {e}")
                error_status_html = f'<div style="color: #dc3545;">❌ 轮询错误: {str(e)}</div>'
                return (error_status_html, {}, "", gr.update(visible=False), False)
        
        # 轮询定时器已移除，现在直接返回最终结果
    
    return demo

# 创建Gradio界面
gradio_app = create_gradio_interface()

# 将Gradio应用挂载到FastAPI，使用标准配置
try:
    app = gr.mount_gradio_app(app, gradio_app, path="/ui")
    print("Gradio界面成功挂载到 /ui")
except Exception as e:
    print(f"Gradio挂载失败: {e}")
    print("尝试备用挂载方式...")
    try:
        # 备用挂载方式
        import gradio as gr
        app.mount("/ui", gradio_app)
        print("Gradio界面使用备用方式挂载")
    except Exception as e2:
        print(f"备用挂载也失败: {e2}")
        print("将在没有Gradio界面的情况下运行")

# 根路径重定向到Gradio界面
@app.get("/")
async def root():
    """根路径重定向到Gradio界面"""
    return HTMLResponse("""
    <html>
        <head>
            <title>Whisper 服务</title>
            <meta http-equiv="refresh" content="0; url=/ui">
        </head>
        <body>
            <p>正在重定向到 <a href="/ui">Whisper 界面</a>...</p>
        </body>
    </html>
    """)

# ----------------------------
# 启动服务
# ----------------------------
if __name__ == '__main__':
    import uvicorn
    
    # 设置环境变量避免字体和缓存问题
    os.environ['GRADIO_ANALYTICS_ENABLED'] = 'False'
    os.environ['GRADIO_SERVER_NAME'] = '0.0.0.0'  # 使用0.0.0.0避免主机名验证问题
    os.environ['GRADIO_CACHE_DIR'] = os.path.join(os.getcwd(), '.gradio_cache')
    # 禁用Gradio的各种验证
    os.environ['GRADIO_SERVER_HEADERS'] = 'Access-Control-Allow-Origin: *'
    os.environ['GRADIO_SHARE'] = 'False'
    os.environ['GRADIO_ALLOW_FLAGGING'] = 'never'
    # 尝试禁用IP验证
    os.environ['GRADIO_VALIDATE_QUEUE'] = 'False'

    #设置环境变量强制使用CPU模式
    os.environ["TORCHINDUCTOR_DISABLE"] = "1"
    
    print("=" * 60)
    print("🎙️ 整合版 Whisper 语音转文字服务")
    print("=" * 60)
    print(f"🌐 API服务地址: {config.BASE_URL}")
    print(f"📱 Gradio界面: {config.GRADIO_URL}")
    print(f"📚 API文档: {config.DOCS_URL}")
    print(f"🔑 固定Token: {config.API_TOKEN}")
    print(f"🧠 默认模型: {config.DEFAULT_MODEL}")
    print(f"💻 计算设备: {config.DEFAULT_DEVICE}")
    print(f"📁 输出目录: {config.OUTPUT_FOLDER}")
    print("=" * 60)
    print("=" * 60)
    print("默认用户账号:")
    print("  Username: admin, Password: admin123")
    print("  Username: user, Password: user123")
    print("=" * 60)
    print("提示: 字体文件404错误不影响核心功能，已自动处理")
    print("=" * 60)
    
    uvicorn.run(app, host=config.HOST, port=config.PORT)
