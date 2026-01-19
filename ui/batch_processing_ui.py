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
                
                # 用户图片输入 - 支持两种方式
                with gr.Row():
                    with gr.Column():
                        # 方式1：文件上传
                        user_images_upload = gr.File(
                            label="方式1：上传图片（0-6张）",
                            file_count="multiple",
                            file_types=["image"]
                        )
                        gr.Markdown("*直接上传图片文件*")
                    
                    with gr.Column():
                        # 方式2：路径输入
                        user_images_paths = gr.Textbox(
                            label="方式2：图片路径（0-6张）",
                            lines=5,
                            placeholder="输入图片文件路径，每行一个，例如：\n/path/to/image1.jpg\nC:/images/image2.png\nhttps://example.com/image3.jpg"
                        )
                        gr.Markdown("*支持 http/https URL 或本地文件路径，兼容 Windows (C:/) 和 Linux (/) 路径*")
                
                gr.Markdown("**提示：两种方式二选一，优先使用上传方式**")
                
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
                
                # 任务执行详情
                gr.Markdown("### 📋 任务执行详情")
                task_results = gr.HTML("<div>等待开始...</div>")
                
                # 视频预览
                gr.Markdown("### 🎥 最终视频预览")
                video_preview = gr.Video(label="视频预览", visible=False)
                
                # 文件下载
                gr.Markdown("### 📥 下载输出文件")
                output_files = gr.File(label="下载输出文件", visible=False)
        
        # 事件处理
        def update_template_info(template_name):
            """更新模板信息并自动填充参数默认值"""
            if not template_name or template_name == "无可用模板":
                return (
                    gr.JSON(value={}, visible=False),
                    "",  # username
                    6,   # age
                    "生日快乐",  # theme
                    "奥特曼",  # character
                    "",  # sub_character
                    "",  # tts_text
                )
            
            info = template_manager.get_template_info(template_name)
            parameters = info.get("parameters", {})
            
            # 从模板参数中提取默认值
            # 使用嵌套的get方法安全地获取参数值
            username = parameters.get("username", {}).get("default", "")
            age = parameters.get("age", {}).get("default", 6)
            theme_text = parameters.get("theme_text", {}).get("default", "生日快乐")
            
            # character参数：优先从parameters中获取，否则从模板元数据中获取
            character = parameters.get("character", {}).get("default", "")
            if not character:
                character = info.get("character", "奥特曼")
            
            # sub_character参数：从parameters中获取，如果不存在则为空
            sub_character = parameters.get("sub_character", {}).get("default", "")
            
            # tts_text参数：从parameters中获取默认值
            tts_text = parameters.get("tts_text", {}).get("default", "")
            
            return (
                gr.JSON(value=info, visible=True),
                username,
                age,
                theme_text,
                character,
                sub_character,
                tts_text,
            )
        
        template_dropdown.change(
            update_template_info,
            inputs=[template_dropdown],
            outputs=[
                template_info,
                username_input,
                age_input,
                theme_input,
                character_input,
                sub_character_input,
                tts_text_input,
            ]
        )
        
        async def execute_batch_processing(
            template_name,
            username,
            age,
            theme,
            character,
            sub_character,
            tts_text,
            user_images_upload,
            user_images_paths
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
                
                # 处理用户图片 - 优先使用上传方式
                if user_images_upload:
                    if isinstance(user_images_upload, list):
                        for img in user_images_upload[:6]:  # 最多6张图片
                            if isinstance(img, str):
                                parameters["user_images"].append(img)
                            elif hasattr(img, 'name'):
                                parameters["user_images"].append(img.name)
                    else:
                        if hasattr(user_images_upload, 'name'):
                            parameters["user_images"].append(user_images_upload.name)
                elif user_images_paths and user_images_paths.strip():
                    # 使用路径输入方式
                    paths = [p.strip() for p in user_images_paths.strip().split('\n') if p.strip()]
                    for path in paths[:6]:  # 最多6张图片
                        parameters["user_images"].append(path)
                
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
                
                # 生成任务执行结果详情
                task_results_html = generate_task_results_html(result)
                
                # 生成总体状态信息
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
                
                # 从任务输出中提取最终视频文件
                video_output = extract_final_video(result)
                output_file_list = extract_output_files(result)
                
                return (
                    status_html,
                    task_results_html,
                    result,
                    gr.update(value=video_output, visible=bool(video_output)),
                    gr.update(value=output_file_list, visible=bool(output_file_list))
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
                user_images_upload,
                user_images_paths
            ],
            outputs=[
                status_info,
                task_results,
                result_status,
                video_preview,
                output_files
            ]
        )
    
    return batch_processing_interface


