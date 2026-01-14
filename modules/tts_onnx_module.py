"""
TTS ONNX 模块

基于 VoxCPM-1.5 ONNX 的语音合成模块，支持参考音频克隆声音。
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

import numpy as np
import soundfile as sf

from config import config
from utils.logger import Logger
from utils.file_utils import FileUtils

from utils.tts_onnx import (
    get_constants_for_version,
    create_session_options,
    create_run_options,
    configure_providers,
    create_session,
    get_device_info_from_providers,
    load_tokenizer,
    build_inputs_v15,
    build_inputs_with_patches,
    run_inference,
    decode_audio,
    encode_audio_to_patches,
    init_db,
    save_ref_features,
    load_ref_features,
)


class TTSOnnxModule:
    """VoxCPM-1.5 ONNX 语音合成服务类"""

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.config = config
            self.model_version = "1.5"  # VoxCPM-1.5
            self.tokenizer = None
            self.prefill_sess = None
            self.decode_sess = None
            self.vae_enc_sess = None
            self.vae_dec_sess = None
            self.providers = None
            self.provider_options = None
            self.session_opts = None
            self.run_opts = None
            self.patch_size = 4  # VoxCPM-1.5 使用 patch_size=4
            self.sample_rate = 44100  # VoxCPM-1.5 使用 44.1kHz
            self.device_type = 'cpu'
            self.device_id = 0
            self.models_dir = None
            self.sqlite_path = None
            self.initialized = False

    async def initialize(self):
        """初始化 TTS 模型"""
        if self.initialized:
            return

        try:
            # 获取配置
            self.models_dir = self._resolve_model_dir()
            self.sqlite_path = self.config.VOX_ONNX_SQLITE_PATH

            Logger.info(f"VoxCPM-1.5 ONNX 模型目录: {self.models_dir}")
            Logger.info(f"SQLite 数据库路径: {self.sqlite_path}")

            # 初始化数据库
            init_db(self.sqlite_path)

            # 加载分词器
            Logger.info("加载分词器...")
            self.tokenizer = load_tokenizer(self.models_dir)

            # 配置 ONNX Runtime
            constants = get_constants_for_version(self.model_version)
            self.providers, self.provider_options = configure_providers(
                self.config.VOX_ONNX_DEVICE,
                constants["MAX_THREADS"],
                self.config.VOX_ONNX_DEVICE_ID
            )
            self.session_opts = create_session_options(
                constants["MAX_THREADS"],
                self.config.VOX_ONNX_OPTIMIZE
            )
            self.run_opts = create_run_options()

            # 获取设备信息
            self.device_type, self.device_id = get_device_info_from_providers(
                self.providers,
                self.config.VOX_ONNX_DEVICE_ID
            )

            # 加载 ONNX 模型
            Logger.info("加载 ONNX 模型...")
            self.prefill_sess = create_session(
                os.path.join(self.models_dir, "voxcpm_prefill.onnx"),
                self.session_opts,
                self.providers,
                self.provider_options
            )
            Logger.info("  - Prefill 模型加载完成")

            self.decode_sess = create_session(
                os.path.join(self.models_dir, "voxcpm_decode_step.onnx"),
                self.session_opts,
                self.providers,
                self.provider_options
            )
            Logger.info("  - Decode 模型加载完成")

            self.vae_enc_sess = create_session(
                os.path.join(self.models_dir, "audio_vae_encoder.onnx"),
                self.session_opts,
                self.providers,
                self.provider_options
            )
            Logger.info("  - VAE 编码器加载完成")

            self.vae_dec_sess = create_session(
                os.path.join(self.models_dir, "audio_vae_decoder.onnx"),
                self.session_opts,
                self.providers,
                self.provider_options
            )
            Logger.info("  - VAE 解码器加载完成")

            # 设置数据类型
            self.inference_dtype = {
                "fp32": np.float32,
                "fp16": np.float16,
                "bf16": np.float32,
            }.get(self.config.VOX_ONNX_DTYPE, np.float32)

            Logger.info(f"VoxCPM-1.5 ONNX TTS 模块初始化成功")
            Logger.info(f"  - 设备: {self.device_type}:{self.device_id}")
            Logger.info(f"  - 采样率: {self.sample_rate}Hz")
            Logger.info(f"  - Patch Size: {self.patch_size}")
            Logger.info(f"  - 数据类型: {self.config.VOX_ONNX_DTYPE}")

            self.initialized = True

        except Exception as e:
            Logger.error(f"VoxCPM-1.5 ONNX TTS 模块初始化失败: {e}")
            raise

    def _resolve_model_dir(self) -> str:
        """
        解析模型目录路径

        Returns:
            str: 模型目录路径
        """
        # 优先使用配置的模型目录
        if os.path.isdir(self.config.VOX_ONNX_MODELS_DIR):
            return self.config.VOX_ONNX_MODELS_DIR

        # 检查 vox-onnx 目录下的模型
        vox_onnx_models = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vox-onnx", "models", "onnx_models_v15")
        if os.path.isdir(vox_onnx_models):
            return vox_onnx_models

        # 检查项目根目录下的模型
        project_root = Path(__file__).resolve().parent.parent.parent
        root_models = project_root / "vox-onnx" / "models" / "onnx_models_v15"
        if root_models.exists():
            return str(root_models)

        # 默认路径
        return self.config.VOX_ONNX_MODELS_DIR

    async def synthesize(
        self,
        text: str,
        prompt_wav: Optional[str] = None,
        prompt_text: Optional[str] = None,
        feat_id: Optional[str] = None,
        cfg_value: float = 2.0,
        min_len: int = 2,
        max_len: int = 2000,
        timesteps: int = 5,
        output_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        语音合成

        Args:
            text: 要合成的文本
            prompt_wav: 参考音频路径
            prompt_text: 参考文本
            feat_id: 预编码特征 ID
            cfg_value: CFG 引导强度
            min_len: 最小生成长度
            max_len: 最大生成长度
            timesteps: Diffusion 推理步数
            output_path: 输出文件路径

        Returns:
            Dict[str, Any]: 合成结果
        """
        if not self.initialized:
            await self.initialize()

        try:
            # 构建输入
            if feat_id is not None:
                # 使用预编码特征
                Logger.info(f"使用预编码特征: {feat_id}")
                patches, patch_size, stored_prompt_text, _ = load_ref_features(self.sqlite_path, feat_id)
                text_token, text_mask, audio_feat, audio_mask = build_inputs_with_patches(
                    self.tokenizer,
                    target_text=text,
                    prompt_text=prompt_text or stored_prompt_text,
                    patches=patches,
                    patch_size=patch_size,
                    inference_dtype=self.inference_dtype
                )
            elif prompt_wav is not None:
                # 使用参考音频
                Logger.info(f"使用参考音频: {prompt_wav}")
                text_token, text_mask, audio_feat, audio_mask = build_inputs_v15(
                    self.tokenizer,
                    target_text=text,
                    prompt_text=prompt_text or "",
                    prompt_wav_path=prompt_wav,
                    vae_enc_sess=self.vae_enc_sess,
                    patch_size=self.patch_size,
                    inference_dtype=self.inference_dtype,
                    run_options=self.run_opts
                )
            else:
                # 无参考音频
                Logger.info("无参考音频模式")
                text_token, text_mask, audio_feat, audio_mask = build_inputs_v15(
                    self.tokenizer,
                    target_text=text,
                    prompt_text="",
                    prompt_wav_path=None,
                    vae_enc_sess=self.vae_enc_sess,
                    patch_size=self.patch_size,
                    inference_dtype=self.inference_dtype,
                    run_options=self.run_opts
                )

            # 运行推理
            Logger.info("开始推理...")
            latents = run_inference(
                self.prefill_sess,
                self.decode_sess,
                text_token,
                text_mask,
                audio_feat,
                audio_mask,
                min_len=min_len,
                max_len=max_len,
                cfg_value=cfg_value,
                timesteps=timesteps,
                device_type=self.device_type,
                device_id=self.device_id,
                inference_dtype=self.inference_dtype,
                run_options=self.run_opts,
                patch_size=self.patch_size
            )

            # 解码音频
            Logger.info("解码音频...")
            audio = decode_audio(
                self.vae_dec_sess,
                latents,
                device_type=self.device_type,
                device_id=self.device_id,
                inference_dtype=self.inference_dtype,
                run_options=self.run_opts
            )

            # 保存音频
            if output_path is None:
                output_path = FileUtils.create_job_dir() / f"tts_onnx_{FileUtils.generate_job_id()}.wav"

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            sf.write(str(output_path), audio, self.sample_rate)

            duration = len(audio) / float(self.sample_rate)

            Logger.info(f"TTS 合成完成: {output_path}, 时长: {duration:.2f}s")

            return {
                "success": True,
                "output_path": str(output_path),
                "text": text,
                "duration": duration,
                "sample_rate": self.sample_rate,
                "num_samples": len(audio)
            }

        except Exception as e:
            Logger.error(f"TTS 合成失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }

    async def save_ref_audio(
        self,
        feat_id: str,
        prompt_audio_path: str,
        prompt_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        保存参考音频特征

        Args:
            feat_id: 特征 ID
            prompt_audio_path: 参考音频路径
            prompt_text: 参考文本

        Returns:
            Dict[str, Any]: 保存结果
        """
        if not self.initialized:
            await self.initialize()

        try:
            # 读取音频
            audio, sr = sf.read(prompt_audio_path, always_2d=False)
            if audio.ndim == 2:
                audio = audio.mean(axis=1)

            # 重采样到 44.1kHz
            if sr != self.sample_rate:
                from utils.tts_onnx.audio_v15 import resample_audio_linear
                audio = resample_audio_linear(audio, sr, self.sample_rate)

            # 编码为 patches
            patches = encode_audio_to_patches(
                self.vae_enc_sess,
                audio,
                self.patch_size,
                self.inference_dtype,
                self.run_opts
            )

            # 保存到数据库
            save_ref_features(
                self.sqlite_path,
                feat_id,
                prompt_text or "",
                self.patch_size,
                self.config.VOX_ONNX_DTYPE,
                patches
            )

            Logger.info(f"参考音频特征保存成功: {feat_id}, patches_shape: {patches.shape}")

            return {
                "success": True,
                "feat_id": feat_id,
                "patches_shape": patches.shape.tolist()
            }

        except Exception as e:
            Logger.error(f"保存参考音频特征失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }

    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息

        Returns:
            Dict[str, Any]: 模型信息
        """
        return {
            "initialized": self.initialized,
            "model_version": self.model_version,
            "device": f"{self.device_type}:{self.device_id}",
            "models_dir": self.models_dir,
            "sqlite_path": self.sqlite_path,
            "sample_rate": self.sample_rate,
            "patch_size": self.patch_size,
            "dtype": self.config.VOX_ONNX_DTYPE,
            "optimize": self.config.VOX_ONNX_OPTIMIZE
        }

    def list_ref_features(self) -> Dict[str, Any]:
        """
        获取所有已保存的参考音频特征

        Returns:
            Dict[str, Any]: 特征列表
        """
        import sqlite3
        from datetime import datetime

        try:
            # 如果未初始化，使用配置中的路径
            if self.sqlite_path is None:
                self.sqlite_path = self.config.VOX_ONNX_SQLITE_PATH

            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.execute(
                "SELECT id, prompt_text, patch_size, dtype, created_at FROM ref_features ORDER BY created_at DESC"
            )
            rows = cursor.fetchall()
            conn.close()

            features = []
            for row in rows:
                feat_id, prompt_text, patch_size, dtype, created_at = row
                created_time = datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
                features.append({
                    "feat_id": feat_id,
                    "prompt_text": prompt_text,
                    "patch_size": patch_size,
                    "dtype": dtype,
                    "created_at": created_time
                })

            return {
                "success": True,
                "count": len(features),
                "features": features
            }

        except Exception as e:
            Logger.error(f"获取特征列表失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "features": []
            }


# 创建全局服务实例
tts_onnx_module = TTSOnnxModule()