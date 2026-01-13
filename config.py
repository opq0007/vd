"""
配置模块

统一管理应用的所有配置参数，支持环境变量覆盖。
"""

import os
import hashlib
from pathlib import Path


class Config:
    """应用配置类 - 统一管理所有配置参数"""

    # ==================== 服务配置 ====================
    API_TOKEN = os.environ.get("API_TOKEN", "whisper-api-key-2024")
    SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production")
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", 7860))

    # ==================== URL 配置 ====================
    BASE_HOST = os.environ.get("BASE_HOST", "127.0.0.1")
    BASE_URL = f"http://{BASE_HOST}:{PORT}"
    API_BASE_URL = f"{BASE_URL}/api"
    GRADIO_URL = f"{BASE_URL}/ui"
    DOCS_URL = f"{BASE_URL}/docs"

    # ==================== Whisper 模型配置 ====================
    DEFAULT_MODEL = os.environ.get("FW_MODEL", "small")
    DEFAULT_DEVICE = os.environ.get("FW_DEVICE", "cpu")
    DEFAULT_COMPUTE = os.environ.get("FW_COMPUTE", "int8")
    CPU_THREADS = 8
    BEAM_SIZE = 5

    # ==================== 本地模型路径配置 ====================
    MODELS_DIR = os.environ.get("FW_MODELS_DIR", "models")
    USE_LOCAL_MODELS = os.environ.get("FW_USE_LOCAL_MODELS", "true").lower() == "true"

    # ==================== 文件和目录配置 ====================
    UPLOAD_FOLDER = 'uploads'
    OUTPUT_FOLDER = 'output'
    DEBUG_FOLDER = 'debug'
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

    # ==================== 任务配置 ====================
    JOB_TIMEOUT = 3600  # 1小时超时
    POLLING_INTERVAL = 2.0  # 轮询间隔（秒）

    # ==================== FFmpeg 配置 ====================
    FFMPEG_PATHS = [
        "ffmpeg",
        r"D:\programs\ffmpeg-7.1.1-full_build\bin\ffmpeg.exe"
    ]

    # ==================== 认证配置 ====================
    API_TOKENS = {
        'whisper-api-key-2024': 'automation',
        'test-token': 'test'
    }

    USERS = {
        'admin': hashlib.sha256('admin123'.encode()).hexdigest(),
        'user': hashlib.sha256('user123'.encode()).hexdigest()
    }

    # ==================== 支持的文件格式 ====================
    VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
    AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac']

    # ==================== VoxCPM 配置 ====================
    VOXCPM_MODEL_DIR = os.environ.get("VOXCPM_MODEL_DIR", os.path.join(MODELS_DIR, "OpenBMB__VoxCPM-0.5B"))
    VOXCPM_REPO_ID = os.environ.get("VOXCPM_REPO_ID", "OpenBMB/VoxCPM-0.5B")
    VOXCPM_DEFAULT_CFG = 2.0
    VOXCPM_DEFAULT_TIMESTEPS = 10

    # ==================== ASR 模型配置 ====================
    ASR_MODEL_NAME = os.environ.get("ASR_MODEL_NAME", "SenseVoiceSmall")
    ASR_MODEL_DIR = os.environ.get("ASR_MODEL_DIR", os.path.join(MODELS_DIR, "iic__" + ASR_MODEL_NAME))

    # ==================== ModelScope 配置 ====================
    MODELSCOPE_CACHE_DIR = os.environ.get("MODELSCOPE_CACHE", os.path.join(MODELS_DIR, "modelscope_cache"))

    # ==================== 日志配置 ====================
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    @classmethod
    def init_directories(cls):
        """初始化必要的目录"""
        for folder in [cls.UPLOAD_FOLDER, cls.OUTPUT_FOLDER, cls.DEBUG_FOLDER, cls.MODELS_DIR]:
            Path(folder).mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_supported_extensions(cls):
        """获取支持的文件扩展名"""
        return cls.VIDEO_EXTENSIONS + cls.AUDIO_EXTENSIONS

    @classmethod
    def get_api_urls(cls, endpoint: str):
        """获取 API 端点的多个 URL 地址"""
        return [
            f"http://127.0.0.1:{cls.PORT}{endpoint}",
            f"http://localhost:{cls.PORT}{endpoint}",
            f"http://0.0.0.0:{cls.PORT}{endpoint}",
            f"http://[::1]:{cls.PORT}{endpoint}"
        ]


# 创建全局配置实例
config = Config()
config.init_directories()