def generate_task_results_html(result: Dict[str, Any]) -> str:
    """
    生成任务执行结果的HTML详情
    
    Args:
        result: 模板执行结果
        
    Returns:
        HTML字符串
    """
    if not result.get("success"):
        return "<div style='color: red;'>处理失败，无任务结果</div>"
    
    task_outputs = result.get("task_outputs", {})
    total_tasks = result.get("total_tasks", 0)
    completed_tasks = result.get("completed_tasks", 0)
    
    html = f"""
    <div style="border: 1px solid #ddd; padding: 15px; border-radius: 5px; background-color: #f9f9f9;">
        <h4 style="margin-top: 0; color: #333;">📋 任务执行详情</h4>
        <p style="margin-bottom: 15px;">
            <strong>总任务数:</strong> {total_tasks} | 
            <strong>完成任务:</strong> {completed_tasks} | 
            <strong>成功率:</strong> {completed_tasks/total_tasks*100:.1f}%
        </p>
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
            <thead>
                <tr style="background-color: #4CAF50; color: white;">
                    <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">序号</th>
                    <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">任务名称</th>
                    <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">任务类型</th>
                    <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">状态</th>
                    <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">输出文件</th>
                    <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">备注</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # 获取模板任务列表（按执行顺序）
    template = template_manager.get_template(result.get("template_name", ""))
    if template:
        tasks = template.get("tasks", [])
        for idx, task in enumerate(tasks, 1):
            task_id = task["id"]
            task_name = task["name"]
            task_type = task["type"]
            
            # 获取任务执行结果
            task_output = task_outputs.get(task_id, {})
            
            # 判断任务状态
            if "error" in task_output:
                status = "❌ 失败"
                status_color = "#f44336"
                error_msg = task_output.get("error", "未知错误")
                output_files = "-"
                remark = f"错误: {error_msg}"
            elif task_output:
                status = "✅ 成功"
                status_color = "#4CAF50"
                # 提取输出文件
                output_files = extract_output_files_from_task(task_output)
                remark = "执行成功"
            else:
                status = "⏭️ 跳过"
                status_color = "#FF9800"
                output_files = "-"
                remark = "未执行"
            
            html += f"""
                <tr style="background-color: {'#f5f5f5' if idx % 2 == 0 else 'white'};">
                    <td style="padding: 8px; border: 1px solid #ddd;">{idx}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{task_name}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{task_type}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; color: {status_color}; font-weight: bold;">{status}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; font-size: 12px;">{output_files}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; font-size: 12px;">{remark}</td>
                </tr>
            """
    
    html += """
            </tbody>
        </table>
    </div>
    """
    
    return html


def extract_output_files_from_task(task_output: Dict[str, Any]) -> str:
    """
    从任务输出中提取文件路径
    
    Args:
        task_output: 任务输出
        
    Returns:
        文件路径字符串
    """
    files = []
    
    # 检查常见的输出字段
    for key in ["output", "output_path", "audio_path", "video_path", "image_path", "output_file"]:
        if key in task_output:
            value = task_output[key]
            if isinstance(value, str):
                files.append(value)
            elif isinstance(value, list):
                files.extend([str(v) for v in value if v])
    
    # 如果没有找到，检查整个字典
    if not files:
        for key, value in task_output.items():
            if isinstance(value, str) and ("output" in key.lower() or "path" in key.lower()):
                files.append(value)
    
    # 限制显示的文件数量
    if len(files) > 3:
        return f"{files[0]} ... (+{len(files)-1} more)"
    elif files:
        return "<br>".join(files[:3])
    else:
        return "-"


def extract_final_video(result: Dict[str, Any]) -> Optional[str]:
    """
    从执行结果中提取最终视频文件
    
    Args:
        result: 模板执行结果
        
    Returns:
        视频文件路径，如果没有则返回None
    """
    task_outputs = result.get("task_outputs", {})
    
    # 查找视频合并任务的输出
    for task_id, task_output in task_outputs.items():
        if "error" not in task_output:
            # 检查常见的视频输出字段
            for key in ["output", "output_path", "video_path", "output_file"]:
                if key in task_output:
                    value = task_output[key]
                    if isinstance(value, str) and value.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
                        return value
                    elif isinstance(value, list) and value:
                        # 检查列表中的第一个视频文件
                        for item in value:
                            if isinstance(item, str) and item.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
                                return item
    
    return None


def extract_output_files(result: Dict[str, Any]) -> Optional[str]:
    """
    从执行结果中提取所有输出文件
    
    Args:
        result: 模块执行结果
        
    Returns:
        输出文件路径，如果没有则返回None
    """
    task_outputs = result.get("task_outputs", {})
    files = []
    
    # 收集所有任务输出文件
    for task_id, task_output in task_outputs.items():
        if "error" not in task_output:
            for key, value in task_output.items():
                if isinstance(value, str) and value and ("output" in key.lower() or "path" in key.lower()):
                    files.append(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str) and item:
                            files.append(item)
    
    # 返回第一个文件（通常是最终输出）
    if files:
        return files[0]
    
    return None