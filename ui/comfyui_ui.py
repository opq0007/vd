"""
ComfyUI 集成 UI 组件

提供与 ComfyUI 交互的 Web 界面。
"""

import gradio as gr
from typing import Optional, List
import json

from modules.comfyui_module import comfyui_module
from utils.logger import Logger


def list_workflow_templates() -> str:
    """
    列出 workflows 目录中的所有工作流模板

    Returns:
        str: 工作流模板列表
    """
    try:
        result = comfyui_module.list_workflows()

        if result.get("success"):
            workflows = result.get("workflows", [])
            output = f"✅ 找到 {result.get('count', 0)} 个工作流模板\n\n"
            output += "-" * 80 + "\n"

            for i, wf in enumerate(workflows, 1):
                output += f"\n{i}. {wf['filename']}\n"
                output += f"   路径: {wf['path']}\n"
                output += f"   大小: {wf['size']} 字节\n"

            output += "\n" + "-" * 80 + "\n"
            output += "\n💡 提示：选择一个工作流模板后，可以输入参数来替换模板中的占位符。\n"
            output += "占位符格式：{{参数名}}，例如 {{prompt}}、{{seed}} 等。"

            return output
        else:
            return f"❌ 获取工作流列表失败\n\n错误：{result.get('error')}"
    except Exception as e:
        Logger.error(f"获取工作流列表失败: {str(e)}")
        return f"❌ 获取工作流列表时发生异常\n\n详细信息：{str(e)}"


def load_workflow_template_info(workflow_name: str) -> str:
        """
        加载工作流模板信息

        Args:
            workflow_name: 工作流文件名

        Returns:
            str: 工作流信息
        """
        try:
            result = comfyui_module.load_workflow_file(workflow_name)

            if result.get("success"):
                workflow = result.get("workflow", {})
                output = f"✅ 工作流加载成功！\n\n"
                output += f"文件名：{result.get('workflow_name', '')}\n"
                output += f"路径：{result.get('workflow_path', '')}\n"
                output += f"节点数量：{len(workflow)}\n\n"

                # 使用模块方法提取参数
                params_result = comfyui_module.extract_parameters(workflow)
                params_found = params_result.get("parameters", [])

                if params_found:
                    output += f"📝 发现 {len(params_found)} 个参数占位符：\n"
                    for param in params_found:
                        output += f"  - {{{{ {param} }}}}\n"
                    output += "\n💡 提示：可以在参数 JSON 中定义这些参数的值。"
                else:
                    output += "📝 未发现参数占位符，此工作流不需要参数替换。"

                return output
            else:
                return f"❌ 加载工作流失败\n\n错误：{result.get('error')}"
        except Exception as e:
            Logger.error(f"加载工作流失败: {str(e)}")
            return f"❌ 加载工作流时发生异常\n\n详细信息：{str(e)}"


def upload_workflow_template(
    workflow_name: str,
    workflow_json: str,
    overwrite: bool = False
) -> str:
    """
    上传工作流模板

    Args:
        workflow_name: 工作流文件名
        workflow_json: 工作流 JSON 字符串
        overwrite: 是否覆盖已存在的文件

    Returns:
        str: 上传结果
    """
    try:
        if not workflow_name.strip():
            return "❌ 错误：工作流文件名不能为空"

        if not workflow_json.strip():
            return "❌ 错误：工作流 JSON 不能为空"

        result = comfyui_module.upload_workflow_template(
            workflow_name=workflow_name,
            workflow_json=workflow_json,
            overwrite=overwrite
        )

        if result.get("success"):
            output = f"✅ 工作流模板上传成功！\n\n"
            output += f"文件名：{result.get('workflow_name', '')}\n"
            output += f"路径：{result.get('workflow_path', '')}\n"
            output += f"消息：{result.get('message', '')}"
            return output
        else:
            return f"❌ 上传失败\n\n错误：{result.get('error')}"
    except Exception as e:
        Logger.error(f"上传工作流模板失败: {str(e)}")
        return f"❌ 上传工作流模板时发生异常\n\n详细信息：{str(e)}"


