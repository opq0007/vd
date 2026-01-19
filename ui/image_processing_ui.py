"""
图像处理 UI 组件

提供图片去背景、图片混合等图像处理功能。
"""

import gradio as gr
from typing import Tuple, Optional
from pathlib import Path

from modules.image_processing_module import image_processing_module
from utils.logger import Logger


def create_image_processing_interface() -> gr.Blocks:
    """
    创建图像处理界面

    Returns:
        gr.Blocks: Gradio 界面块
    """
    with gr.Blocks() as image_processing_interface:
        gr.Markdown("## 图像处理")
        gr.Markdown("提供图片去背景、图片混合等图像处理功能")

        with gr.Tabs():
            # Tab 1: 图片去背景
            with gr.Tab("图片去背景"):
                gr.Markdown("### 🖼️ 去除图片背景")
                gr.Markdown("使用 RMBG-1.4 模型自动去除图片背景，生成透明背景的 PNG 图片")

                with gr.Row():
                    with gr.Column():
                        # 输入类型选择
                        bg_input_type = gr.Radio(
                            choices=["upload", "path"],
                            value="upload",
                            label="输入类型"
                        )

                        # 上传图片区域
                        with gr.Group(visible=True) as bg_upload_group:
                            input_image = gr.Image(
                                label="上传图片",
                                type="filepath",
                                sources=["upload", "clipboard"]
                            )

                        # 路径输入区域
                        with gr.Group(visible=False) as bg_path_group:
                            bg_image_path_input = gr.Textbox(
                                label="图片文件路径",
                                placeholder="输入图片文件的URL或本地路径",
                                info="支持http/https URL或本地文件路径"
                            )

                        remove_bg_btn = gr.Button("🎨 去除背景", variant="primary")

                    with gr.Column():
                        # 输出区域
                        output_image = gr.Image(
                            label="处理结果",
                            type="filepath"
                        )
                        bg_status_info = gr.HTML("<div>等待提交任务...</div>")
                        bg_result_status = gr.JSON(label="详细状态", visible=False)

                # 绑定事件
                def update_bg_input_visibility(input_type):
                    return (
                        gr.update(visible=(input_type == "upload")),
                        gr.update(visible=(input_type == "path"))
                    )

                bg_input_type.change(
                    update_bg_input_visibility,
                    inputs=[bg_input_type],
                    outputs=[bg_upload_group, bg_path_group]
                )

                remove_bg_btn.click(
                    fn=process_remove_background,
                    inputs=[bg_input_type, input_image, bg_image_path_input],
                    outputs=[output_image, bg_status_info, bg_result_status]
                )

            # Tab 2: 图片混合
            with gr.Tab("图片混合"):
                gr.Markdown("### 🎭 图片混合")
                gr.Markdown("将第二张图片叠加到第一张图片上，支持位置调整、缩放和自动去背景")

                with gr.Row():
                    with gr.Column():
                        # 输入类型选择
                        blend_input_type = gr.Radio(
                            choices=["upload", "path"],
                            value="upload",
                            label="输入类型"
                        )

                        # 上传图片区域
                        with gr.Group(visible=True) as blend_upload_group:
                            gr.Markdown("#### 📤 输入图片")
                            
                            base_image_input = gr.Image(
                                label="基础图片（第一张）",
                                type="filepath",
                                sources=["upload", "clipboard"]
                            )
                            
                            overlay_image_input = gr.Image(
                                label="叠加图片（第二张）",
                                type="filepath",
                                sources=["upload", "clipboard"]
                            )

                        # 路径输入区域
                        with gr.Group(visible=False) as blend_path_group:
                            gr.Markdown("#### 📤 输入图片路径")
                            
                            base_image_path_input = gr.Textbox(
                                label="基础图片路径（第一张）",
                                placeholder="输入图片文件的URL或本地路径",
                                info="支持http/https URL或本地文件路径"
                            )
                            
                            overlay_image_path_input = gr.Textbox(
                                label="叠加图片路径（第二张）",
                                placeholder="输入图片文件的URL或本地路径",
                                info="支持http/https URL或本地文件路径"
                            )

                        gr.Markdown("#### ⚙️ 混合参数")

                        with gr.Row():
                            position_x = gr.Number(
                                label="X 坐标",
                                value=85,
                                minimum=0,
                                maximum=5000,
                                step=1,
                                info="叠加图片在基础图片上的水平位置"
                            )
                            position_y = gr.Number(
                                label="Y 坐标",
                                value=90,
                                minimum=0,
                                maximum=5000,
                                step=1,
                                info="叠加图片在基础图片上的垂直位置"
                            )

                        with gr.Row():
                            scale = gr.Slider(
                                minimum=0.1,
                                maximum=3.0,
                                value=1.0,
                                step=0.1,
                                label="缩放比例",
                                info="叠加图片的缩放比例（1.0=原始大小，当宽高都为0时使用）"
                            )
                            auto_remove_bg = gr.Checkbox(
                                label="自动去背景",
                                value=False,
                                info="自动去除叠加图片的背景"
                            )

                        with gr.Row():
                            width = gr.Number(
                                label="宽度（像素）",
                                value=425,
                                minimum=0,
                                maximum=5000,
                                step=1,
                                info="直接指定叠加图片的宽度（0=不指定，使用缩放比例）"
                            )
                            height = gr.Number(
                                label="高度（像素）",
                                value=615,
                                minimum=0,
                                maximum=5000,
                                step=1,
                                info="直接指定叠加图片的高度（0=不指定，使用缩放比例）"
                            )

                        blend_btn = gr.Button("🎭 混合图片", variant="primary")

                    with gr.Column():
                        # 输出区域
                        gr.Markdown("#### 📝 处理结果")
                        
                        blended_image = gr.Image(
                            label="混合结果",
                            type="filepath"
                        )
                        
                        blend_status_info = gr.HTML("<div>等待提交任务...</div>")
                        blend_result_status = gr.JSON(label="详细状态", visible=False)

                # 绑定事件
                blend_btn.click(
                    fn=process_blend_images,
                    inputs=[
                        blend_input_type,
                        base_image_input,
                        overlay_image_input,
                        base_image_path_input,
                        overlay_image_path_input,
                        position_x,
                        position_y,
                        scale,
                        width,
                        height,
                        auto_remove_bg
                    ],
                    outputs=[blended_image, blend_status_info, blend_result_status]
                )

                # 绑定事件
                def update_blend_input_visibility(input_type):
                    return (
                        gr.update(visible=(input_type == "upload")),
                        gr.update(visible=(input_type == "path"))
                    )

                blend_input_type.change(
                    update_blend_input_visibility,
                    inputs=[blend_input_type],
                    outputs=[blend_upload_group, blend_path_group]
                )

    return image_processing_interface


