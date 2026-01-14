"""
Whisper 语音识别服务模块

提供基于 faster-whisper 的语音转文字功能，支持模型复用和多种转录模式。
"""

import os
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

from faster_whisper import WhisperModel

from config import config
from utils.logger import Logger


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

    async def _load_model(
        self,
        model_name: str = None,
        device: str = None,
        compute_type: str = None
    ):
        """
        加载 Whisper 模型（带缓存和本地模型支持）

        Args:
            model_name: 模型名称
            device: 设备类型
            compute_type: 计算类型

        Returns:
            WhisperModel: 加载的模型实例
        """
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
            local_model_path = os.path.join(self.config.MODELS_DIR, model_name)
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
                    cpu_threads=self.config.CPU_THREADS
                )
            )
            self.model_cache[cache_key] = model
            Logger.info(f"Whisper model loaded successfully: {actual_model}")
            return model
        except Exception as e:
            Logger.error(f"Failed to load Whisper model: {e}")
            raise

    async def transcribe_basic(
        self,
        audio_path: str,
        beam_size: int = None,
        model_name: str = None
    ) -> Dict[str, Any]:
        """
        基础语音转文字

        Args:
            audio_path: 音频文件路径
            beam_size: beam search 大小
            model_name: 模型名称

        Returns:
            Dict[str, Any]: 包含转录结果的字典
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        beam_size = beam_size or self.config.BEAM_SIZE

        try:
            model = await self._load_model(model_name)

            loop = asyncio.get_event_loop()
            segments, info = await loop.run_in_executor(
                None,
                lambda: model.transcribe(audio_path, beam_size=beam_size, language='zh')
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

            Logger.info(f"Basic transcription completed: {len(result['segments'])} segments, language: {info.language}")
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
            List: 转录片段列表
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
                    word_timestamps=word_timestamps,
                    language='zh'  # 强制指定为简体中文
                )
            )

            # 立即将segments转换为列表，避免生成器被消耗
            segments_list = list(segments)
            Logger.info(f"Advanced transcription completed: {len(segments_list)} segments, language: {info.language}")
            return segments_list

        except Exception as e:
            Logger.error(f"Advanced transcription error: {e}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息

        Returns:
            Dict[str, Any]: 模型信息字典
        """
        # 检查本地可用模型
        local_models = []
        if self.config.USE_LOCAL_MODELS:
            models_dir = self.config.MODELS_DIR
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
            "models_dir": self.config.MODELS_DIR,
            "use_local_models": self.config.USE_LOCAL_MODELS
        }

    def clear_cache(self):
        """清除模型缓存"""
        self.model_cache.clear()
        Logger.info("Model cache cleared")


# 创建全局服务实例
whisper_service = WhisperService()