def on_workflow_select(workflow_name: str):
    """
    当选择工作流模板时的回调函数
    自动加载模板信息并生成参数示例

    Args:
        workflow_name: 工作流文件名

    Returns:
        tuple: (模板信息, 参数示例)
    """
    if not workflow_name:
        return "", ""

    try:
        # 加载模板信息
        info_result = comfyui_module.load_workflow_file(workflow_name)

        if not info_result.get("success"):
            return f"❌ 加载失败: {info_result.get('error')}", ""

        workflow = info_result.get("workflow", {})

        # 提取参数并生成示例
        params_result = comfyui_module.extract_parameters(workflow)

        # 生成模板信息
        info_output = f"✅ 工作流加载成功！\n\n"
        info_output += f"文件名：{info_result.get('workflow_name', '')}\n"
        info_output += f"路径：{info_result.get('workflow_path', '')}\n"
        info_output += f"节点数量：{len(workflow)}\n\n"

        params_found = params_result.get("parameters", [])

        if params_found:
            info_output += f"📝 发现 {len(params_found)} 个参数占位符：\n"
            for param in params_found:
                info_output += f"  - {{{{ {param} }}}}\n"
            info_output += "\n💡 提示：参数示例已自动填充到下方输入框中。"
        else:
            info_output += "📝 未发现参数占位符，此工作流不需要参数替换。"

        # 生成参数示例 JSON
        params_example = params_result.get("example", {})
        if params_example:
            params_json = json.dumps(params_example, indent=2, ensure_ascii=False)
        else:
            params_json = ""

        return info_output, params_json

    except Exception as e:
        Logger.error(f"加载工作流信息失败: {str(e)}")
        return f"❌ 加载失败: {str(e)}", ""


def execute_workflow_from_template(    workflow_name: str,
    params_json: str,
    server_url: str,
    auth_token: str = "",
    username: str = "",
    password: str = "",
    timeout: int = 300,
    progress=gr.Progress()
) -> str:
    """
    从工作流模板执行工作流

    Args:
        workflow_name: 工作流文件名
        params_json: 参数 JSON 字符串
        server_url: ComfyUI 服务器地址
        auth_token: 认证 Token
        username: 用户名
        password: 密码
        timeout: 超时时间（秒），默认 300 秒
        progress: Gradio 进度条

    Returns:
        str: 执行结果
    """
    try:
        import asyncio

        if not workflow_name.strip():
            return "❌ 错误：请选择工作流模板"

        # 解析参数 JSON
        params = {}
        if params_json.strip():
            try:
                params = json.loads(params_json)
            except json.JSONDecodeError as e:
                return f"❌ 错误：参数 JSON 格式无效\n\n{str(e)}"

        progress(0.1, desc="加载工作流模板...")

        async def run_execute():
            result = await comfyui_module.execute_workflow_from_template(
                workflow_name=workflow_name,
                server_url=server_url,
                auth_token=auth_token if auth_token.strip() else None,
                username=username if username.strip() else None,
                password=password if password.strip() else None,
                params=params if params else None,
                timeout=timeout
            )
            return result

        progress(0.3, desc="提交工作流...")
        result = asyncio.run(run_execute())

        progress(1.0, desc="执行完成！")

        if result.get("success"):
            output = f"✅ 工作流执行成功！\n\n"
            output += f"工作流模板：{workflow_name}\n"
            output += f"提示 ID：{result.get('prompt_id')}\n"
            output += f"超时时间：{timeout}秒\n"

            if params:
                output += f"使用的参数：\n{json.dumps(params, indent=2, ensure_ascii=False)}\n\n"

            # 输出图片
            if result.get("output_images"):
                output += f"📸 输出图片（{len(result['output_images'])}张）：\n"
                for i, img_info in enumerate(result['output_images'], 1):
                    output += f"  {i}. 文件名: {img_info.get('filename', '')}\n"
                    output += f"     下载链接: {img_info.get('url', '')}\n"
                output += "\n"

            # 输出音频
            if result.get("output_audio"):
                output += f"🎵 输出音频（{len(result['output_audio'])}个）：\n"
                for i, audio_info in enumerate(result['output_audio'], 1):
                    output += f"  {i}. 文件名: {audio_info.get('filename', '')}\n"
                    output += f"     下载链接: {audio_info.get('url', '')}\n"
                output += "\n"

            # 输出视频
            if result.get("output_videos"):
                output += f"🎬 输出视频（{len(result['output_videos'])}个）：\n"
                for i, video_info in enumerate(result['output_videos'], 1):
                    output += f"  {i}. 文件名: {video_info.get('filename', '')}\n"
                    output += f"     下载链接: {video_info.get('url', '')}\n"
                output += "\n"

            # 输出其他文件
            if result.get("output_files"):
                output += f"📁 输出文件（{len(result['output_files'])}个）：\n"
                for i, file_info in enumerate(result['output_files'], 1):
                    output += f"  {i}. 文件名: {file_info.get('filename', '')}\n"
                    output += f"     下载链接: {file_info.get('url', '')}\n"
                output += "\n"

            output += f"消息：{result.get('message', '')}"
            return output
        else:
            return f"❌ 工作流执行失败\n\n错误：{result.get('error')}"
    except Exception as e:
        Logger.error(f"执行工作流失败: {str(e)}")
        return f"❌ 执行工作流时发生异常\n\n详细信息：{str(e)}"


