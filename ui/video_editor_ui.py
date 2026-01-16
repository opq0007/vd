"""
自动剪辑 UI 组件

提供花字、插图、水印等高级视频效果功能。
"""

import gradio as gr
from typing import Tuple, Optional
from pathlib import Path

from modules.video_editor_module import video_editor_module
from utils.logger import Logger
from utils.font_manager import font_manager


def create_video_editor_interface() -> gr.Blocks:
    """
    创建自动剪辑界面

    Returns:
        gr.Blocks: Gradio 界面块
    """
    # 获取可用字体列表
    available_fonts = font_manager.get_available_fonts()
    if not available_fonts:
        available_fonts = ["请将字体文件放入fonts目录"]
        default_font = ""
    else:
        default_font = available_fonts[0]

    with gr.Blocks() as video_editor_interface:
        gr.Markdown("## 自动剪辑")
        gr.Markdown("为视频添加花字、插图、水印等高级效果")

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

                with gr.Group(visible=False) as path_group:
                    video_path_input = gr.Textbox(
                        label="视频文件路径",
                        placeholder="输入视频文件的URL或本地路径",
                        info="支持http/https URL或本地文件路径"
                    )

                # 花字配置
                with gr.Accordion("🌟 花字配置", open=False):
                    gr.Markdown("#### 🌟 花字配置")
                    with gr.Row():
                        flower_text = gr.Textbox(
                            label="花字内容",
                            placeholder="输入要显示的花字文字"
                        )
                        flower_font = gr.Dropdown(
                            choices=available_fonts,
                            value=default_font,
                            label="字体"
                        )
                        flower_size = gr.Slider(
                            minimum=20, maximum=100, value=40, step=5,
                            label="字体大小"
                        )
                    with gr.Row():
                        flower_color = gr.ColorPicker(
                            label="文字颜色",
                            value="#FFFFFF",
                            info="选择花字的文字颜色",
                            show_label=True
                        )
                    with gr.Row():
                        flower_x = gr.Slider(
                            minimum=0, maximum=1920, value=100, step=10,
                            label="X坐标"
                        )
                        flower_y = gr.Slider(
                            minimum=0, maximum=1080, value=100, step=10,
                            label="Y坐标"
                        )
                    with gr.Accordion("🖌️ 描边设置", open=False):
                        with gr.Row():
                            flower_stroke_enabled = gr.Checkbox(
                                label="启用描边",
                                value=False,
                                info="为文字添加描边效果"
                            )
                        with gr.Row():
                            flower_stroke_color = gr.ColorPicker(
                                label="描边颜色",
                                value="#000000",
                                info="选择描边的颜色"
                            )
                            flower_stroke_width = gr.Slider(
                                minimum=1, maximum=10, value=2, step=1,
                                label="描边宽度",
                                info="描边的粗细程度"
                            )
                    with gr.Row():
                        flower_timing_type = gr.Radio(
                            choices=["帧数范围", "时间戳范围"],
                            value="时间戳范围",
                            label="插入时机类型"
                        )
                    with gr.Group():
                        with gr.Row(visible=True) as flower_frame_group:
                            flower_start_frame = gr.Number(
                                label="起始帧", value=0, minimum=0, precision=0
                            )
                            flower_end_frame = gr.Number(
                                label="结束帧", value=100, minimum=0, precision=0
                            )
                        with gr.Row(visible=False) as flower_time_group:
                            flower_start_time = gr.Textbox(
                                label="起始时间", value="00:00:00", placeholder="格式: HH:MM:SS"
                            )
                            flower_end_time = gr.Textbox(
                                label="结束时间", value="00:00:05", placeholder="格式: HH:MM:SS"
                            )

                # 插视频配置
                with gr.Accordion("🎬 插视频配置", open=False):
                    gr.Markdown("#### 🎬 插视频配置")
                    gr.Markdown("将另一个视频的每一帧依次插入到原视频的指定位置")
                    with gr.Row():
                        video_insert_path = gr.Textbox(
                            label="视频路径",
                            placeholder="输入视频文件路径",
                            info="支持本地路径"
                        )
                    with gr.Row():
                        video_insert_x = gr.Slider(
                            minimum=0, maximum=1920, value=200, step=10,
                            label="X坐标"
                        )
                        video_insert_y = gr.Slider(
                            minimum=0, maximum=1080, value=200, step=10,
                            label="Y坐标"
                        )
                    with gr.Row():
                        video_insert_width = gr.Slider(
                            minimum=50, maximum=800, value=200, step=10,
                            label="宽度"
                        )
                        video_insert_height = gr.Slider(
                            minimum=50, maximum=600, value=150, step=10,
                            label="高度"
                        )
                    with gr.Row():
                        video_insert_timing_type = gr.Radio(
                            choices=["起始帧", "起始时间"],
                            value="起始时间",
                            label="插入起始时机"
                        )
                    with gr.Group():
                        with gr.Row(visible=True) as video_insert_time_group:
                            video_insert_start_time = gr.Textbox(
                                label="起始时间", value="00:00:00", placeholder="格式: HH:MM:SS"
                            )
                        with gr.Row(visible=False) as video_insert_frame_group:
                            video_insert_start_frame = gr.Number(
                                label="起始帧", value=0, minimum=0, precision=0
                            )

                # 插图配置
                with gr.Accordion("🖼️ 插图配置", open=False):
                    gr.Markdown("#### 🖼️ 插图配置")
                    with gr.Row():
                        image_path = gr.Textbox(
                            label="图片路径",
                            placeholder="输入图片文件路径或URL",
                            info="支持本地路径或URL"
                        )
                        image_remove_bg = gr.Checkbox(
                            label="移除背景",
                            value=True,
                            info="自动移除图片背景，只保留主体内容"
                        )
                    with gr.Row():
                        image_x = gr.Slider(
                            minimum=0, maximum=1920, value=200, step=10,
                            label="X坐标"
                        )
                        image_y = gr.Slider(
                            minimum=0, maximum=1080, value=200, step=10,
                            label="Y坐标"
                        )
                    with gr.Row():
                        image_width = gr.Slider(
                            minimum=50, maximum=800, value=200, step=10,
                            label="宽度"
                        )
                        image_height = gr.Slider(
                            minimum=50, maximum=600, value=150, step=10,
                            label="高度"
                        )
                    with gr.Row():
                        image_timing_type = gr.Radio(
                            choices=["帧数范围", "时间戳范围"],
                            value="时间戳范围",
                            label="插入时机类型"
                        )
                    with gr.Group():
                        with gr.Row(visible=True) as image_frame_group:
                            image_start_frame = gr.Number(
                                label="起始帧", value=0, minimum=0, precision=0
                            )
                            image_end_frame = gr.Number(
                                label="结束帧", value=100, minimum=0, precision=0
                            )
                        with gr.Row(visible=False) as image_time_group:
                            image_start_time = gr.Textbox(
                                label="起始时间", value="00:00:00", placeholder="格式: HH:MM:SS"
                            )
                            image_end_time = gr.Textbox(
                                label="结束时间", value="00:00:05", placeholder="格式: HH:MM:SS"
                            )

                # 水印配置
                with gr.Accordion("🔒 水印配置", open=False):
                    gr.Markdown("#### 🔒 水印配置")
                    with gr.Row():
                        watermark_text = gr.Textbox(
                            label="水印文字",
                            placeholder="输入水印文字内容"
                        )
                        watermark_font = gr.Dropdown(
                            choices=available_fonts,
                            value=default_font,
                            label="字体"
                        )
                        watermark_size = gr.Slider(
                            minimum=12, maximum=60, value=20, step=2,
                            label="字体大小"
                        )
                    with gr.Row():
                        watermark_color = gr.ColorPicker(
                            label="文字颜色",
                            value="#FFFFFF",
                            info="选择水印文字的颜色",
                            show_label=True
                        )
                    with gr.Row():
                        watermark_timing_type = gr.Radio(
                            choices=["帧数范围", "时间戳范围"],
                            value="时间戳范围",
                            label="插入时机类型"
                        )
                        watermark_style = gr.Radio(
                            choices=["半透明浮动", "斜向移动"],
                            value="半透明浮动",
                            label="水印效果"
                        )
                    with gr.Group():
                        with gr.Row(visible=True) as watermark_frame_group:
                            watermark_start_frame = gr.Number(
                                label="起始帧", value=0, minimum=0, precision=0
                            )
                            watermark_end_frame = gr.Number(
                                label="结束帧", value=999999, minimum=0, precision=0
                            )
                        with gr.Row(visible=False) as watermark_time_group:
                            watermark_start_time = gr.Textbox(
                                label="起始时间", value="00:00:00", placeholder="格式: HH:MM:SS"
                            )
                            watermark_end_time = gr.Textbox(
                                label="结束时间", value="99:59:59", placeholder="格式: HH:MM:SS"
                            )

                process_btn = gr.Button("🎬 应用效果", variant="primary")

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

                def update_flower_timing_visibility(timing_type):
                    frame_visible = timing_type == "帧数范围"
                    time_visible = timing_type == "时间戳范围"
                    return (
                        gr.Row(visible=frame_visible),
                        gr.Row(visible=time_visible)
                    )

                flower_timing_type.change(
                    update_flower_timing_visibility,
                    inputs=[flower_timing_type],
                    outputs=[flower_frame_group, flower_time_group]
                )

                def update_image_timing_visibility(timing_type):
                    frame_visible = timing_type == "帧数范围"
                    time_visible = timing_type == "时间戳范围"
                    return (
                        gr.Row(visible=frame_visible),
                        gr.Row(visible=time_visible)
                    )

                image_timing_type.change(
                    update_image_timing_visibility,
                    inputs=[image_timing_type],
                    outputs=[image_frame_group, image_time_group]
                )

                def update_watermark_timing_visibility(timing_type):
                    frame_visible = timing_type == "帧数范围"
                    time_visible = timing_type == "时间戳范围"
                    return (
                        gr.Row(visible=frame_visible),
                        gr.Row(visible=time_visible)
                    )

                watermark_timing_type.change(
                    update_watermark_timing_visibility,
                    inputs=[watermark_timing_type],
                    outputs=[watermark_frame_group, watermark_time_group]
                )

                def update_video_insert_timing_visibility(timing_type):
                    frame_visible = timing_type == "起始帧"
                    time_visible = timing_type == "起始时间"
                    return (
                        gr.Row(visible=time_visible),
                        gr.Row(visible=frame_visible)
                    )

                video_insert_timing_type.change(
                    update_video_insert_timing_visibility,
                    inputs=[video_insert_timing_type],
                    outputs=[video_insert_time_group, video_insert_frame_group]
                )

            with gr.Column():
                # 输出结果区域
                gr.Markdown("### 📝 处理结果")

                job_id_display = gr.Textbox(label="任务ID", interactive=False)
                status_info = gr.HTML("<div>等待提交任务...</div>")
                result_status = gr.JSON(label="详细状态", visible=False)

                gr.Markdown("#### 🎬 视频文件")
                video_download = gr.File(label="下载处理后的视频文件", visible=False)

        # 绑定事件
        process_btn.click(
            fn=process_video_effects,
            inputs=[
                input_type,
                video_input,
                video_path_input,
                # 花字配置
                flower_text,
                flower_font,
                flower_size,
                flower_color,
                flower_x,
                flower_y,
                flower_timing_type,
                flower_start_frame,
                flower_end_frame,
                flower_start_time,
                flower_end_time,
                flower_stroke_enabled,
                flower_stroke_color,
                flower_stroke_width,
                # 插视频配置
                video_insert_path,
                video_insert_x,
                video_insert_y,
                video_insert_width,
                video_insert_height,
                video_insert_timing_type,
                video_insert_start_frame,
                video_insert_start_time,
                # 插图配置
                image_path,
                image_x,
                image_y,
                image_width,
                image_height,
                image_timing_type,
                image_start_frame,
                image_end_frame,
                image_start_time,
                image_end_time,
                image_remove_bg,
                # 水印配置
                watermark_text,
                watermark_font,
                watermark_size,
                watermark_color,
                watermark_timing_type,
                watermark_start_frame,
                watermark_end_frame,
                watermark_start_time,
                watermark_end_time,
                watermark_style
            ],
            outputs=[
                job_id_display,
                status_info,
                result_status,
                video_download
            ]
        )

    return video_editor_interface


