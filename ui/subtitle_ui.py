"""
高级字幕生成 UI 组件

提供纯粹的字幕生成功能，包括语音识别、字幕生成、字幕烧录等。
"""

import gradio as gr
from typing import Tuple, Optional
from pathlib import Path

from modules.subtitle_module import subtitle_module
from utils.logger import Logger


def create_subtitle_interface() -> gr.Blocks:
    """
    创建高级字幕生成界面

    Returns:
        gr.Blocks: Gradio 界面块
    """
    with gr.Blocks() as subtitle_interface:
        gr.Markdown("## 高级字幕生成")
        gr.Markdown("为视频生成字幕，支持翻译和烧录功能")

        with gr.Row():
            with gr.Column():
                # 输入文件区域
                gr.Markdown("### 📤 上传文件")
                input_type = gr.Radio(
                    choices=["upload", "path"],
                    value="upload",
                    label="输入类型"
                )

                with gr.Group(visible=True) as upload_group:
                    video_input = gr.Video(label="上传视频文件")
                    audio_input_adv = gr.Audio(label="上传音频文件")
                    gr.Markdown("*提示：可以同时上传视频和音频文件，或只上传其中一个*")

                with gr.Group(visible=False) as path_group:
                    gr.Markdown("#### 📹 视频文件")
                    video_path_input = gr.Textbox(
                        label="视频文件路径",
                        placeholder="输入视频文件的URL或本地路径",
                        info="支持http/https URL或本地文件路径"
                    )
                    gr.Markdown("#### 🎵 音频文件")
                    audio_path_input = gr.Textbox(
                        label="音频文件路径",
                        placeholder="输入音频文件的URL或本地路径",
                        info="支持http/https URL或本地文件路径"
                    )
                    gr.Markdown("*提示：可以同时提供视频和音频文件，或只提供其中一个*")

                # 基础参数配置
                gr.Markdown("### ⚙️ 字幕参数")

                with gr.Row():
                    model_choice_adv = gr.Dropdown(
                        choices=["tiny", "base", "small", "medium", "large"],
                        value="small",
                        label="Whisper 模型"
                    )
                    device_choice = gr.Dropdown(
                        choices=["cpu", "cuda"],
                        value="cpu",
                        label="设备选择"
                    )

                with gr.Row():
                    generate_subtitle = gr.Checkbox(
                        label="生成字幕",
                        value=True,
                        info="取消勾选则仅进行音频处理"
                    )
                    bilingual = gr.Checkbox(label="双语字幕", value=True)
                    word_timestamps = gr.Checkbox(label="词级时间戳", value=False)

                with gr.Row():
                    burn_type = gr.Radio(
                        choices=["none", "hard"],
                        value="none",
                        label="字幕烧录类型"
                    )
                    beam_size_adv = gr.Slider(
                        minimum=1,
                        maximum=10,
                        value=5,
                        step=1,
                        label="Beam Size"
                    )

                transcribe_adv_btn = gr.Button("🎬 生成字幕", variant="primary")

                # 事件处理
                def update_input_visibility(input_type):
                    return (
                        gr.update(visible=(input_type == "upload")),
                        gr.update(visible=(input_type == "path"))
                    )

                input_type.change(
                    update_input_visibility,
                    inputs=[input_type],
                    outputs=[upload_group, path_group]
                )

            with gr.Column():
                # 输出结果区域
                gr.Markdown("### 📝 转录结果")

                job_id_display = gr.Textbox(label="任务ID", interactive=False)
                status_info = gr.HTML("<div>等待提交任务...</div>")
                result_status = gr.JSON(label="详细状态", visible=False)

                gr.Markdown("#### 📄 字幕文件")
                srt_download = gr.File(label="下载SRT字幕文件", visible=False)
                bilingual_srt_download = gr.File(label="下载双语SRT字幕文件", visible=False)

                gr.Markdown("#### 🎬 视频文件")
                video_download = gr.File(label="下载处理后的视频文件", visible=False)

                gr.Markdown("#### 📝 转录文本")
                transcript_output = gr.Textbox(
                    label="转录文本",
                    lines=10,
                    interactive=False,
                    visible=False
                )

        # 绑定事件
        transcribe_adv_btn.click(
            fn=process_subtitle,
            inputs=[
                input_type,
                video_input,
                audio_input_adv,
                video_path_input,
                audio_path_input,
                model_choice_adv,
                device_choice,
                generate_subtitle,
                bilingual,
                word_timestamps,
                burn_type,
                beam_size_adv
            ],
            outputs=[
                job_id_display,
                status_info,
                result_status,
                srt_download,
                bilingual_srt_download,
                video_download,
                transcript_output
            ]
        )

    return subtitle_interface


