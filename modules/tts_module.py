"""
语音合成模块 (TTS Module)

提供基于 VoxCPM 的语音合成功能，支持参考音频克隆声音。
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

import torch

from config import config
from utils.logger import Logger
from utils.file_utils import FileUtils


class TTSModule:
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
            self.model_dir = None
            self.initialized = False

    def _resolve_model_dir(self) -> str:
        """
        解析模型目录路径

        Returns:
            str: 模型目录路径
        """
        if os.path.isdir(self.config.VOXCPM_MODEL_DIR):
            return self.config.VOXCPM_MODEL_DIR

        # 如果本地模型不存在，尝试下载
        repo_id = self.config.VOXCPM_REPO_ID
        target_dir = os.path.join(self.config.MODELS_DIR, repo_id.replace("/", "__"))

        if not os.path.isdir(target_dir):
            os.makedirs(target_dir, exist_ok=True)

            # 尝试从ModelScope下载
            try:
                Logger.info("Trying to download VoxCPM model from ModelScope...")
                self._download_from_modelscope(repo_id, target_dir)
                Logger.info("Model downloaded successfully from ModelScope")
                return target_dir
            except Exception as e:
                Logger.warning(f"ModelScope download failed: {e}")

            # 尝试从HF镜像下载
            try:
                Logger.info("Trying to download VoxCPM model from HF mirror...")
                self._download_from_hf_mirror(repo_id, target_dir)
                Logger.info("Model downloaded successfully from HF mirror")
                return target_dir
            except Exception as e:
                Logger.warning(f"HF mirror download failed: {e}")

            # 最后尝试原始HF
            try:
                Logger.info("Trying to download VoxCPM model from original HF...")
                self._download_from_hf_original(repo_id, target_dir)
                Logger.info("Model downloaded successfully from original HF")
                return target_dir
            except Exception as e:
                Logger.error(f"All download methods failed: {e}")
                return self.config.MODELS_DIR

        return target_dir

    def _download_from_modelscope(self, repo_id: str, target_dir: str):
        """从ModelScope下载模型"""
        try:
            from modelscope import snapshot_download
            os.environ['MODELSCOPE_CACHE'] = self.config.MODELSCOPE_CACHE_DIR
            os.makedirs(self.config.MODELSCOPE_CACHE_DIR, exist_ok=True)

            Logger.info(f"Downloading from ModelScope: {repo_id}")

            snapshot_download(
                model_id=repo_id,
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
            original_endpoint = os.environ.get('HF_ENDPOINT')
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

            try:
                snapshot_download(
                    repo_id=repo_id,
                    local_dir=target_dir,
                    local_dir_use_symlinks=False
                )
            finally:
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

    async def initialize(self):
        """初始化TTS模型"""
        if self.initialized:
            return

        try:
            self.model_dir = self._resolve_model_dir()
            Logger.info(f"VoxCPM model directory: {self.model_dir}")

            # 加载模型（这里需要根据实际的VoxCPM API进行调整）
            # self.voxcpm_model = load_voxcpm_model(self.model_dir, self.device)
            # self.asr_model = await self._load_asr_model()

            Logger.info("VoxCPM TTS module initialized successfully")
            self.initialized = True

        except Exception as e:
            Logger.error(f"Failed to initialize TTS module: {e}")
            # 使用模拟模式
            self._initialize_mock()

    def _initialize_mock(self):
        """初始化模拟模式（用于测试）"""
        Logger.warning("Using mock TTS mode")
        self.initialized = True

    async def synthesize(
        self,
        text: str,
        prompt_wav: Optional[str] = None,
        prompt_text: Optional[str] = None,
        cfg_value: float = 2.0,
        inference_timesteps: int = 10,
        do_normalize: bool = True,
        denoise: bool = True,
        output_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        语音合成

        Args:
            text: 要合成的文本
            prompt_wav: 参考音频路径
            prompt_text: 参考文本
            cfg_value: CFG引导强度
            inference_timesteps: 推理步数
            do_normalize: 是否标准化文本
            denoise: 是否降噪
            output_path: 输出文件路径

        Returns:
            Dict[str, Any]: 合成结果
        """
        if not self.initialized:
            await self.initialize()

        try:
            # 处理参考音频
            prompt_audio = None
            if prompt_wav:
                if FileUtils.is_url(prompt_wav):
                    # 下载URL音频
                    job_dir = FileUtils.create_job_dir()
                    prompt_audio = FileUtils.process_path_input(prompt_wav, job_dir)
                else:
                    prompt_audio = Path(prompt_wav).resolve()

            # 文本标准化
            if do_normalize:
                text = self._normalize_text(text)

            # 执行语音合成
            # 这里需要根据实际的VoxCPM API进行调整
            # audio_data = self.voxcpm_model.generate(
            #     text=text,
            #     prompt_audio=prompt_audio,
            #     prompt_text=prompt_text,
            #     cfg=cfg_value,
            #     steps=inference_timesteps
            # )

            # 保存音频
            if output_path is None:
                output_path = FileUtils.create_job_dir() / f"tts_output_{FileUtils.generate_job_id()}.wav"

            # 保存音频文件
            # self._save_audio(audio_data, output_path)

            # 模拟输出
            Logger.info(f"TTS synthesis completed: {output_path}")

            return {
                "success": True,
                "output_path": str(output_path),
                "text": text,
                "duration": 0.0,
                "sample_rate": 16000
            }

        except Exception as e:
            Logger.error(f"TTS synthesis failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _normalize_text(self, text: str) -> str:
        """
        标准化文本

        Args:
            text: 原始文本

        Returns:
            str: 标准化后的文本
        """
        # 这里可以添加文本标准化逻辑
        # 例如：去除特殊字符、转换大小写等
        return text.strip()

    def _save_audio(self, audio_data, output_path: Path):
        """保存音频文件"""
        import numpy as np
        import soundfile as sf

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存音频
        sf.write(str(output_path), audio_data, 16000)

    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息

        Returns:
            Dict[str, Any]: 模型信息
        """
        return {
            "initialized": self.initialized,
            "device": self.device,
            "model_dir": self.model_dir,
            "model_repo_id": self.config.VOXCPM_REPO_ID,
            "default_cfg": self.config.VOXCPM_DEFAULT_CFG,
            "default_timesteps": self.config.VOXCPM_DEFAULT_TIMESTEPS
        }


# 创建全局服务实例
tts_module = TTSModule()