async def process_remove_background(
    input_type: str,
    input_image: Optional[str],
    image_path: Optional[str]
) -> Tuple[Optional[str], str, dict]:
    """
    处理图片去背景

    Args:
        input_type: 输入类型 (upload/path)
        input_image: 上传的图片路径
        image_path: 图片文件路径（URL或本地路径）

    Returns:
        Tuple: (输出图片路径, 状态信息, 详细状态)
    """
    try:
        # 参数验证
        actual_image_path = None
        
        if input_type == "upload":
            if not input_image:
                status_html = """
                <div style="color: red;">
                    <h3>❌ 处理失败</h3>
                    <p>错误: 请上传图片</p>
                </div>
                """
                return (
                    None,
                    status_html,
                    {"success": False, "error": "请上传图片"}
                )
            actual_image_path = input_image
        else:  # path
            if not image_path or not image_path.strip():
                status_html = """
                <div style="color: red;">
                    <h3>❌ 处理失败</h3>
                    <p>错误: 请提供图片文件路径</p>
                </div>
                """
                return (
                    None,
                    status_html,
                    {"success": False, "error": "请提供图片文件路径"}
                )
            actual_image_path = image_path

        Logger.info(f"开始处理图片去背景 - input_type: {input_type}, path: {actual_image_path}")

        # 执行去背景
        result = await image_processing_module.remove_background(
            image_path=actual_image_path,
            input_type=input_type
        )

        # 构建状态信息
        if result["success"]:
            output_path = result.get("output_path")
            status_html = f"""
            <div style="color: green;">
                <h3>✅ 处理完成</h3>
                <p>输出文件: {Path(output_path).name}</p>
                <p>原始尺寸: {result.get('original_size')}</p>
            </div>
            """
        else:
            status_html = f"""
            <div style="color: red;">
                <h3>❌ 处理失败</h3>
                <p>错误: {result.get('error', '未知错误')}</p>
            </div>
            """

        return (
            result.get("output_path") if result["success"] else None,
            status_html,
            result
        )

    except Exception as e:
        Logger.error(f"Background removal error: {e}")
        import traceback
        Logger.error(traceback.format_exc())

        status_html = f"""
        <div style="color: red;">
            <h3>❌ 处理失败</h3>
            <p>错误: {str(e)}</p>
        </div>
        """

        return (
            None,
            status_html,
            {"success": False, "error": str(e)}
        )


