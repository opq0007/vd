"""
语音合成 UI 组件

提供 VoxCPM-1.5 ONNX 语音合成界面。
"""

import gradio as gr
from typing import Tuple, Optional

from modules.tts_onnx_module import tts_onnx_module
from utils.logger import Logger


def create_tts_interface() -> gr.Blocks:
    """
    创建语音合成界面

    Returns:
        gr.Blocks: Gradio 界面块
    """
    with gr.Blocks() as tts_interface:
        gr.Markdown("## 🎤 VoxCPM-1.5 语音合成 (ONNX)")
        gr.Markdown("使用 VoxCPM-1.5 ONNX 模型进行高质量语音合成，支持 44.1kHz 音频，支持参考音频克隆声音")

        with gr.Row():
            with gr.Column():
                # 输入区域
                gr.Markdown("### 📝 输入文本")
                text_input = gr.Textbox(
                    value="你好，这是一个测试文本。",
                    label="目标文本",
                    placeholder="请输入要合成的文本...",
                    lines=3
                )

                gr.Markdown("### 🎵 参考音频（可选）")

                with gr.Row():
                    ref_input_type = gr.Radio(
                        choices=["上传文件", "路径方式", "预编码特征"],
                        value="上传文件",
                        label="参考音频输入方式"
                    )

                # 查看所有特征按钮
                with gr.Row():
                    list_features_btn = gr.Button("📋 查看所有特征 ID", variant="secondary", size="sm")

                # 上传文件选项
                with gr.Column(visible=True) as upload_col:
                    prompt_wav_upload = gr.Audio(
                        sources=["upload", "microphone"],
                        type="filepath",
                        label="参考音频 - 上传或录制一段音频作为声音参考"
                    )
                    save_ref_btn = gr.Button("💾 保存为预编码特征", variant="secondary", size="sm")
                    feat_id_input = gr.Textbox(
                        label="特征 ID",
                        placeholder="输入特征 ID 以保存或使用预编码特征"
                    )

                # 路径方式选项
                with gr.Column(visible=False) as path_col:
                    prompt_wav_path = gr.Textbox(
                        label="参考音频路径",
                        placeholder="请输入音频文件路径或URL"
                    )

                # 预编码特征选项
                with gr.Column(visible=False) as feat_col:
                    feat_id_select = gr.Textbox(
                        label="特征 ID",
                        placeholder="输入已保存的特征 ID"
                    )

                with gr.Row():
                    prompt_text = gr.Textbox(
                        value="",
                        label="参考文本 - 可选：参考音频对应的文本内容",
                        placeholder="如果上传了参考音频，可以输入对应的文本..."
                    )

                generate_btn = gr.Button("🎬 生成语音", variant="primary")

            with gr.Column():
                # 参数配置区域
                gr.Markdown("### ⚙️ 参数配置")

                cfg_value = gr.Slider(
                    minimum=1.0,
                    maximum=3.0,
                    value=2.0,
                    step=0.1,
                    label="CFG值（引导强度）- 控制生成语音与目标文本的匹配程度"
                )

                inference_timesteps = gr.Slider(
                    minimum=4,
                    maximum=30,
                    value=5,
                    step=1,
                    label="推理步数 - 影响生成质量和速度的平衡（默认 5）"
                )

                max_len = gr.Slider(
                    minimum=100,
                    maximum=5000,
                    value=2000,
                    step=100,
                    label="最大生成长度 - 控制生成音频的最大长度"
                )

        # 输出区域
        gr.Markdown("### 📤 输出结果")
        with gr.Row():
            audio_output = gr.Audio(label="生成的语音")
            status_output = gr.Textbox(label="状态", interactive=False)

        # 特征列表显示区域
        gr.Markdown("### 📋 已保存的特征")
        features_output = gr.Textbox(
            label="特征列表",
            placeholder='点击"查看所有特征 ID"按钮查看已保存的特征...',
            lines=10,
            interactive=False
        )

        # 绑定事件
        ref_input_type.change(
            fn=lambda x: {
                upload_col: gr.Column(visible=x == "上传文件"),
                path_col: gr.Column(visible=x == "路径方式"),
                feat_col: gr.Column(visible=x == "预编码特征")
            },
            inputs=[ref_input_type],
            outputs=[upload_col, path_col, feat_col]
        )

        # 查看所有特征
        list_features_btn.click(
            fn=list_ref_features,
            outputs=[features_output]
        )

        # 保存参考音频特征
        save_ref_btn.click(
            fn=save_ref_audio,
            inputs=[
                prompt_wav_upload,
                feat_id_input,
                prompt_text
            ],
            outputs=[status_output]
        )

        # 生成语音
        generate_btn.click(
            fn=synthesize_tts,
            inputs=[
                text_input,
                prompt_wav_upload,
                prompt_wav_path,
                feat_id_select,
                prompt_text,
                ref_input_type,
                cfg_value,
                inference_timesteps,
                max_len
            ],
            outputs=[audio_output, status_output]
        )

    return tts_interface


