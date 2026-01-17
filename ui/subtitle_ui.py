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
                    subtitle_file = gr.File(
                        label="上传字幕文件（可选）",
                        file_types=[".srt", ".vtt", ".ass", ".ssa"]
                    )
                    gr.Markdown("*提示：可以同时上传视频、音频和字幕文件，或只上传其中部分文件。优先级：字幕文件 > 音频文件 > 视频文件*")

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
                    gr.Markdown("#### 📄 字幕文件")
                    subtitle_path_input = gr.Textbox(
                        label="字幕文件路径",
                        placeholder="输入字幕文件的URL或本地路径",
                        info="支持http/https URL或本地文件路径，支持 .srt, .vtt, .ass, .ssa 格式"
                    )
                    gr.Markdown("*提示：可以同时提供视频、音频和字幕文件，或只提供其中部分文件。优先级：字幕文件 > 音频文件 > 视频文件*")

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
                    bilingual = gr.Checkbox(label="双语字幕", value=False)
                    word_timestamps = gr.Checkbox(label="词级时间戳", value=False)

                # Whisper 时间戳分段优化参数
                gr.Markdown("### 🎯 Whisper 参数")
                with gr.Row():
                    vad_filter = gr.Checkbox(
                        label="启用 VAD 语音活动检测",
                        value=True,
                        info="启用后能更准确地检测语音边界"
                    )
                    condition_on_previous_text = gr.Checkbox(
                        label="不依赖前文分段",
                        value=True,
                        info="启用后不依赖前文内容，产生更自然的分段"
                    )
                    temperature = gr.Slider(
                        minimum=0.0,
                        maximum=1.0,
                        value=0.0,
                        step=0.1,
                        label="温度参数",
                        info="控制预测的随机性，0 表示更保守（推荐），1 表示更随机"
                    )

                # 字幕显示参数（后处理）
                gr.Markdown("### 📝 字幕显示参数（后处理）")
                with gr.Row():
                    max_chars_per_line = gr.Slider(
                        minimum=10,
                        maximum=30,
                        value=20,
                        step=2,
                        label="每行最大字符数",
                        info="字幕每行显示的最大字符数，超过会自动换行（推荐 20）"
                    )
                    max_lines_per_segment = gr.Slider(
                        minimum=1,
                        maximum=4,
                        value=2,
                        step=1,
                        label="每段最大行数",
                        info="每个字幕段的最大行数，超过会自动分割（推荐 2）"
                    )

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
                    subtitle_bottom_margin = gr.Number(
                        label="字幕下沿距离（像素）",
                        value=50,
                        minimum=0,
                        maximum=500,
                        step=1,
                        info="控制字幕距离视频底边的距离，默认50像素"
                    )
                
                # 时长基准选择
                with gr.Row():
                    duration_reference = gr.Radio(
                        choices=["video", "audio"],
                        value="video",
                        label="时长基准",
                        info="当视频和音频同时存在时，决定以哪个时长为准"
                    )
                
                # 音频语速调整选项
                with gr.Row():
                    adjust_audio_speed = gr.Checkbox(
                        label="自动调整音频语速",
                        value=False,
                        info="当以视频时长为基准时，自动调整音频语速以匹配视频时长"
                    )
                    audio_speed_factor = gr.Slider(
                        minimum=0.5,
                        maximum=2.0,
                        value=1.0,
                        step=0.1,
                        label="语速调整倍数",
                        visible=False,
                        info="手动指定音频语速调整倍数（0.5=慢一倍，2.0=快一倍）"
                    )
                
                # 音频音量控制选项
                with gr.Row():
                    audio_volume = gr.Slider(
                        minimum=0.0,
                        maximum=3.0,
                        value=1.0,
                        step=0.1,
                        label="音频音量",
                        info="控制合并时音频的音量大小（1.0=原音量，0.5=降低一半，2.0=提高一倍）"
                    )
                
                # 原音频保留选项
                with gr.Row():
                    keep_original_audio = gr.Checkbox(
                        label="保留原视频音频",
                        value=True,
                        info="当同时提供视频和音频时，是否保留原视频的音频（勾选则混合，不勾选则替换）"
                    )
                
                # LLM 字幕纠错选项
                with gr.Group():
                    llm_correction_group = gr.Group()
                    with llm_correction_group:
                        enable_llm_correction = gr.Checkbox(
                            label="启用 LLM 字幕纠错",
                            value=False,
                            info="使用智谱 AI 模型对生成的字幕进行智能纠错（需要配置 API Key）"
                        )
                        reference_text = gr.Textbox(
                            label="参考文本",
                            lines=5,
                            placeholder="输入正确的文本内容，用于纠正字幕中的错字、漏字、多字等错误...",
                            visible=False,
                            info="提供正确的文本内容，系统将根据此文本纠正字幕错误"
                        )
                    
                    # 显示/隐藏参考文本输入框
                    def update_reference_text_visibility(enable_correction):
                        return gr.update(visible=enable_correction)
                    
                    enable_llm_correction.change(
                        update_reference_text_visibility,
                        inputs=[enable_llm_correction],
                        outputs=[reference_text]
                    )
                
                gr.Markdown("*注：选择'audio'时，如果视频时长不足，将自动以最后一帧画面补充*")
                
                # 显示/隐藏手动语速调整滑块
                def update_audio_speed_visibility(adjust_speed):
                    return gr.update(visible=adjust_speed)
                
                adjust_audio_speed.change(
                    update_audio_speed_visibility,
                    inputs=[adjust_audio_speed],
                    outputs=[audio_speed_factor]
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

                gr.Markdown("#### 🎬 视频预览")
                video_preview = gr.Video(label="视频预览", visible=False)

                gr.Markdown("#### 📥 视频文件")
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
                subtitle_file,
                video_path_input,
                audio_path_input,
                subtitle_path_input,
                model_choice_adv,
                device_choice,
                generate_subtitle,
                bilingual,
                word_timestamps,
                burn_type,
                beam_size_adv,
                subtitle_bottom_margin,
                duration_reference,
                adjust_audio_speed,
                audio_speed_factor,
                audio_volume,
                keep_original_audio,
                enable_llm_correction,
                reference_text,
                # Whisper 基础参数
                vad_filter,
                condition_on_previous_text,
                temperature,
                # 字幕显示参数（后处理）
                max_chars_per_line,
                max_lines_per_segment
            ],
            outputs=[
                job_id_display,
                status_info,
                result_status,
                srt_download,
                bilingual_srt_download,
                video_preview,
                video_download,
                transcript_output
            ]
        )

    return subtitle_interface