async def process_subtitle(
    input_type: str,
    video_file: Optional[str],
    audio_file: Optional[str],
    video_path: Optional[str],
    audio_path: Optional[str],
    model_name: str,
    device: str,
    generate_subtitle: bool,
    bilingual: bool,
    word_timestamps: bool,
    burn_type: str,
    beam_size: int
) -> Tuple[str, str, dict, Optional[str], Optional[str], Optional[str], str]:
    """
    处理字幕生成（纯字幕功能）

    Args:
        input_type: 输入类型
        video_file: 上传的视频文件
        audio_file: 上传的音频文件
        video_path: 视频文件路径
        audio_path: 音频文件路径
        model_name: 模型名称
        device: 设备类型
        generate_subtitle: 是否生成字幕
        bilingual: 是否生成双语字幕
        word_timestamps: 是否包含词级时间戳
        burn_type: 字幕烧录类型
        beam_size: beam search 大小

    Returns:
        Tuple: (任务ID, 状态信息, 详细状态, SRT文件, 双语SRT文件, 视频文件, 转录文本)
    """
    try:
        # 参数验证：检查是否有输入文件
        has_input = False

        if input_type == "upload":
            # Upload模式：检查视频或音频文件
            if video_file or audio_file:
                has_input = True
        elif input_type == "path":
            # Path模式：检查视频或音频路径
            if video_path or audio_path:
                has_input = True

        if not has_input:
            status_html = """
            <div style="color: red;">
                <h3>❌ 处理失败</h3>
                <p>错误: 请上传或提供有效的视频/音频文件</p>
            </div>
            """
            return (
                "error",
                status_html,
                {"success": False, "error": "请上传或提供有效的视频/音频文件"},
                None,
                None,
                None,
                ""
            )

        Logger.info(f"开始处理字幕生成 - input_type: {input_type}, video_file: {video_file}, audio_file: {audio_file}")

        # 执行字幕生成（不包含视频效果）
        result = await subtitle_module.generate_subtitles_advanced(
            input_type=input_type,
            video_file=video_file,
            audio_file=audio_file,
            video_path=video_path,
            audio_path=audio_path,
            model_name=model_name,
            device=device,
            generate_subtitle=generate_subtitle,
            bilingual=bilingual,
            word_timestamps=word_timestamps,
            burn_subtitles=burn_type,
            beam_size=beam_size,
            out_basename=None,
            flower_config=None,  # 不包含花字
            image_config=None,   # 不包含插图
            watermark_config=None  # 不包含水印
        )

        # 生成任务ID
        job_id = result.get("out_basename", "unknown")

        # 构建状态信息
        if result["success"]:
            status_html = f"""
            <div style="color: green;">
                <h3>✅ 处理完成</h3>
                <p>任务ID: {job_id}</p>
                <p>生成字幕片段数: {result.get('segments_count', 0)}</p>
            </div>
            """
        else:
            status_html = f"""
            <div style="color: red;">
                <h3>❌ 处理失败</h3>
                <p>错误: {result.get('error', '未知错误')}</p>
            </div>
            """

        # 确保文件路径是绝对路径
        subtitle_path = result.get("subtitle_path")
        if subtitle_path:
            subtitle_path = str(Path(subtitle_path).absolute())

        bilingual_subtitle_path = result.get("bilingual_subtitle_path")
        if bilingual_subtitle_path:
            bilingual_subtitle_path = str(Path(bilingual_subtitle_path).absolute())

        video_with_subtitle_path = result.get("video_with_subtitle_path")
        if video_with_subtitle_path:
            video_with_subtitle_path = str(Path(video_with_subtitle_path).absolute())

        return (
            job_id,
            status_html,
            result,
            subtitle_path,
            bilingual_subtitle_path,
            video_with_subtitle_path,
            result.get("transcript_text", "")
        )

    except Exception as e:
        Logger.error(f"Subtitle processing error: {e}")
        import traceback
        Logger.error(traceback.format_exc())

        status_html = f"""
        <div style="color: red;">
            <h3>❌ 处理失败</h3>
            <p>错误: {str(e)}</p>
        </div>
        """

        return (
            "error",
            status_html,
            {"success": False, "error": str(e)},
            None,
            None,
            None,
            ""
        )