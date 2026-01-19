"""
综合处理 UI 组件

提供基于模板的自动化视频处理界面。
"""

import gradio as gr
from typing import Dict, Any, List, Optional
from pathlib import Path

from modules.template_manager import template_manager
from modules.task_orchestrator import task_orchestrator
from utils.logger import Logger


def create_batch_processing_interface() -> gr.Blocks:
    """
    创建综合处理界面

    Returns:
        gr.Blocks: Gradio 界面块
    """
    with gr.Blocks() as batch_processing_interface:
        gr.Markdown("## 🚀 综合处理")
        gr.Markdown("基于模板的自动化视频处理，一键完成复杂操作")

        with gr.Row():
            with gr.Column():
                # 模板选择区域
                gr.Markdown("### 📋 选择模板")
                template_names = template_manager.get_template_names()
                
                if not template_names:
                    template_names = ["无可用模板"]
                    default_template = ""
                else:
                    default_template = template_names[0]
                
                template_dropdown = gr.Dropdown(
                    choices=template_names,
                    value=default_template,
                    label="选择模板",
                    info="选择要使用的处理模板"
                )
                
                template_info = gr.JSON(label="模板信息", visible=False)
                
                # 参数输入区域
                gr.Markdown("### 📝 输入参数")
                parameter_inputs = {}
                
                # 基础参数
                with gr.Row():
                    username_input = gr.Textbox(
                        label="用户名",
                        placeholder="输入用户名",
                        value=""
                    )
                    age_input = gr.Number(
                        label="年龄",
                        value=6,
                        minimum=1,
                        maximum=120
                    )
                
                with gr.Row():
                    theme_input = gr.Textbox(
                        label="主题",
                        placeholder="例如：生日快乐、儿童节快乐",
                        value="生日快乐"
                    )
                    character_input = gr.Textbox(
                        label="操作模板对象",
                        placeholder="例如：奥特曼、艾莎公主",
                        value="奥特曼"
                    )
                
                with gr.Row():
                    sub_character_input = gr.Textbox(
                        label="二级对象（可选）",
                        placeholder="例如：具体哪个奥特曼",
                        value=""
                    )
                
                # TTS 文本
                tts_text_input = gr.Textbox(
                    label="TTS 文本内容",
                    placeholder="输入要合成的语音文本",
                    value="",
                    lines=3
                )
                
                # 用户图片上传
                user_images_input = gr.File(
                    label="用户图片（0-5张）",
                    file_count="multiple",
                    file_types=["image"]
                )
                
                # 执行按钮
                execute_btn = gr.Button("🚀 开始处理", variant="primary")
                
            with gr.Column():
                # 进度显示区域
                gr.Markdown("### 📊 处理进度")
                
                progress_bar = gr.Progress()
                status_info = gr.HTML("<div>等待开始...</div>")
                
                # 任务列表
                gr.Markdown("### 📋 任务列表")
                task_list = gr.JSON(label="任务列表", visible=False)
                
                # 结果展示区域
                gr.Markdown("### 🎬 处理结果")
                result_status = gr.JSON(label="详细状态", visible=False)
                
                # 视频预览
                video_preview = gr.Video(label="视频预览", visible=False)
                
                # 文件下载
                output_files = gr.File(label="下载输出文件", visible=False)
        
        # 事件处理
        def update_template_info(template_name):
            """更新模板信息"""
            if not template_name or template_name == "无可用模板":
                return gr.JSON(value={}, visible=False)
            
            info = template_manager.get_template_info(template_name)
            return gr.JSON(value=info, visible=True)
        
        template_dropdown.change(
            update_template_info,
            inputs=[template_dropdown],
            outputs=[template_info]
        )
        
        async def execute_batch_processing(
            template_name,
            username,
            age,
            theme,
            character,
            sub_character,
            tts_text,
            user_images
        ):
            """执行批量处理"""
            try:
                if not template_name or template_name == "无可用模板":
                    return (
                        "<div style='color: red;'>请选择有效的模板</div>",
                        None,
                        None,
                        None
                    )
                
                # 准备参数
                parameters = {
                    "username": username,
                    "age": age,
                    "theme": theme,
                    "character": character,
                    "sub_character": sub_character,
                    "tts_text": tts_text,
                    "user_images": []
                }
                
                # 处理用户图片
                if user_images:
                    if isinstance(user_images, list):
                        for img in user_images[:5]:  # 最多5张图片
                            if isinstance(img, str):
                                parameters["user_images"].append(img)
                            elif hasattr(img, 'name'):
                                parameters["user_images"].append(img.name)
                    else:
                        if hasattr(user_images, 'name'):
                            parameters["user_images"].append(user_images.name)
                
                # 进度回调
                async def progress_callback(progress_info):
                    status_html = f"""
                    <div>
                        <p><strong>当前任务:</strong> {progress_info['task_name']}</p>
                        <p><strong>进度:</strong> {progress_info['completed']}/{progress_info['total']} ({progress_info['progress']:.1%})</p>
                        <p><strong>状态:</strong> {progress_info['status']}</p>
                    </div>
                    """
                    return status_html
                
                # 执行模板
                result = await task_orchestrator.execute_template(
                    template_name,
                    parameters,
                    progress_callback
                )
                
                # 生成状态信息
                if result["success"]:
                    status_html = f"""
                    <div style="color: green;">
                        <h3>✅ 处理完成</h3>
                        <p>模板: {result['template_name']}</p>
                        <p>完成任务: {result['completed_tasks']}/{result['total_tasks']}</p>
                    </div>
                    """
                else:
                    status_html = f"""
                    <div style="color: red;">
                        <h3>❌ 处理失败</h3>
                        <p>错误: {result.get('error', '未知错误')}</p>
                    </div>
                    """
                
                # TODO: 从任务输出中提取视频文件
                video_output = None
                output_file_list = None
                
                return (
                    status_html,
                    result,
                    video_output,
                    output_file_list
                )
                
            except Exception as e:
                Logger.error(f"批量处理失败: {e}")
                import traceback
                Logger.error(traceback.format_exc())
                
                status_html = f"""
                <div style="color: red;">
                    <h3>❌ 处理失败</h3>
                    <p>错误: {str(e)}</p>
                </div>
                """
                
                return (
                    status_html,
                    {"error": str(e)},
                    None,
                    None
                )
        
        execute_btn.click(
            fn=execute_batch_processing,
            inputs=[
                template_dropdown,
                username_input,
                age_input,
                theme_input,
                character_input,
                sub_character_input,
                tts_text_input,
                user_images_input
            ],
            outputs=[
                status_info,
                result_status,
                video_preview,
                output_files
            ]
        )
    
    return batch_processing_interface