async def process_subtitle(
    input_type: str,
    video_file: Optional[str],
    audio_file: Optional[str],
    subtitle_file: Optional[str],
    video_path: Optional[str],
    audio_path: Optional[str],
    subtitle_path: Optional[str],
    model_name: str,
    device: str,
    generate_subtitle: bool,
    bilingual: bool,
    word_timestamps: bool,
    burn_type: str,
    beam_size: int,
    subtitle_bottom_margin: int,
    duration_reference: str,
    adjust_audio_speed: bool,
    audio_speed_factor: float,
    audio_volume: float,
    keep_original_audio: bool,
    enable_llm_correction: bool,
    reference_text: Optional[str],
    # Whisper 基础参数
    vad_filter: bool,
    condition_on_previous_text: bool,
    temperature: float,
    # 字幕显示参数（后处理）
    max_chars_per_line: int,
    max_lines_per_segment: int
) -> Tuple[str, str, dict, Optional[str], Optional[str], Optional[str], str]:
    """
    处理字幕生成（纯字幕功能）

    Args:
        input_type: 输入类型
        video_file: 上传的视频文件
        audio_file: 上传的音频文件
        subtitle_file: 上传的字幕文件
        video_path: 视频文件路径
        audio_path: 音频文件路径
        subtitle_path: 字幕文件路径
        model_name: 模型名称
        device: 设备类型
        generate_subtitle: 是否生成字幕
        bilingual: 是否生成双语字幕
        word_timestamps: 是否包含词级时间戳
        burn_type: 字幕烧录类型
        beam_size: beam search 大小
        subtitle_bottom_margin: 字幕下沿距离（像素）
        duration_reference: 时长基准
        adjust_audio_speed: 是否自动调整音频语速
        audio_speed_factor: 语速调整倍数
        audio_volume: 音频音量
        keep_original_audio: 是否保留原视频音频
        enable_llm_correction: 是否启用LLM字幕纠错
        reference_text: 参考文本

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
                gr.update(value=None, visible=False),
                gr.update(value=None, visible=False),
                gr.update(value=None, visible=False),
                gr.update(value=None, visible=False),
                gr.update(value="", visible=False)
            )

        Logger.info(f"开始处理字幕生成 - input_type: {input_type}, video_file: {video_file}, audio_file: {audio_file}")

        # 执行字幕生成（不包含视频效果）
        result = await subtitle_module.generate_subtitles_advanced(
            input_type=input_type,
            video_file=video_file,
            audio_file=audio_file,
            subtitle_file=subtitle_file,
            video_path=video_path,
            audio_path=audio_path,
            subtitle_path=subtitle_path,
            model_name=model_name,
            device=device,
            generate_subtitle=generate_subtitle,
            bilingual=bilingual,
            word_timestamps=word_timestamps,
            burn_subtitles=burn_type,
            beam_size=beam_size,
            subtitle_bottom_margin=subtitle_bottom_margin,
            out_basename=None,
            flower_config=None,  # 不包含花字
            image_config=None,   # 不包含插图
            watermark_config=None,  # 不包含水印
            duration_reference=duration_reference,  # 时长基准
            adjust_audio_speed=adjust_audio_speed,  # 音频语速调整
            audio_speed_factor=audio_speed_factor,  # 语速调整倍数
            audio_volume=audio_volume,  # 音频音量控制
            keep_original_audio=keep_original_audio,  # 保留原音频
            enable_llm_correction=enable_llm_correction,  # LLM 字幕纠错
            reference_text=reference_text,  # 参考文本
            # Whisper 基础参数
            vad_filter=vad_filter,
            condition_on_previous_text=condition_on_previous_text,
            temperature=temperature,
            # 字幕显示参数（后处理）
            max_chars_per_line=max_chars_per_line,
            max_lines_per_segment=max_lines_per_segment
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
            gr.update(value=subtitle_path, visible=bool(subtitle_path)),
            gr.update(value=bilingual_subtitle_path, visible=bool(bilingual_subtitle_path)),
            gr.update(value=video_with_subtitle_path, visible=bool(video_with_subtitle_path)),
            gr.update(value=video_with_subtitle_path, visible=bool(video_with_subtitle_path)),
            gr.update(value=result.get("transcript_text", ""), visible=bool(result.get("transcript_text")))
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
            gr.update(value=None, visible=False),
            gr.update(value=None, visible=False),
            gr.update(value=None, visible=False),
            gr.update(value=None, visible=False),
            gr.update(value="", visible=False)
        )