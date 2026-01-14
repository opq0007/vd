"""
音频处理模块

提供音频读取、重采样和验证功能。
"""

from typing import Tuple
import numpy as np
import soundfile as sf

from .constants import SAMPLE_RATE, get_constants_for_version


def resample_audio_linear(audio: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    """
    使用线性插值重采样音频

    Args:
        audio: 输入音频数组
        sr_in: 输入采样率
        sr_out: 输出采样率

    Returns:
        np.ndarray: 重采样后的音频
    """
    if sr_in == sr_out:
        return audio

    duration = audio.shape[0] / float(sr_in)
    new_len = int(round(duration * sr_out))
    x_old = np.linspace(0.0, duration, num=audio.shape[0], endpoint=False)
    x_new = np.linspace(0.0, duration, num=new_len, endpoint=False)
    return np.interp(x_new, x_old, audio).astype(np.float32)


def read_audio_mono(path: str, target_sr: int = SAMPLE_RATE) -> Tuple[np.ndarray, int]:
    """
    读取单声道音频并重采样到目标采样率

    Args:
        path: 音频文件路径
        target_sr: 目标采样率 (默认为常量中的采样率)

    Returns:
        Tuple[np.ndarray, int]: (音频数组, 采样率)
    """
    audio, sr = sf.read(path, always_2d=False)

    # 转换为单声道
    if audio.ndim == 2:
        audio = audio.mean(axis=1)

    # 重采样到目标采样率
    if sr != target_sr:
        print(f"[INFO] 重采样: {sr}Hz -> {target_sr}Hz")
        audio = resample_audio_linear(audio, sr, target_sr)
        sr = target_sr

    audio = audio.astype(np.float32, copy=False)
    return audio, sr


def read_audio_mono_v15(path: str) -> Tuple[np.ndarray, int]:
    """
    VoxCPM-1.5 专用的音频读取函数 (44.1kHz)

    Args:
        path: 音频文件路径

    Returns:
        Tuple[np.ndarray, int]: (音频数组, 采样率)
    """
    constants = get_constants_for_version("1.5")
    return read_audio_mono(path, target_sr=constants["SAMPLE_RATE"])


def read_audio_mono_v05b(path: str) -> Tuple[np.ndarray, int]:
    """
    VoxCPM-0.5B 专用的音频读取函数 (16kHz)

    Args:
        path: 音频文件路径

    Returns:
        Tuple[np.ndarray, int]: (音频数组, 采样率)
    """
    constants = get_constants_for_version("0.5B")
    return read_audio_mono(path, target_sr=constants["SAMPLE_RATE"])


def validate_audio_length(audio: np.ndarray, sample_rate: int, max_seconds: int = 30) -> bool:
    """
    验证音频长度是否在合理范围内

    Args:
        audio: 音频数组
        sample_rate: 采样率
        max_seconds: 最大允许秒数

    Returns:
        bool: 是否有效
    """
    duration = len(audio) / sample_rate
    return 0 < duration <= max_seconds


def get_audio_info(audio: np.ndarray, sample_rate: int) -> dict:
    """
    获取音频信息

    Args:
        audio: 音频数组
        sample_rate: 采样率

    Returns:
        dict: 音频信息
    """
    duration = len(audio) / sample_rate
    return {
        "duration_seconds": duration,
        "sample_rate": sample_rate,
        "num_samples": len(audio),
        "max_amplitude": np.max(np.abs(audio)),
        "rms": np.sqrt(np.mean(audio ** 2))
    }


__all__ = [
    "read_audio_mono",
    "read_audio_mono_v15",
    "read_audio_mono_v05b",
    "resample_audio_linear",
    "validate_audio_length",
    "get_audio_info"
]