"""
TTS ONNX 常量管理

管理 VoxCPM-0.5B 和 VoxCPM-1.5 的版本化常量。
"""

import os
from typing import Dict

# Default constants for VoxCPM-0.5B (backward compatibility)
AUDIO_START_TOKEN = 101
CHUNK_SIZE = 640  # audio samples per latent step (16kHz version)
SAMPLE_RATE = 16000  # Default sample rate for 0.5B
MAX_THREADS = max(1, os.cpu_count() or 1)

# VoxCPM-1.5 constants
CHUNK_SIZE_15 = 1764  # audio samples per latent step (44.1kHz version)
SAMPLE_RATE_15 = 44100  # Sample rate for 1.5

__all__ = [
    "AUDIO_START_TOKEN",
    "CHUNK_SIZE",
    "SAMPLE_RATE",
    "MAX_THREADS",
    "CHUNK_SIZE_15",
    "SAMPLE_RATE_15",
    "get_constants_for_version",
]

def get_constants_for_version(version: str = "0.5B") -> Dict[str, any]:
    """
    根据版本返回对应的常量

    Args:
        version: 模型版本 ("0.5B" 或 "1.5")

    Returns:
        Dict[str, any]: 包含该版本常量的字典
    """
    if version == "1.5":
        return {
            "AUDIO_START_TOKEN": AUDIO_START_TOKEN,
            "CHUNK_SIZE": CHUNK_SIZE_15,
            "SAMPLE_RATE": SAMPLE_RATE_15,
            "MAX_THREADS": MAX_THREADS,
        }
    else:
        return {
            "AUDIO_START_TOKEN": AUDIO_START_TOKEN,
            "CHUNK_SIZE": CHUNK_SIZE,
            "SAMPLE_RATE": SAMPLE_RATE,
            "MAX_THREADS": MAX_THREADS,
        }