async def process_video_effects(*args):
    """
    处理视频效果

    Args:
        *args: 所有输入参数

    Returns:
        Tuple: (任务ID, 状态信息, 详细状态, 视频文件)
    """
    try:
        # 解包参数
        (input_type, video_file, video_path,
         # 花字配置
         flower_text, flower_font, flower_size, flower_color, flower_x, flower_y,
         flower_timing_type, flower_start_frame, flower_end_frame,
         flower_start_time, flower_end_time,
         flower_stroke_enabled, flower_stroke_color, flower_stroke_width,
         # 插视频配置
         video_insert_path, video_insert_x, video_insert_y, video_insert_width, video_insert_height,
         video_insert_timing_type, video_insert_start_frame, video_insert_start_time,
         # 插图配置
         image_path, image_x, image_y, image_width, image_height,
         image_timing_type, image_start_frame, image_end_frame,
         image_start_time, image_end_time, image_remove_bg,
         # 水印配置
         watermark_text, watermark_font, watermark_size, watermark_color,
         watermark_timing_type, watermark_start_frame, watermark_end_frame,
         watermark_start_time, watermark_end_time, watermark_style) = args

        # 准备花字配置
        flower_config = None
        if flower_text and flower_text.strip():
            flower_config = {
                'text': flower_text,
                'font': flower_font,
                'size': int(flower_size),
                'color': flower_color,
                'x': int(flower_x),
                'y': int(flower_y),
                'timing_type': flower_timing_type,
                'start_frame': int(flower_start_frame),
                'end_frame': int(flower_end_frame),
                'start_time': flower_start_time,
                'end_time': flower_end_time,
                'stroke_enabled': flower_stroke_enabled,
                'stroke_color': flower_stroke_color,
                'stroke_width': int(flower_stroke_width)
            }

        # 准备插图配置
        image_config = None
        if image_path and image_path.strip():
            image_config = {
                'path': image_path,
                'x': int(image_x),
                'y': int(image_y),
                'width': int(image_width),
                'height': int(image_height),
                'remove_bg': image_remove_bg,
                'timing_type': image_timing_type,
                'start_frame': int(image_start_frame),
                'end_frame': int(image_end_frame),
                'start_time': image_start_time,
                'end_time': image_end_time
            }

        # 准备插视频配置
        video_config = None
        if video_insert_path and video_insert_path.strip():
            video_config = {
                'path': video_insert_path,
                'x': int(video_insert_x),
                'y': int(video_insert_y),
                'width': int(video_insert_width),
                'height': int(video_insert_height),
                'timing_type': video_insert_timing_type,
                'start_frame': int(video_insert_start_frame),
                'start_time': video_insert_start_time
            }

        # 准备水印配置
        watermark_config = None
        if watermark_text and watermark_text.strip():
            watermark_config = {
                'text': watermark_text,
                'font': watermark_font,
                'size': int(watermark_size),
                'color': watermark_color,
                'timing_type': watermark_timing_type,
                'start_frame': int(watermark_start_frame),
                'end_frame': int(watermark_end_frame),
                'start_time': watermark_start_time,
                'end_time': watermark_end_time,
                'style': watermark_style
            }

        # 执行视频效果处理
        result = await video_editor_module.apply_video_effects(
            input_type=input_type,
            video_file=video_file,
            video_path=video_path,
            flower_config=flower_config,
            image_config=image_config,
            video_config=video_config,
            watermark_config=watermark_config
        )

        # 生成任务ID
        job_id = result.get("out_basename", "unknown")

        # 构建状态信息
        if result["success"]:
            status_html = f"""
            <div style="color: green;">
                <h3>✅ 处理完成</h3>
                <p>任务ID: {job_id}</p>
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
        video_output_path = result.get("video_output_path")
        if video_output_path:
            video_output_path = str(Path(video_output_path).absolute())

        return (
            job_id,
            status_html,
            result,
            video_output_path
        )

    except Exception as e:
        Logger.error(f"Video processing error: {e}")
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
            None
        )