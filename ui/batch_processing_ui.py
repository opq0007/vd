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
                with gr.Row():
                    gr.Markdown("### 📋 选择模板")
                    refresh_templates_btn = gr.Button("🔄", size="sm", variant="secondary", scale=0, min_width=40)

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
                    info="选择要使用的处理模板",
                    scale=1
                )
                
                # 模板类型标识（隐藏）
                is_aigc_template = gr.State(value=False)

                # 参数输入区域 - 普通模板
                with gr.Group(visible=True) as normal_params_group:
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

                # 参数输入区域 - AIGC 模板
                with gr.Group(visible=False) as aigc_params_group:
                    gr.Markdown("### 📝 AIGC 全自动视频生成参数")
                    
                    # 视频主题
                    aigc_topic_input = gr.Textbox(
                        label="视频主题",
                        placeholder="例如：如何制作美味的意大利面",
                        lines=2
                    )
                    
                    # 视频配置
                    with gr.Row():
                        aigc_video_size_dropdown = gr.Dropdown(
                            label="视频尺寸",
                            choices=[
                                ("竖屏 (1080x1920)", "portrait"),
                                ("横屏 (1920x1080)", "landscape"),
                                ("方形 (1080x1080)", "square")
                            ],
                            value="portrait"
                        )
                        aigc_duration_slider = gr.Slider(
                            label="视频时长（秒）",
                            minimum=10,
                            maximum=300,
                            value=60,
                            step=10
                        )
                    
                    with gr.Row():
                        aigc_fps_slider = gr.Slider(
                            label="帧率",
                            minimum=15,
                            maximum=60,
                            value=25,
                            step=5
                        )
                        aigc_template_dropdown = gr.Dropdown(
                            label="视频模板（可选）",
                            choices=[("不使用模板", "")],
                            value=""
                        )
                    
                    # LLM 配置
                    gr.Markdown("### 🤖 LLM 配置")
                    with gr.Accordion("高级 LLM 设置", open=False):
                        aigc_llm_model_input = gr.Textbox(
                            label="LLM 模型",
                            value="glm-4.5-flash",
                            placeholder="例如：glm-4.5-flash"
                        )
                        aigc_llm_api_key_input = gr.Textbox(
                            label="LLM API Key",
                            type="password",
                            placeholder="请输入智谱 AI API Key"
                        )
                    
                    # ComfyUI 配置
                    gr.Markdown("### 🎨 ComfyUI 配置")
                    with gr.Accordion("ComfyUI 设置", open=False):
                        aigc_comfyui_server_url_input = gr.Textbox(
                            label="ComfyUI 服务器地址",
                            value="http://127.0.0.1:8188",
                            placeholder="http://127.0.0.1:8188"
                        )
                        aigc_image_workflow_path_input = gr.Textbox(
                            label="图片生成工作流路径",
                            placeholder="留空使用默认工作流"
                        )
                        aigc_video_workflow_path_input = gr.Textbox(
                            label="视频生成工作流路径",
                            placeholder="留空使用默认工作流"
                        )
                    
                    # TTS 配置
                    gr.Markdown("### 🗣️ TTS 配置")
                    with gr.Accordion("语音合成设置", open=False):
                        aigc_tts_feat_id_input = gr.Textbox(
                            label="预编码特征 ID",
                            placeholder="例如：atm"
                        )
                        aigc_tts_prompt_wav_input = gr.Textbox(
                            label="参考音频路径",
                            placeholder="留空使用默认声音"
                        )
                        aigc_tts_prompt_text_input = gr.Textbox(
                            label="参考文本",
                            placeholder="留空使用默认声音"
                        )
                    
                    # 背景音乐配置
                    gr.Markdown("### 🎵 背景音乐配置")
                    with gr.Accordion("背景音乐设置", open=False):
                        aigc_background_music_input = gr.Textbox(
                            label="背景音乐路径",
                            placeholder="留空不添加背景音乐"
                        )
                        aigc_bgm_volume_slider = gr.Slider(
                            label="背景音乐音量",
                            minimum=0.0,
                            maximum=1.0,
                            value=0.3,
                            step=0.1
                        )
                
                # 执行按钮
                execute_btn = gr.Button("🚀 开始处理", variant="primary")
                
            with gr.Column():
                # 进度显示区域
                gr.Markdown("### 📊 处理进度")
                
                progress_bar = gr.Progress()
                status_info = gr.HTML("<div>等待开始...</div>")
                
                # 任务执行详情
                gr.Markdown("### 📋 任务执行详情")
                task_results = gr.HTML("<div>等待开始...</div>")
                
                # 视频预览
                gr.Markdown("### 🎥 最终视频预览")
                video_preview = gr.Video(label="视频预览", visible=False)
        
        # 事件处理
        def refresh_template_list():
            """刷新模板列表"""
            # 重新加载模板
            template_manager.reload_templates()

            # 获取更新后的模板列表
            template_names = template_manager.get_template_names()

            if not template_names:
                template_names = ["无可用模板"]
                default_template = ""
            else:
                default_template = template_names[0]

            return gr.Dropdown(choices=template_names, value=default_template)

        def update_template_info(template_name):
            """更新模板信息并自动填充参数默认值"""
            if not template_name or template_name == "无可用模板":
                return (
                    "",  # username
                    6,   # age
                    "生日快乐",  # theme
                    "奥特曼",  # character
                    "",  # sub_character
                    "",  # tts_text
                    gr.update(visible=True),   # normal_params_group
                    gr.update(visible=False),  # aigc_params_group
                    False  # is_aigc_template
                )

            info = template_manager.get_template_info(template_name)
            template = template_manager.get_template(template_name)
            
            # 检查是否为 AIGC 模板
            is_aigc = template.get("is_aigc_template", False) if template else False
            
            if is_aigc:
                # AIGC 模板 - 显示 AIGC 参数界面
                parameters = info.get("parameters", {})
                return (
                    "",  # username
                    6,   # age
                    "生日快乐",  # theme
                    "奥特曼",  # character
                    "",  # sub_character
                    "",  # tts_text
                    gr.update(visible=False),  # normal_params_group
                    gr.update(visible=True),   # aigc_params_group
                    True  # is_aigc_template
                )
            else:
                # 普通模板 - 显示普通参数界面
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
                    username,
                    age,
                    theme_text,
                    character,
                    sub_character,
                    tts_text,
                    gr.update(visible=True),   # normal_params_group
                    gr.update(visible=False),  # aigc_params_group
                    False  # is_aigc_template
                )
        
        template_dropdown.change(
            update_template_info,
            inputs=[template_dropdown],
            outputs=[
                username_input,
                age_input,
                theme_input,
                character_input,
                sub_character_input,
                tts_text_input,
                normal_params_group,
                aigc_params_group,
                is_aigc_template
            ]
        )

        refresh_templates_btn.click(
            refresh_template_list,
            outputs=[template_dropdown]
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
            user_images_paths,
            is_aigc_template,
            # AIGC 参数
            aigc_topic,
            aigc_video_size,
            aigc_duration,
            aigc_fps,
            aigc_template,
            aigc_llm_model,
            aigc_llm_api_key,
            aigc_comfyui_server_url,
            aigc_image_workflow_path,
            aigc_video_workflow_path,
            aigc_tts_feat_id,
            aigc_tts_prompt_wav,
            aigc_tts_prompt_text,
            aigc_background_music,
            aigc_bgm_volume
        ):
            """执行批量处理"""
            try:
                if not template_name or template_name == "无可用模板":
                    return (
                        "<div style='color: red;'>请选择有效的模板</div>",
                        None,
                        None
                    )
                
                # 检查是否为 AIGC 模板
                if is_aigc_template:
                    # 使用 auto_video_task_module 处理 AIGC 模板
                    from modules.auto_video_task_module import auto_video_task_module
                    
                    # 进度回调
                    async def aigc_progress_callback(progress_info):
                        step = progress_info.get("step", "")
                        prog = progress_info.get("progress", 0)
                        message = progress_info.get("message", "")

                        # 更新进度文本
                        step_messages = {
                            "script": "正在生成视频文案...",
                            "media": "正在生成 AI 配图/视频...",
                            "tts": "正在合成语音解说...",
                            "video_segments": "正在生成视频片段...",
                            "merge": "正在合并视频片段...",
                            "bgm": "正在添加背景音乐...",
                            "template": "正在应用视频模板...",
                            "complete": "视频生成完成！",
                            "error": f"错误：{message}"
                        }

                        progress_text = step_messages.get(step, message)
                        return f"""
                        <div>
                            <p><strong>当前步骤:</strong> {progress_text}</p>
                            <p><strong>进度:</strong> {prog:.1%}</p>
                        </div>
                        """
                    
                    # 执行 AIGC 视频生成
                    result = await auto_video_task_module.generate_video_from_topic(
                        topic=aigc_topic,
                        video_size=aigc_video_size,
                        duration=aigc_duration,
                        fps=aigc_fps,
                        llm_model=aigc_llm_model,
                        llm_api_key=aigc_llm_api_key,
                        comfyui_server_url=aigc_comfyui_server_url,
                        image_workflow_path=aigc_image_workflow_path,
                        video_workflow_path=aigc_video_workflow_path,
                        tts_feat_id=aigc_tts_feat_id,
                        tts_prompt_wav=aigc_tts_prompt_wav,
                        tts_prompt_text=aigc_tts_prompt_text,
                        background_music=aigc_background_music,
                        background_music_volume=aigc_bgm_volume,
                        template_name=aigc_template,
                        progress_callback=aigc_progress_callback
                    )
                    
                    # 生成总体状态信息
                    if result["success"]:
                        status_html = f"""
                        <div style="color: green;">
                            <h3>✅ AIGC 视频生成完成</h3>
                            <p>主题: {result['topic']}</p>
                            <p>场景数: {result['script']['scene_count']}</p>
                            <p>总时长: {result['script']['total_duration']:.1f}秒</p>
                        </div>
                        """
                        task_results_html = f"""
                        <div>
                            <h4>生成详情</h4>
                            <p><strong>输出视频:</strong> {result['output_video']}</p>
                            <p><strong>任务目录:</strong> {result['job_dir']}</p>
                        </div>
                        """
                        video_output = result["output_video"]
                    else:
                        status_html = f"""
                        <div style="color: red;">
                            <h3>❌ AIGC 视频生成失败</h3>
                            <p>错误: {result.get('error', '未知错误')}</p>
                        </div>
                        """
                        task_results_html = ""
                        video_output = None
                    
                    return (
                        status_html,
                        task_results_html,
                        gr.update(value=video_output, visible=bool(video_output))
                    )
                else:
                    # 使用普通模板处理
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

                    return (
                        status_html,
                        task_results_html,
                        gr.update(value=video_output, visible=bool(video_output))
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
                    "",
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
                user_images_paths,
                is_aigc_template,
                # AIGC 参数
                aigc_topic_input,
                aigc_video_size_dropdown,
                aigc_duration_slider,
                aigc_fps_slider,
                aigc_template_dropdown,
                aigc_llm_model_input,
                aigc_llm_api_key_input,
                aigc_comfyui_server_url_input,
                aigc_image_workflow_path_input,
                aigc_video_workflow_path_input,
                aigc_tts_feat_id_input,
                aigc_tts_prompt_wav_input,
                aigc_tts_prompt_text_input,
                aigc_background_music_input,
                aigc_bgm_volume_slider
            ],
            outputs=[
                status_info,
                task_results,
                video_preview
            ]
        )

        # 页面加载时自动刷新模板列表
        batch_processing_interface.load(
            refresh_template_list,
            outputs=[template_dropdown]
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
    from utils.result_formatter import result_formatter
    return result_formatter.generate_task_results_html(result)


def extract_output_files_from_task(task_output: Dict[str, Any]) -> str:
    """
    从任务输出中提取文件路径（格式化为前端展示格式）
    
    Args:
        task_output: 任务输出
        
    Returns:
        格式化的文件路径字符串（用于前端展示）
    """
    from utils.result_formatter import result_formatter
    return result_formatter.extract_output_files_from_task(task_output, format_for_display=True)


def extract_final_video(result: Dict[str, Any]) -> Optional[str]:
    """
    从执行结果中提取最终视频文件

    Args:
        result: 模板执行结果

    Returns:
        视频文件路径，如果没有则返回None
    """
    from utils.result_formatter import result_formatter
    return result_formatter.extract_final_video(result)