def test_comfyui_connection(
    server_url: str,
    auth_token: str = "",
    username: str = "",
    password: str = ""
) -> str:
    """
    测试 ComfyUI 连接

    Args:
        server_url: ComfyUI 服务器地址
        auth_token: 认证 Token
        username: 用户名
        password: 密码

    Returns:
        str: 测试结果
    """
    try:
        import asyncio

        async def run_test():
            result = await comfyui_module.test_connection(
                server_url=server_url,
                auth_token=auth_token if auth_token.strip() else None,
                username=username if username.strip() else None,
                password=password if password.strip() else None
            )
            return result

        result = asyncio.run(run_test())

        if result.get("success"):
            output = f"✅ 连接成功！\n\n"
            output += f"服务器地址：{result['server_url']}\n"
            output += f"服务器信息：\n{json.dumps(result.get('server_info', {}), indent=2, ensure_ascii=False)}"
            return output
        else:
            return f"❌ 连接失败\n\n错误：{result.get('error')}"
    except Exception as e:
        Logger.error(f"测试连接失败: {str(e)}")
        return f"❌ 测试连接时发生异常\n\n详细信息：{str(e)}"


def get_comfyui_nodes(
    server_url: str,
    auth_token: str = "",
    username: str = "",
    password: str = ""
) -> str:
    """
    获取 ComfyUI 可用节点

    Args:
        server_url: ComfyUI 服务器地址
        auth_token: 认证 Token
        username: 用户名
        password: 密码

    Returns:
        str: 节点列表
    """
    try:
        import asyncio

        async def run_get():
            result = await comfyui_module.get_available_nodes(
                server_url=server_url,
                auth_token=auth_token if auth_token.strip() else None,
                username=username if username.strip() else None,
                password=password if password.strip() else None
            )
            return result

        result = asyncio.run(run_get())

        if result.get("success"):
            nodes = result.get("nodes", {})
            output = f"✅ 获取成功！\n\n"
            output += f"节点数量：{result.get('count', 0)}\n\n"
            output += "节点列表：\n"
            output += "-" * 80 + "\n"

            for node_name, node_info in nodes.items():
                output += f"\n📦 {node_name}\n"
                if 'display_name' in node_info:
                    output += f"   显示名称：{node_info['display_name']}\n"
                if 'description' in node_info:
                    output += f"   描述：{node_info['description']}\n"
                if 'category' in node_info:
                    output += f"   分类：{node_info['category']}\n"

            return output
        else:
            return f"❌ 获取失败\n\n错误：{result.get('error')}"
    except Exception as e:
        Logger.error(f"获取节点失败: {str(e)}")
        return f"❌ 获取节点时发生异常\n\n详细信息：{str(e)}"