async def synthesize_tts(
    text: str,
    prompt_wav_upload: Optional[str],
    prompt_wav_path: Optional[str],
    feat_id: Optional[str],
    prompt_text: Optional[str],
    ref_input_type: str,
    cfg_value: float,
    inference_timesteps: int,
    max_len: int
) -> Tuple[Optional[str], str]:
    """
    执行语音合成

    Args:
        text: 要合成的文本
        prompt_wav_upload: 上传的参考音频
        prompt_wav_path: 参考音频路径
        feat_id: 预编码特征 ID
        prompt_text: 参考文本
        ref_input_type: 输入方式
        cfg_value: CFG值
        inference_timesteps: 推理步数
        max_len: 最大生成长度

    Returns:
        Tuple[Optional[str], str]: (音频路径, 状态消息)
    """
    if not text:
        return None, "请输入要合成的文本"

    try:
        # 确定参考音频路径
        prompt_audio = None
        if ref_input_type == "上传文件" and prompt_wav_upload:
            prompt_audio = prompt_wav_upload
        elif ref_input_type == "路径方式" and prompt_wav_path:
            prompt_audio = prompt_wav_path

        # 使用 ONNX TTS
        result = await tts_onnx_module.synthesize(
            text=text,
            prompt_wav=prompt_audio,
            prompt_text=prompt_text,
            feat_id=feat_id if ref_input_type == "预编码特征" else None,
            cfg_value=cfg_value,
            min_len=2,
            max_len=max_len,
            timesteps=inference_timesteps
        )

        if result["success"]:
            duration = result.get("duration", 0)
            sample_rate = result.get("sample_rate", 0)
            return result["output_path"], f"语音合成成功！时长: {duration:.2f}s, 采样率: {sample_rate}Hz"
        else:
            return None, f"合成失败: {result.get('error', '未知错误')}"

    except Exception as e:
        Logger.error(f"TTS synthesis error: {e}")
        import traceback
        Logger.error(traceback.format_exc())
        return None, f"合成失败: {str(e)}"


async def save_ref_audio(
    prompt_wav_upload: Optional[str],
    feat_id: str,
    prompt_text: Optional[str]
) -> str:
    """
    保存参考音频特征

    Args:
        prompt_wav_upload: 上传的参考音频
        feat_id: 特征 ID
        prompt_text: 参考文本

    Returns:
        str: 状态消息
    """
    if not prompt_wav_upload:
        return "请先上传参考音频"

    if not feat_id:
        return "请输入特征 ID"

    try:
        result = await tts_onnx_module.save_ref_audio(
            feat_id=feat_id,
            prompt_audio_path=prompt_wav_upload,
            prompt_text=prompt_text
        )

        if result["success"]:
            return f"参考音频特征保存成功！特征 ID: {feat_id}, Patches 形状: {result['patches_shape']}"
        else:
            return f"保存失败: {result.get('error', '未知错误')}"

    except Exception as e:
        Logger.error(f"Save ref audio error: {e}")
        return f"保存失败: {str(e)}"


def list_ref_features() -> str:
    """
    查看所有已保存的特征

    Returns:
        str: 特征列表文本
    """
    try:
        result = tts_onnx_module.list_ref_features()

        if result["success"]:
            if result["count"] == 0:
                return "暂无已保存的特征"
            
            features = result["features"]
            lines = [f"已保存特征数量: {result['count']}\n"]
            lines.append("=" * 80)
            
            for feat in features:
                lines.append(f"\n特征 ID: {feat['feat_id']}")
                lines.append(f"参考文本: {feat['prompt_text']}")
                lines.append(f"Patch Size: {feat['patch_size']}")
                lines.append(f"数据类型: {feat['dtype']}")
                lines.append(f"创建时间: {feat['created_at']}")
                lines.append("-" * 80)
            
            return "\n".join(lines)
        else:
            return f"获取特征列表失败: {result.get('error', '未知错误')}"

    except Exception as e:
        Logger.error(f"List ref features error: {e}")
        return f"获取特征列表失败: {str(e)}"