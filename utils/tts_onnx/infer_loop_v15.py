"""
推理循环模块

提供 VoxCPM 推理循环功能，支持 VoxCPM-0.5B 和 VoxCPM-1.5。
"""

from typing import Optional
import numpy as np
import onnxruntime as ort
from tqdm import tqdm


def run_inference(prefill_sess: ort.InferenceSession,
                  decode_sess: ort.InferenceSession,
                  text_token: np.ndarray,
                  text_mask: np.ndarray,
                  audio_feat: np.ndarray,
                  audio_mask: np.ndarray,
                  min_len: int,
                  max_len: int,
                  cfg_value: float,
                  timesteps: int = 10,
                  device_type: str = 'cpu',
                  device_id: int = 0,
                  inference_dtype: np.dtype = np.float32,
                  run_options: Optional[ort.RunOptions] = None,
                  patch_size: int = 2) -> np.ndarray:
    """
    运行 VoxCPM 推理循环，支持 VoxCPM-0.5B 和 VoxCPM-1.5

    Args:
        prefill_sess: Prefill 阶段的 ONNX 会话
        decode_sess: Decode 阶段的 ONNX 会话
        text_token: 文本 token
        text_mask: 文本 mask
        audio_feat: 音频特征
        audio_mask: 音频 mask
        min_len: 最小生成长度
        max_len: 最大生成长度
        cfg_value: CFG 系数
        timesteps: Diffusion 推理步数 (VoxCPM-1.5 通常用 5, VoxCPM-0.5B 通常用 10)
        device_type: 设备类型
        device_id: 设备 ID
        inference_dtype: 推理数据类型
        run_options: 运行选项
        patch_size: Patch 大小 (VoxCPM-0.5B=2, VoxCPM-1.5=4)

    Returns:
        np.ndarray: 生成的潜在表示
    """
    prefill_in_names = [inp.name for inp in prefill_sess.get_inputs()]
    prefill_out_names = [out.name for out in prefill_sess.get_outputs()]
    decode_in_names = [inp.name for inp in decode_sess.get_inputs()]
    decode_out_names = [out.name for out in decode_sess.get_outputs()]

    # 创建 OrtValue 输入
    text_token_ort = ort.OrtValue.ortvalue_from_numpy(text_token, device_type, device_id)
    text_mask_ort = ort.OrtValue.ortvalue_from_numpy(text_mask, device_type, device_id)
    audio_feat_ort = ort.OrtValue.ortvalue_from_numpy(audio_feat.astype(inference_dtype), device_type, device_id)
    audio_mask_ort = ort.OrtValue.ortvalue_from_numpy(audio_mask, device_type, device_id)

    # Prefill 阶段输入
    input_feed_prefill = {
        prefill_in_names[0]: text_token_ort,
        prefill_in_names[1]: text_mask_ort,
        prefill_in_names[2]: audio_feat_ort,
        prefill_in_names[3]: audio_mask_ort,
    }

    # 运行 Prefill
    outputs = prefill_sess.run_with_ort_values(prefill_out_names, input_feed_prefill)

    (
        dit_hidden_ort,
        base_next_keys_ort,
        base_next_values_ort,
        residual_next_keys_ort,
        residual_next_values_ort,
        prefix_feat_cond_ort,
    ) = outputs

    pred_seq = []
    cfg_scalar = np.array(cfg_value, dtype=inference_dtype)
    cfg_scalar_ort = ort.OrtValue.ortvalue_from_numpy(cfg_scalar, device_type, device_id)

    # Decode 循环
    print(f"[INFO] 开始解码循环 (timesteps={timesteps}, patch_size={patch_size})...")

    # 根据模型版本调整最大长度
    # VoxCPM-1.5 的 token 速率更低，相同音频长度需要更多 token
    if patch_size == 4:  # VoxCPM-1.5
        # 由于 token 速率从 12.5Hz 降低到 6.25Hz，需要调整生成长度
        effective_max_len = max_len
        print(f"[INFO] VoxCPM-1.5 检测到，使用 patch_size={patch_size}")
    else:  # VoxCPM-0.5B
        effective_max_len = max_len
        print(f"[INFO] VoxCPM-0.5B 检测到，使用 patch_size={patch_size}")

    for step in tqdm(range(effective_max_len), desc="Decoding", unit="step"):
        # 生成噪声 (适配不同的 patch_size)
        noise_shape = prefix_feat_cond_ort.shape()
        noise = np.random.randn(*noise_shape).astype(inference_dtype)
        noise_ort = ort.OrtValue.ortvalue_from_numpy(noise, device_type, device_id)

        # Decode 阶段输入
        input_feed_decode = {
            decode_in_names[0]: dit_hidden_ort,
            decode_in_names[1]: base_next_keys_ort,
            decode_in_names[2]: base_next_values_ort,
            decode_in_names[3]: residual_next_keys_ort,
            decode_in_names[4]: residual_next_values_ort,
            decode_in_names[5]: prefix_feat_cond_ort,
            decode_in_names[6]: noise_ort,
            decode_in_names[7]: cfg_scalar_ort,
        }

        # 运行 Decode 步骤
        dec_out = decode_sess.run_with_ort_values(decode_out_names, input_feed_decode)

        (
            pred_feat_ort,
            new_dit_hidden_ort,
            new_base_next_keys_ort,
            new_base_next_values_ort,
            new_residual_next_keys_ort,
            new_residual_next_values_ort,
            stop_flag_ort,
        ) = dec_out

        # 保存预测特征
        pred_feat = pred_feat_ort.numpy()
        pred_seq.append(pred_feat)

        # 更新状态
        prefix_feat_cond_ort = pred_feat_ort
        dit_hidden_ort = new_dit_hidden_ort
        base_next_keys_ort = new_base_next_keys_ort
        base_next_values_ort = new_base_next_values_ort
        residual_next_keys_ort = new_residual_next_keys_ort
        residual_next_values_ort = new_residual_next_values_ort

        # 检查停止条件
        flag = bool(stop_flag_ort.numpy().reshape(-1)[0])
        if len(pred_seq) > min_len and flag:
            print(f"[OK] 停止标志检测到，在第 {step+1} 步停止生成")
            break

    # 处理输出序列
    if len(pred_seq) == 0:
        print("[WARNING] 警告：没有生成任何特征，返回零张量")
        return np.zeros((1, 64, 0), dtype=inference_dtype)

    # 重塑序列 [batch, seq_len, patch_size, feat_dim] -> [batch, feat_dim, total_len]
    seq = np.concatenate([s[np.newaxis, ...] for s in pred_seq], axis=1)  # [1, T, patch_size, feat_dim]
    seq = np.transpose(seq, (0, 3, 1, 2))  # [1, feat_dim, T, patch_size]
    B, D, T, P = seq.shape

    # 展平最后两个维度
    result = seq.reshape(B, D, T * P).astype(inference_dtype)

    print(f"[OK] 解码完成: 生成了 {len(pred_seq)} 个 patch, 总维度 {result.shape}")

    return result


__all__ = ["run_inference"]