def execute_comfyui_workflow(
    workflow_json: str,
    server_url: str,
    auth_token: str = "",
    username: str = "",
    password: str = "",
    timeout: int = 300,
    progress=gr.Progress()
) -> str:
    """
    执行 ComfyUI 工作流

    Args:
        workflow_json: 工作流 JSON 字符串
        server_url: ComfyUI 服务器地址
        auth_token: 认证 Token
        username: 用户名
        password: 密码
        timeout: 超时时间（秒），默认 300 秒
        progress: Gradio 进度条

    Returns:
        str: 执行结果
    """
    try:
        import asyncio

        if not workflow_json.strip():
            return "❌ 错误：工作流 JSON 不能为空"

        # 验证 JSON 格式
        try:
            workflow = json.loads(workflow_json)
        except json.JSONDecodeError as e:
            return f"❌ 错误：工作流 JSON 格式无效\n\n{str(e)}"

        progress(0.1, desc="连接 ComfyUI 服务器...")

        async def run_execute():
            result = await comfyui_module.execute_workflow_from_json(
                workflow_json=workflow_json,
                server_url=server_url,
                auth_token=auth_token if auth_token.strip() else None,
                username=username if username.strip() else None,
                password=password if password.strip() else None,
                timeout=timeout
            )
            return result

        progress(0.3, desc="提交工作流...")
        result = asyncio.run(run_execute())

        progress(1.0, desc="执行完成！")

        if result.get("success"):
            output = f"✅ 工作流执行成功！\n\n"
            output += f"提示 ID：{result.get('prompt_id')}\n"
            output += f"超时时间：{timeout}秒\n\n"

            # 输出图片
            if result.get("output_images"):
                output += f"📸 输出图片（{len(result['output_images'])}张）：\n"
                for i, img_info in enumerate(result['output_images'], 1):
                    output += f"  {i}. 文件名: {img_info.get('filename', '')}\n"
                    output += f"     下载链接: {img_info.get('url', '')}\n"
                output += "\n"

            # 输出音频
            if result.get("output_audio"):
                output += f"🎵 输出音频（{len(result['output_audio'])}个）：\n"
                for i, audio_info in enumerate(result['output_audio'], 1):
                    output += f"  {i}. 文件名: {audio_info.get('filename', '')}\n"
                    output += f"     下载链接: {audio_info.get('url', '')}\n"
                output += "\n"

            # 输出视频
            if result.get("output_videos"):
                output += f"🎬 输出视频（{len(result['output_videos'])}个）：\n"
                for i, video_info in enumerate(result['output_videos'], 1):
                    output += f"  {i}. 文件名: {video_info.get('filename', '')}\n"
                    output += f"     下载链接: {video_info.get('url', '')}\n"
                output += "\n"

            # 输出其他文件
            if result.get("output_files"):
                output += f"📁 输出文件（{len(result['output_files'])}个）：\n"
                for i, file_info in enumerate(result['output_files'], 1):
                    output += f"  {i}. 文件名: {file_info.get('filename', '')}\n"
                    output += f"     下载链接: {file_info.get('url', '')}\n"
                output += "\n"

            output += f"消息：{result.get('message', '')}"
            return output
        else:
            return f"❌ 工作流执行失败\n\n错误：{result.get('error')}"
    except Exception as e:
        Logger.error(f"执行工作流失败: {str(e)}")
        return f"❌ 执行工作流时发生异常\n\n详细信息：{str(e)}"