async def process_blend_images(
    input_type: str,
    base_image: Optional[str],
    overlay_image: Optional[str],
    base_image_path: Optional[str],
    overlay_image_path: Optional[str],
    position_x: int,
    position_y: int,
    scale: float,
    width: int,
    height: int,
    auto_remove_bg: bool
) -> Tuple[Optional[str], str, dict]:
    """
    处理图片混合

    Args:
        input_type: 输入类型 (upload/path)
        base_image: 上传的基础图片路径
        overlay_image: 上传的叠加图片路径
        base_image_path: 基础图片文件路径（URL或本地路径）
        overlay_image_path: 叠加图片文件路径（URL或本地路径）
        position_x: X坐标
        position_y: Y坐标
        scale: 缩放比例
        width: 宽度（0表示不指定）
        height: 高度（0表示不指定）
        auto_remove_bg: 是否自动去背景

    Returns:
        Tuple: (输出图片路径, 状态信息, 详细状态)
    """
    try:
        # 参数验证
        actual_base_path = None
        actual_overlay_path = None
        
        if input_type == "upload":
            if not base_image or not overlay_image:
                status_html = """
                <div style="color: red;">
                    <h3>❌ 处理失败</h3>
                    <p>错误: 请上传两张图片</p>
                </div>
                """
                return (
                    None,
                    status_html,
                    {"success": False, "error": "请上传两张图片"}
                )
            actual_base_path = base_image
            actual_overlay_path = overlay_image
        else:  # path
            if not base_image_path or not base_image_path.strip() or not overlay_image_path or not overlay_image_path.strip():
                status_html = """
                <div style="color: red;">
                    <h3>❌ 处理失败</h3>
                    <p>错误: 请提供两张图片的文件路径</p>
                </div>
                """
                return (
                    None,
                    status_html,
                    {"success": False, "error": "请提供两张图片的文件路径"}
                )
            actual_base_path = base_image_path
            actual_overlay_path = overlay_image_path

        Logger.info(f"开始处理图片混合 - input_type: {input_type}, base: {actual_base_path}, overlay: {actual_overlay_path}")

        # 处理宽高参数（0表示不指定）
        width_param = width if width > 0 else None
        height_param = height if height > 0 else None

        # 执行图片混合
        result = await image_processing_module.blend_images(
            base_image_path=actual_base_path,
            overlay_image_path=actual_overlay_path,
            input_type=input_type,
            position_x=position_x,
            position_y=position_y,
            scale=scale,
            width=width_param,
            height=height_param,
            remove_bg=auto_remove_bg
        )

        # 构建状态信息
        if result["success"]:
            output_path = result.get("output_path")
            
            # 确定尺寸调整方式
            size_adjustment_info = ""
            if result.get("width") and result.get("height"):
                size_adjustment_info = f"<p>尺寸调整: 直接指定 ({result.get('width')} x {result.get('height')})</p>"
            else:
                size_adjustment_info = f"<p>尺寸调整: 缩放比例 ({result.get('scale')})</p>"
            
            status_html = f"""
            <div style="color: green;">
                <h3>✅ 处理完成</h3>
                <p>输出文件: {Path(output_path).name}</p>
                <p>基础图片尺寸: {result.get('base_size')}</p>
                <p>叠加图片尺寸: {result.get('overlay_size')}</p>
                <p>叠加位置: ({result.get('position')[0]}, {result.get('position')[1]})</p>
                {size_adjustment_info}
                <p>背景已去除: {'是' if result.get('background_removed') else '否'}</p>
            </div>
            """
        else:
            status_html = f"""
            <div style="color: red;">
                <h3>❌ 处理失败</h3>
                <p>错误: {result.get('error', '未知错误')}</p>
            </div>
            """

        return (
            result.get("output_path") if result["success"] else None,
            status_html,
            result
        )

    except Exception as e:
        Logger.error(f"Image blending error: {e}")
        import traceback
        Logger.error(traceback.format_exc())

        status_html = f"""
        <div style="color: red;">
            <h3>❌ 处理失败</h3>
            <p>错误: {str(e)}</p>
        </div>
        """

        return (
            None,
            status_html,
            {"success": False, "error": str(e)}
        )