"""
TTS ONNX 工具模块

提供 VoxCPM-1.5 ONNX 推理所需的核心工具函数和类。
"""

__all__ = [
    "get_constants_for_version",
    "create_session_options",
    "create_run_options",
    "configure_providers",
    "create_session",
    "get_device_info_from_providers",
    "read_audio_mono",
    "read_audio_mono_v15",
    "encode_audio_to_patches",
    "decode_audio",
    "build_inputs",
    "build_inputs_with_patches",
    "build_inputs_v15",
    "run_inference",
    "load_tokenizer",
    "mask_multichar_chinese_tokens",
    "init_db",
    "save_ref_features",
    "load_ref_features",
]

from .constants import get_constants_for_version
from .runtime import (
    create_session_options,
    create_run_options,
    configure_providers,
    create_session,
    get_device_info_from_providers,
)
from .audio_v15 import read_audio_mono, read_audio_mono_v15
from .vae import encode_audio_to_patches, decode_audio
from .inputs_v15 import build_inputs, build_inputs_with_patches, build_inputs_v15
from .infer_loop_v15 import run_inference
from .tokenize import load_tokenizer, mask_multichar_chinese_tokens
from .store import init_db, save_ref_features, load_ref_features