def upload_file_to_comfyui(
    file_path: str,
    filename: str,
    server_url: str,
    auth_token: str = "",
    username: str = "",
    password: str = ""
) -> str:
    """
    上传文件到 ComfyUI 服务器

    Args:
        file_path: 本地文件路径
        filename: 上传后的文件名
        server_url: ComfyUI 服务器地址
        auth_token: 认证 Token
        username: 用户名
        password: 密码

    Returns:
        str: 上传结果
    """
    try:
        import asyncio
        import os

        if not file_path.strip():
            return "❌ 错误：文件路径不能为空"

        if not os.path.exists(file_path):
            return f"❌ 错误：文件不存在: {file_path}"

        # 如果没有指定文件名，使用原文件名
        if not filename.strip():
            filename = os.path.basename(file_path)

        async def run_upload():
            result = await comfyui_module.upload_file(
                filename=filename,
                filepath=file_path,
                server_url=server_url,
                auth_token=auth_token if auth_token.strip() else None,
                username=username if username.strip() else None,
                password=password if password.strip() else None
            )
            return result

        result = asyncio.run(run_upload())

        if result.get("success"):
            output = f"✅ 文件上传成功！\n\n"
            output += f"文件名：{result.get('filename', '')}\n"
            output += f"本地路径：{result.get('filepath', '')}\n"
            output += f"消息：{result.get('message', '')}"
            return output
        else:
            return f"❌ 文件上传失败\n\n错误：{result.get('error')}"
    except Exception as e:
        Logger.error(f"上传文件失败: {str(e)}")
        return f"❌ 上传文件时发生异常\n\n详细信息：{str(e)}"


