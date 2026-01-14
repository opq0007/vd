"""
VAE 编码/解码模块

提供音频 VAE 编码和解码功能。
"""

from typing import Optional
import numpy as np
import onnxruntime as ort

from .constants import CHUNK_SIZE


def get_model_input_dtype(session: ort.InferenceSession, input_name: str) -> np.dtype:
    """
    获取模型输入的数据类型

    Args:
        session: ONNX 会话
        input_name: 输入名称

    Returns:
        np.dtype: 数据类型
    """
    for inp in session.get_inputs():
        if inp.name == input_name:
            onnx_type = inp.type
            s = str(onnx_type)
            if 'tensor_type' in s:
                if 'float16' in s:
                    return np.float16
                elif 'float32' in s:
                    return np.float32
                elif 'float64' in s:
                    return np.float64
                elif 'int32' in s:
                    return np.int32
                elif 'int64' in s:
                    return np.int64
    return np.float32


def encode_audio_to_patches(vae_enc_sess: ort.InferenceSession,
                            audio: np.ndarray,
                            patch_size: int,
                            inference_dtype: np.dtype = np.float32,
                            run_options: Optional[ort.RunOptions] = None) -> np.ndarray:
    """
    音频编码为 patches

    Args:
        vae_enc_sess: VAE 编码器会话
        audio: 音频数据
        patch_size: Patch 大小
        inference_dtype: 推理数据类型
        run_options: 运行选项

    Returns:
        np.ndarray: 编码后的 patches [num_patches, patch_size, latent_dim]
    """
    patch_len = patch_size * CHUNK_SIZE
    if audio.shape[0] % patch_len != 0:
        pad_len = patch_len - (audio.shape[0] % patch_len)
        audio = np.pad(audio, (0, pad_len), mode="constant")
    vae_input_dtype = get_model_input_dtype(vae_enc_sess, "audio_data")
    inp = audio.reshape(1, 1, -1).astype(vae_input_dtype)
    z = vae_enc_sess.run(None, {"audio_data": inp}, run_options=run_options)[0]
    z = np.squeeze(z, axis=0)
    D = z.shape[0]
    L = z.shape[1]
    assert D == 64, f"Unexpected latent dim {D}"

    # Handle case where L is not divisible by patch_size
    if L % patch_size != 0:
        # Pad the latent to make it divisible by patch_size
        pad_len = patch_size - (L % patch_size)
        z = np.pad(z, ((0, 0), (0, pad_len)), mode='constant', constant_values=0)
        L = z.shape[1]
        print(f"[WARNING] Padded audio latent from {L-pad_len} to {L} (pad_len={pad_len})")

    T = L // patch_size
    patches = z.reshape(D, T, patch_size).transpose(1, 2, 0)
    if patches.shape[0] > 0:
        patches = patches[:-1, ...]
    return patches.astype(inference_dtype)


def decode_audio(vae_dec_sess: ort.InferenceSession,
                 latents: np.ndarray,
                 device_type: str = 'cpu',
                 device_id: int = 0,
                 inference_dtype: np.dtype = np.float32,
                 run_options: Optional[ort.RunOptions] = None) -> np.ndarray:
    """
    从 latents 解码音频

    Args:
        vae_dec_sess: VAE 解码器会话
        latents: 潜在表示 [batch, latent_dim, total_len]
        device_type: 设备类型
        device_id: 设备 ID
        inference_dtype: 推理数据类型
        run_options: 运行选项

    Returns:
        np.ndarray: 解码后的音频波形
    """
    if latents.shape[-1] == 0:
        return np.zeros((0,), dtype=inference_dtype)

    vae_dec_in_names = [inp.name for inp in vae_dec_sess.get_inputs()]
    vae_dec_out_names = [out.name for out in vae_dec_sess.get_outputs()]
    vae_input_dtype = get_model_input_dtype(vae_dec_sess, "z")
    latents_ort = ort.OrtValue.ortvalue_from_numpy(latents.astype(vae_input_dtype), device_type, device_id)
    input_feed_vae_dec = {vae_dec_in_names[0]: latents_ort}
    audio_out = vae_dec_sess.run_with_ort_values(vae_dec_out_names, input_feed_vae_dec)[0]
    audio = audio_out.numpy()
    audio = np.squeeze(audio, axis=1)
    audio = audio[0]
    return audio.astype(inference_dtype)


__all__ = ["get_model_input_dtype", "encode_audio_to_patches", "decode_audio"]