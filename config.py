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
    API_TOKEN = os.environ.get("API_TOKEN", "opq#key")
    SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production")
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", 7860))
    ENABLE_GRADIO_UI = os.environ.get("ENABLE_GRADIO_UI", "true").lower() in ("true", "1", "yes")
    ENABLE_TOKEN_AUTH = os.environ.get("ENABLE_TOKEN_AUTH", "true").lower() in ("true", "1", "yes")
    BASE_URL = f"http://{HOST}:{PORT}"
    DOCS_URL = f"http://{HOST}:{PORT}/docs"
    GRADIO_URL = f"http://{HOST}:{PORT}"
    GRADIO_USERNAME = os.environ.get("GRADIO_USERNAME", "admin")
    GRADIO_PASSWORD = os.environ.get("GRADIO_PASSWORD", "admin")
    GRADIO_AUTH_TIMEOUT = int(os.environ.get("GRADIO_AUTH_TIMEOUT", "86400"))

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
    API_TOKEN = os.environ.get("API_TOKEN", "opq#key")
    API_TOKENS = {
        'opq#key': 'automation'
    }

    # ==================== 支持的文件格式 ====================
    VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
    AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac']

# ==================== VoxCPM-ONNX 配置 ====================
    VOX_ONNX_MODELS_DIR = os.environ.get("VOX_ONNX_MODELS_DIR", os.path.join(MODELS_DIR, "onnx_models_v15"))
    VOX_ONNX_DEVICE = os.environ.get("VOX_ONNX_DEVICE", "cpu")
    VOX_ONNX_DEVICE_ID = int(os.environ.get("VOX_ONNX_DEVICE_ID", "0"))
    VOX_ONNX_OPTIMIZE = os.environ.get("VOX_ONNX_OPTIMIZE", "1").lower() in ("1", "true", "yes")
    VOX_ONNX_DTYPE = os.environ.get("VOX_ONNX_DTYPE", "fp32")
    VOX_ONNX_SQLITE_PATH = os.environ.get("VOX_ONNX_SQLITE_PATH", os.path.join(MODELS_DIR, "voxcpm_ref.db"))
    VOX_ONNX_DEFAULT_CFG = 2.0
    VOX_ONNX_DEFAULT_TIMESTEPS = 5  # VoxCPM-1.5 默认使用 5 timesteps

    # ==================== ASR 模型配置 ====================
    ASR_MODEL_NAME = os.environ.get("ASR_MODEL_NAME", "SenseVoiceSmall")
    ASR_MODEL_DIR = os.environ.get("ASR_MODEL_DIR", os.path.join(MODELS_DIR, "iic__" + ASR_MODEL_NAME))

    # ==================== ModelScope 配置 ====================
    MODELSCOPE_CACHE_DIR = os.environ.get("MODELSCOPE_CACHE", os.path.join(MODELS_DIR, "modelscope_cache"))

    # ==================== 日志配置 ====================
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # ==================== LLM 配置 ====================
    # 通用 LLM 配置（支持 OpenAI 兼容接口）
    LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
    LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/chat/completions")
    LLM_MODEL = os.environ.get("LLM_MODEL", "glm-4.7")
    LLM_TEMPERATURE = 0.3
    LLM_MAX_TOKENS = 8000

    # 向后兼容：智谱 AI 配置（如果未设置 LLM_*，则使用 ZHIPU_* 作为备选）
    if not LLM_API_KEY:
        LLM_API_KEY = os.environ.get("ZHIPU_API_KEY", "")
    if "open.bigmodel.cn" in LLM_BASE_URL and not os.environ.get("LLM_BASE_URL"):
        # 默认值保持智谱
        LLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    if LLM_MODEL == "glm-4.5-flash" and not os.environ.get("LLM_MODEL"):
        LLM_MODEL = os.environ.get("ZHIPU_MODEL", "glm-4.5-flash")

    # 保留旧配置以供参考（废弃但保留兼容性）
    ZHIPU_API_KEY = LLM_API_KEY  # 兼容性：指向 LLM_API_KEY
    ZHIPU_API_URL = LLM_BASE_URL  # 兼容性：指向 LLM_BASE_URL
    ZHIPU_MODEL = LLM_MODEL  # 兼容性：指向 LLM_MODEL
    ZHIPU_TEMPERATURE = LLM_TEMPERATURE
    ZHIPU_MAX_TOKENS = LLM_MAX_TOKENS

    # ==================== 文件持久化配置 ====================
    # HuggingFace Token - 从 https://huggingface.co/settings/tokens 获取
    HUGGINGFACE_TOKEN = os.environ.get("HUGGINGFACE_TOKEN", "")
    # ModelScope Token - 从 https://modelscope.cn/my/myaccesstoken 获取
    MODELSCOPE_TOKEN = os.environ.get("MODELSCOPE_TOKEN", "")

    # ==================== ComfyUI 配置 ====================
    # ComfyUI 服务器地址
    COMFYUI_SERVER_URL = os.environ.get("COMFYUI_SERVER_URL", "http://127.0.0.1:8188")
    # ComfyUI 默认认证 Token（Bearer token）
    COMFYUI_AUTH_TOKEN = os.environ.get("COMFYUI_AUTH_TOKEN", "")
    # ComfyUI 工作流执行超时时间（秒）
    COMFYUI_TIMEOUT = int(os.environ.get("COMFYUI_TIMEOUT", "300"))

    # ==================== 邮件发送配置 ====================
    # SMTP 服务器配置
    # 注意：QQ邮箱使用授权码登录，不是QQ密码
    # 授权码获取方式：QQ邮箱 -> 设置 -> 账户 -> POP3/SMTP服务 -> 生成授权码
    EMAIL_SMTP_HOST = os.environ.get("EMAIL_SMTP_HOST", "smtp.qq.com")
    EMAIL_SMTP_PORT = int(os.environ.get("EMAIL_SMTP_PORT", "465"))  # 465(SSL) 或 587(STARTTLS)
    EMAIL_SMTP_USE_TLS = os.environ.get("EMAIL_SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
    # 发件人邮箱配置
    EMAIL_FROM_ADDRESS = os.environ.get("EMAIL_FROM_ADDRESS", "")  # 完整的QQ邮箱地址，如 123456@qq.com
    EMAIL_FROM_PASSWORD = os.environ.get("EMAIL_FROM_PASSWORD", "")  # 授权码，不是QQ密码
    EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "整合版 Whisper 服务")
    # 邮件发送超时时间（秒）
    EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "300"))

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