def create_comfyui_interface() -> gr.Blocks:
    """
    创建 ComfyUI 集成界面

    Returns:
        gr.Blocks: Gradio 界面块
    """
    with gr.Blocks() as comfyui_interface:
        gr.Markdown("## 🎨 ComfyUI 集成")
        gr.Markdown("连接 ComfyUI 服务器并执行工作流生成多种媒体文件")

        # 服务器配置
        with gr.Row():
            server_url_input = gr.Textbox(
                label="ComfyUI 服务器地址",
                value="http://127.0.0.1:8188",
                placeholder="例如: http://127.0.0.1:8188",
                info="ComfyUI 服务器的地址"
            )

        # 鉴权配置
        with gr.Accordion("🔐 鉴权配置（可选）", open=False):
            with gr.Row():
                auth_token_input = gr.Textbox(
                    label="认证 Token",
                    placeholder="Bearer Token",
                    info="使用 Token 认证（优先级高于用户名密码）"
                )
            with gr.Row():
                username_input = gr.Textbox(
                    label="用户名",
                    placeholder="用户名",
                    info="基本认证用户名"
                )
                password_input = gr.Textbox(
                    label="密码",
                    placeholder="密码",
                    type="password",
                    info="基本认证密码"
                )

        # 功能选项卡
        with gr.Tabs():
            # 连接测试选项卡
            with gr.TabItem("🔗 连接测试"):
                with gr.Row():
                    test_conn_btn = gr.Button(
                        "🧪 测试连接",
                        variant="primary"
                    )

                test_conn_output = gr.Code(
                    label="测试结果",
                    lines=15,
                    interactive=False,
                    value='点击"测试连接"按钮查看结果...'
                )

            # 节点列表选项卡
            with gr.TabItem("📦 节点列表"):
                with gr.Row():
                    get_nodes_btn = gr.Button(
                        "📋 获取节点列表",
                        variant="primary"
                    )

                nodes_output = gr.Code(
                    label="节点列表",
                    lines=20,
                    interactive=False,
                    value='点击"获取节点列表"按钮查看可用节点...'
                )

            # 工作流模板选项卡
            with gr.TabItem("📋 工作流模板"):
                # 工作流选择和刷新
                with gr.Row():
                    workflow_name_dropdown = gr.Dropdown(
                        label="选择模板",
                        choices=[],
                        scale=4,
                        info="选择工作流模板"
                    )
                    refresh_workflows_btn = gr.Button(
                        "🔄",
                        variant="secondary",
                        size="sm",
                        scale=0,
                        min_width=60
                    )
                    upload_template_btn = gr.Button(
                        "📤",
                        variant="secondary",
                        size="sm",
                        scale=0,
                        min_width=60
                    )

                # 上传模板区域（默认折叠）
                with gr.Accordion("📤 上传新模板", open=False):
                    with gr.Row():
                        upload_workflow_name_input = gr.Textbox(
                            label="文件名",
                            placeholder="my_workflow.json",
                            scale=3
                        )
                        upload_overwrite_checkbox = gr.Checkbox(
                            label="覆盖",
                            value=False,
                            scale=1
                        )

                    upload_workflow_json_textarea = gr.Code(
                        label="工作流 JSON",
                        language="json",
                        value='{\n  "1": {\n    "inputs": {\n      "text": "{{prompt}}"\n    }\n  }\n}',
                        lines=6
                    )

                    with gr.Row():
                        do_upload_btn = gr.Button(
                            "上传",
                            variant="primary",
                            size="sm",
                            scale=1
                        )

                    upload_result_output = gr.Textbox(
                        label="上传结果",
                        lines=3,
                        interactive=False,
                        placeholder="上传结果..."
                    )

                # 模板信息和参数配置（并排显示）
                with gr.Row():
                    with gr.Column(scale=1):
                        with gr.Accordion("📋 模板信息", open=False):
                            template_info_output = gr.Code(
                                label="详情",
                                lines=4,
                                interactive=False,
                                value='选择模板后显示...'
                            )

                    with gr.Column(scale=1):
                        with gr.Accordion("⚙️ 参数配置", open=True):
                            params_json_textarea = gr.Code(
                                label="参数 JSON",
                                language="json",
                                lines=4,
                                value='自动填充参数示例...'
                            )

                # 执行配置和按钮
                with gr.Row():
                    template_timeout_input = gr.Number(
                        label="超时(秒)",
                        value=300,
                        minimum=10,
                        maximum=3600,
                        step=10,
                        scale=1
                    )
                    execute_template_btn = gr.Button(
                        "🚀 执行",
                        variant="primary",
                        size="sm",
                        scale=1
                    )

                # 执行结果
                with gr.Accordion("📊 执行结果", open=False):
                    template_output = gr.Code(
                        label="结果",
                        lines=8,
                        interactive=False,
                        value="执行结果将显示在这里..."
                    )

            # 工作流执行选项卡
            with gr.TabItem("⚙️ 工作流执行"):
                gr.Markdown("### 工作流配置")
                gr.Markdown("在下方输入 ComfyUI 工作流 JSON（可以从 ComfyUI 界面导出）")

                workflow_json_textarea = gr.Code(
                    label="工作流 JSON",
                    language="json",
                    value='{\n  "1": {\n    "inputs": {\n      "text": "a beautiful landscape",\n      "seed": 123456\n    },\n    "class_type": "KSampler"\n  }\n}',
                    lines=15
                )

                timeout_input = gr.Number(
                    label="超时时间（秒）",
                    value=300,
                    minimum=10,
                    maximum=3600,
                    step=10,
                    info="工作流执行超时时间，默认 300 秒（5分钟）"
                )

                execute_workflow_btn = gr.Button(
                    "🚀 执行工作流",
                    variant="primary",
                    size="lg"
                )

                workflow_output = gr.Code(
                    label="执行结果",
                    lines=20,
                    interactive=False,
                    value="工作流执行结果将显示在这里..."
                )

            # 文件上传选项卡
            with gr.TabItem("📤 文件上传"):
                gr.Markdown("### 上传文件到 ComfyUI")
                gr.Markdown("支持上传图片、音频、视频等多种格式的文件到 ComfyUI 服务器")

                with gr.Row():
                    file_path_input = gr.Textbox(
                        label="本地文件路径",
                        placeholder="例如: D:/images/test.png",
                        info="要上传的本地文件路径"
                    )
                    filename_input = gr.Textbox(
                        label="上传后的文件名（可选）",
                        placeholder="留空则使用原文件名",
                        info="上传到 ComfyUI 后的文件名"
                    )

                upload_file_btn = gr.Button(
                    "📤 上传文件",
                    variant="primary"
                )

                upload_file_output = gr.Code(
                    label="上传结果",
                    lines=10,
                    interactive=False,
                    value="文件上传结果将显示在这里..."
                )

        # 使用说明
        with gr.Accordion("📖 使用说明", open=False):
            gr.Markdown("""
#### 1. 启动 ComfyUI 服务器
首先需要在本地启动 ComfyUI 服务器：
```bash
# 进入 ComfyUI 目录
cd ComfyUI

# 启动服务器
python main.py --listen 0.0.0.0 --port 8188
```

#### 2. 配置服务器地址
在"ComfyUI 服务器地址"输入框中填写服务器地址：
- 本地服务器：`http://127.0.0.1:8188`
- 远程服务器：`http://your-server-ip:8188`

#### 3. 配置鉴权（可选）
如果 ComfyUI 服务器启用了鉴权，可以配置以下参数：
- **认证 Token**：使用 Bearer Token 认证（优先级最高）
- **用户名/密码**：使用基本认证

#### 4. 测试连接
点击"测试连接"按钮，验证是否能成功连接到 ComfyUI 服务器。

#### 5. 获取节点列表
点击"获取节点列表"按钮，查看 ComfyUI 中可用的所有节点。

#### 6. 执行工作流
1. 在 ComfyUI 界面中设计工作流
2. 点击"Save (API Format)"导出工作流 JSON
3. 将 JSON 粘贴到"工作流 JSON"输入框
4. 设置超时时间（默认 300 秒）
5. 点击"执行工作流"按钮
6. 查看执行结果和输出文件

#### 7. 上传文件
1. 在"本地文件路径"输入框中填写要上传的文件路径
2. 可选：在"上传后的文件名"中指定上传后的文件名
3. 点击"上传文件"按钮
4. 查看上传结果

支持上传的文件类型：
- 📸 图片：.png, .jpg, .jpeg, .gif, .bmp, .webp
- 🎵 音频：.mp3, .wav, .ogg, .flac, .m4a, .aac
- 🎬 视频：.mp4, .avi, .mov, .mkv, .webm

#### 工作流 JSON 格式说明

工作流 JSON 应该包含节点定义和连接关系，格式如下：
```json
{
  "1": {
    "inputs": {
      "ckpt_name": "v1-5-pruned-emaonly.ckpt"
    },
    "class_type": "CheckpointLoaderSimple"
  },
  "2": {
    "inputs": {
      "text": "a beautiful landscape",
      "clip": ["1", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "3": {
    "inputs": {
      "seed": 123456,
      "steps": 20,
      "cfg": 7,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1,
      "model": ["1", 0],
      "positive": ["2", 0],
      "negative": ["2", 0]
    },
    "class_type": "KSampler"
  }
}
```

#### 注意事项
- 确保 ComfyUI 服务器已启动并可访问
- 工作流 JSON 必须使用 API 格式（Save (API Format)）
- 支持生成图片、音频、视频等多种媒体文件
- 执行大工作流可能需要较长时间，请根据实际情况调整超时时间
- 输出文件会显示在执行结果中，可以复制链接下载

#### 常见问题

**Q: 连接失败怎么办？**
A: 检查 ComfyUI 服务器是否已启动，确认服务器地址和端口是否正确。如果启用了鉴权，请检查鉴权配置。

**Q: 如何获取工作流 JSON？**
A: 在 ComfyUI 界面中，点击菜单栏的"Save (API Format)"即可导出。

**Q: 执行超时怎么办？**
A: 检查工作流是否过于复杂，或者增加超时时间配置（最大支持 3600 秒/1 小时）。

**Q: 支持哪些文件类型？**
A: 支持图片（.png, .jpg, .jpeg, .gif, .bmp, .webp）、音频（.mp3, .wav, .ogg, .flac, .m4a, .aac）、视频（.mp4, .avi, .mov, .mkv, .webm）等多种格式。
            """)

        # 绑定事件
        test_conn_btn.click(
            fn=test_comfyui_connection,
            inputs=[
                server_url_input,
                auth_token_input,
                username_input,
                password_input
            ],
            outputs=test_conn_output
        )

        get_nodes_btn.click(
            fn=get_comfyui_nodes,
            inputs=[
                server_url_input,
                auth_token_input,
                username_input,
                password_input
            ],
            outputs=nodes_output
        )

        # 工作流模板事件绑定
        def update_workflow_dropdown():
            """更新工作流下拉列表"""
            result = comfyui_module.list_workflows()
            if result.get("success"):
                return gr.Dropdown(
                    choices=[wf['filename'] for wf in result['workflows']],
                    value=None
                )
            else:
                return gr.Dropdown(choices=[], value=None)

        # 刷新后更新下拉列表
        def refresh_and_update():
            """刷新工作流列表并更新下拉框"""
            result = comfyui_module.list_workflows()
            if result.get("success"):
                choices = [wf['filename'] for wf in result['workflows']]
            else:
                choices = []
            return gr.Dropdown(choices=choices, value=None)

        refresh_workflows_btn.click(
            fn=refresh_and_update,
            inputs=[],
            outputs=[workflow_name_dropdown]
        )

        # 选择工作流时自动加载信息和参数示例
        workflow_name_dropdown.change(
            fn=on_workflow_select,
            inputs=[workflow_name_dropdown],
            outputs=[template_info_output, params_json_textarea]
        )

        # 上传工作流模板
        do_upload_btn.click(
            fn=upload_workflow_template,
            inputs=[
                upload_workflow_name_input,
                upload_workflow_json_textarea,
                upload_overwrite_checkbox
            ],
            outputs=[upload_result_output]
        )

        # 上传成功后刷新列表
        def upload_and_refresh(workflow_name, workflow_json, overwrite):
            """上传并刷新列表"""
            upload_result = upload_workflow_template(workflow_name, workflow_json, overwrite)
            dropdown_result = refresh_and_update()
            return upload_result, dropdown_result

        do_upload_btn.click(
            fn=upload_and_refresh,
            inputs=[
                upload_workflow_name_input,
                upload_workflow_json_textarea,
                upload_overwrite_checkbox
            ],
            outputs=[upload_result_output, workflow_name_dropdown]
        )

        execute_template_btn.click(
            fn=execute_workflow_from_template,
            inputs=[
                workflow_name_dropdown,
                params_json_textarea,
                server_url_input,
                auth_token_input,
                username_input,
                password_input,
                template_timeout_input
            ],
            outputs=template_output
        )

        # 初始化时加载工作流列表
        comfyui_interface.load(
            fn=refresh_and_update,
            inputs=[],
            outputs=[workflow_name_dropdown]
        )

        execute_workflow_btn.click(
            fn=execute_comfyui_workflow,
            inputs=[
                workflow_json_textarea,
                server_url_input,
                auth_token_input,
                username_input,
                password_input,
                timeout_input
            ],
            outputs=workflow_output
        )

        upload_file_btn.click(
            fn=upload_file_to_comfyui,
            inputs=[
                file_path_input,
                filename_input,
                server_url_input,
                auth_token_input,
                username_input,
                password_input
            ],
            outputs=upload_file_output
        )

    return comfyui_interface