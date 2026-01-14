"""
输入构建模块

提供 VoxCPM 推理输入构建功能，支持 VoxCPM-0.5B 和 VoxCPM-1.5。
"""

from typing import Optional, Tuple
import time
import numpy as np
import onnxruntime as ort

from .constants import AUDIO_START_TOKEN, get_constants_for_version
from .audio_v15 import read_audio_mono
from .vae import encode_audio_to_patches


def build_inputs(tokenizer,
                 target_text: str,
                 prompt_text: str,
                 prompt_wav_path: Optional[str],
                 vae_enc_sess: ort.InferenceSession,
                 patch_size: int,
                 inference_dtype: np.dtype = np.float32,
                 run_options: Optional[ort.RunOptions] = None,
                 sample_rate: int = 16000,
                 chunk_size: int = 640
                 ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    构建 VoxCPM 推理输入，支持 VoxCPM-0.5B 和 VoxCPM-1.5

    Args:
        tokenizer: 分词器
        target_text: 目标文本
        prompt_text: 提示文本
        prompt_wav_path: 参考音频路径
        vae_enc_sess: VAE 编码器会话
        patch_size: Patch 大小 (VoxCPM-0.5B=2, VoxCPM-1.5=4)
        inference_dtype: 推理数据类型
        run_options: 运行选项
        sample_rate: 采样率 (VoxCPM-0.5B=16000, VoxCPM-1.5=44100)
        chunk_size: 音频块大小

    Returns:
        Tuple: (text_token, text_mask, audio_feat, audio_mask)
    """
    print(f"[INFO] 构建输入: patch_size={patch_size}, sample_rate={sample_rate}")

    if not prompt_wav_path:
        # 无参考音频的情况
        text = target_text
        t_tok0 = time.perf_counter()
        text_token = np.array(tokenizer(text), dtype=np.int64)
        tok_dt = time.perf_counter() - t_tok0
        print(f"[INFO] 分词耗时: {tok_dt:.3f}s，token数: {text_token.shape[0]}")
        text_token = np.concatenate([text_token, np.array([AUDIO_START_TOKEN], dtype=np.int64)], axis=-1)
        text_length = text_token.shape[0]

        # 对于不同的 patch_size，音频特征维度相同但结构不同
        audio_feat = np.zeros((text_length, patch_size, 64), dtype=inference_dtype)
        text_mask = np.ones(text_length, dtype=np.int32)
        audio_mask = np.zeros(text_length, dtype=np.int32)

        print(f"[OK] 无参考音频输入构建完成: text_length={text_length}, audio_feat_shape={audio_feat.shape}")
    else:
        # 有参考音频的情况
        text = (prompt_text or "") + (target_text or "")
        t_tok0 = time.perf_counter()
        tokenized = tokenizer(text)
        # 处理分词器返回的不同格式
        if isinstance(tokenized, dict):
            text_token = np.array(tokenized['input_ids'], dtype=np.int64)
        else:
            text_token = np.array(tokenized, dtype=np.int64)
        tok_dt = time.perf_counter() - t_tok0
        print(f"[INFO] 分词耗时: {tok_dt:.3f}s，token数: {text_token.shape[0]}")
        text_token = np.concatenate([text_token, np.array([AUDIO_START_TOKEN], dtype=np.int64)], axis=-1)
        text_length = text_token.shape[0]

        # 读取和处理音频
        t_audio0 = time.perf_counter()
        audio, sr = read_audio_mono(prompt_wav_path, target_sr=sample_rate)
        audio_dt = time.perf_counter() - t_audio0
        print(f"[AUDIO] 音频读取+重采样耗时: {audio_dt:.3f}s，采样率: {sr}，样本数: {audio.shape[0]}")

        # VAE 编码
        t_vaeenc0 = time.perf_counter()
        patches = encode_audio_to_patches(vae_enc_sess, audio, patch_size, inference_dtype, run_options)
        vae_enc_dt = time.perf_counter() - t_vaeenc0
        print(f"[VAE] VAE编码耗时: {vae_enc_dt:.3f}s，patch形状: {patches.shape}")

        audio_length = patches.shape[0]

        # 构建输入序列
        text_pad = np.zeros(audio_length, dtype=np.int64)
        text_token = np.concatenate([text_token, text_pad])
        audio_pad = np.zeros((text_length, patch_size, 64), dtype=inference_dtype)
        audio_feat = np.concatenate([audio_pad, patches], axis=0)
        text_mask = np.concatenate([np.ones(text_length), np.zeros(audio_length)]).astype(np.int32)
        audio_mask = np.concatenate([np.zeros(text_length), np.ones(audio_length)]).astype(np.int32)

        print(f"[OK] 有参考音频输入构建完成: text_length={text_length}, audio_length={audio_length}, total_shape={audio_feat.shape}")

    # 添加 batch 维度
    text_token = np.expand_dims(text_token, 0)
    text_mask = np.expand_dims(text_mask, 0)
    audio_feat = np.expand_dims(audio_feat, 0)
    audio_mask = np.expand_dims(audio_mask, 0)
    audio_feat = audio_feat.astype(inference_dtype, copy=False)

    return text_token, text_mask, audio_feat, audio_mask


def build_inputs_with_patches(tokenizer,
                              target_text: str,
                              prompt_text: str,
                              patches: np.ndarray,
                              patch_size: int,
                              inference_dtype: np.dtype = np.float32) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    使用预计算的 patches 构建输入

    Args:
        tokenizer: 分词器
        target_text: 目标文本
        prompt_text: 提示文本
        patches: 预计算的音频 patches
        patch_size: Patch 大小
        inference_dtype: 推理数据类型

    Returns:
        Tuple: (text_token, text_mask, audio_feat, audio_mask)
    """
    text = (prompt_text or "") + (target_text or "")
    t_tok0 = time.perf_counter()
    tokenized = tokenizer(text)
    # 处理分词器返回的不同格式
    if isinstance(tokenized, dict):
        text_token = np.array(tokenized['input_ids'], dtype=np.int64)
    else:
        text_token = np.array(tokenized, dtype=np.int64)
    tok_dt = time.perf_counter() - t_tok0
    print(f"[INFO] 分词耗时: {tok_dt:.3f}s，token数: {text_token.shape[0]}")
    text_token = np.concatenate([text_token, np.array([AUDIO_START_TOKEN], dtype=np.int64)], axis=-1)
    text_length = text_token.shape[0]

    audio_length = patches.shape[0]
    text_pad = np.zeros(audio_length, dtype=np.int64)
    text_token = np.concatenate([text_token, text_pad])
    audio_pad = np.zeros((text_length, patch_size, 64), dtype=inference_dtype)
    audio_feat = np.concatenate([audio_pad, patches.astype(inference_dtype)], axis=0)
    text_mask = np.concatenate([np.ones(text_length), np.zeros(audio_length)]).astype(np.int32)
    audio_mask = np.concatenate([np.zeros(text_length), np.ones(audio_length)]).astype(np.int32)

    text_token = np.expand_dims(text_token, 0)
    text_mask = np.expand_dims(text_mask, 0)
    audio_feat = np.expand_dims(audio_feat, 0)
    audio_mask = np.expand_dims(audio_mask, 0)

    return text_token, text_mask, audio_feat, audio_mask


def build_inputs_v15(tokenizer,
                     target_text: str,
                     prompt_text: str,
                     prompt_wav_path: Optional[str],
                     vae_enc_sess: ort.InferenceSession,
                     patch_size: int = 4,
                     inference_dtype: np.dtype = np.float32,
                     run_options: Optional[ort.RunOptions] = None
                     ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    VoxCPM-1.5 专用的输入构建函数

    Args:
        tokenizer: 分词器
        target_text: 目标文本
        prompt_text: 提示文本
        prompt_wav_path: 参考音频路径
        vae_enc_sess: VAE 编码器会话
        patch_size: Patch 大小 (默认为 4，适配 VoxCPM-1.5)
        inference_dtype: 推理数据类型
        run_options: 运行选项

    Returns:
        Tuple: (text_token, text_mask, audio_feat, audio_mask)
    """
    # VoxCPM-1.5 使用 44.1kHz 采样率和对应的 chunk_size
    constants = get_constants_for_version("1.5")

    return build_inputs(
        tokenizer=tokenizer,
        target_text=target_text,
        prompt_text=prompt_text,
        prompt_wav_path=prompt_wav_path,
        vae_enc_sess=vae_enc_sess,
        patch_size=patch_size,
        inference_dtype=inference_dtype,
        run_options=run_options,
        sample_rate=constants["SAMPLE_RATE"],
        chunk_size=constants["CHUNK_SIZE"]
    )


__all__ = [
    "build_inputs",
    "build_inputs_with_patches",
    "build_inputs_v15"
]