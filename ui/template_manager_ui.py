"""
模板管理 UI 模块

提供模板文件的管理功能，包括新增、查看、编辑和删除模板，以及上传模板资源文件。
"""

import gradio as gr
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from utils.logger import Logger
from modules.template_manager import template_manager


def get_template_manager_ui() -> gr.Blocks:
    """
    创建模板管理界面

    Returns:
        gr.Blocks: Gradio 界面组件
    """

    # 获取模板列表
    def get_template_list() -> List[Dict[str, Any]]:
        """获取所有模板列表"""
        try:
            templates = template_manager.get_all_templates()
            return templates
        except Exception as e:
            Logger.error(f"获取模板列表失败: {e}")
            return []

    # 获取模板详情
    def get_template_detail(template_name: str) -> Dict[str, Any]:
        """获取指定模板的详细信息"""
        if not template_name:
            return {}
        try:
            template = template_manager.get_template(template_name)
            if template:
                return template
            return {}
        except Exception as e:
            Logger.error(f"获取模板详情失败: {e}")
            return {}

    # 保存模板
    def save_template(
        template_name: str,
        template_json: str,
        is_new: bool = False
    ) -> str:
        """保存模板"""
        try:
            # 验证JSON格式
            template_data = json.loads(template_json)

            # 验证必需字段
            required_fields = ["name", "description", "version", "tasks"]
            for field in required_fields:
                if field not in template_data:
                    return f"错误: 缺少必需字段 '{field}'"

            # 保存模板
            if is_new:
                # 检查模板是否已存在
                if template_manager.get_template(template_name):
                    return f"错误: 模板 '{template_name}' 已存在"
                # 保存新模板
                template_manager.save_template(template_name, template_data)
                return f"✅ 模板 '{template_name}' 创建成功"
            else:
                # 更新现有模板
                template_manager.save_template(template_name, template_data)
                return f"✅ 模板 '{template_name}' 更新成功"

        except json.JSONDecodeError as e:
            return f"错误: JSON 格式无效 - {str(e)}"
        except Exception as e:
            Logger.error(f"保存模板失败: {e}")
            return f"错误: {str(e)}"

    # 删除模板
    def delete_template(template_name: str) -> str:
        """删除模板"""
        if not template_name:
            return "错误: 请选择要删除的模板"
        try:
            template_manager.delete_template(template_name)
            return f"✅ 模板 '{template_name}' 删除成功"
        except Exception as e:
            Logger.error(f"删除模板失败: {e}")
            return f"错误: {str(e)}"

    # 上传模板资源文件
    def upload_template_resource(
        template_name: str,
        file: Optional[str] = None
    ) -> str:
        """上传模板资源文件"""
        if not template_name:
            return "错误: 请先选择模板"
        if not file:
            return "错误: 请选择要上传的文件"

        try:
            # 获取模板目录
            template = template_manager.get_template(template_name)
            if not template:
                return f"错误: 模板 '{template_name}' 不存在"

            template_dir = Path(template.get("template_dir", ""))
            if not template_dir.exists():
                template_dir.mkdir(parents=True, exist_ok=True)

            # 复制文件到模板目录
            file_path = Path(file)
            dest_path = template_dir / file_path.name

            import shutil
            shutil.copy2(file_path, dest_path)

            return f"✅ 文件 '{file_path.name}' 上传成功到模板目录"
        except Exception as e:
            Logger.error(f"上传模板资源文件失败: {e}")
            return f"错误: {str(e)}"

    # 获取模板资源文件列表
    def get_template_resources(template_name: str) -> List[str]:
        """获取模板资源文件列表"""
        if not template_name:
            return []
        try:
            template = template_manager.get_template(template_name)
            if not template:
                return []

            template_dir = Path(template.get("template_dir", ""))
            if not template_dir.exists():
                return []

            # 获取所有文件
            resources = []
            for file in template_dir.iterdir():
                if file.is_file():
                    resources.append(file.name)

            return resources
        except Exception as e:
            Logger.error(f"获取模板资源文件列表失败: {e}")
            return []

    # 格式化JSON
    def format_json(json_str: str) -> str:
        """格式化JSON字符串"""
        try:
            data = json.loads(json_str)
            return json.dumps(data, indent=2, ensure_ascii=False)
        except:
            return json_str

    # 创建界面
    with gr.Blocks(
        title="模板管理"
    ) as template_manager_ui:
        # 添加自定义 CSS 样式
        gr.HTML("""
        <style>
        .template-list {
            max-height: 400px;
            overflow-y: auto;
        }
        .json-editor {
            font-family: 'Courier New', monospace;
            font-size: 14px;
        }
        .resource-list {
            max-height: 200px;
            overflow-y: auto;
        }
        </style>
        """)

        gr.Markdown("## 📁 模板管理")
        gr.Markdown("管理综合处理模板文件，包括新增、编辑、删除模板以及上传模板资源文件。")

        with gr.Row():
            with gr.Column(scale=1):
                # 左侧：模板列表和资源文件管理
                # 模板列表
                with gr.Row():
                    gr.Markdown("### 📋 模板列表")
                    refresh_btn = gr.Button("🔄", size="sm", variant="secondary", scale=0, min_width=40)

                template_dropdown = gr.Dropdown(
                    label="选择模板",
                    choices=[],
                    interactive=True,
                    scale=1
                )
                template_info = gr.JSON(label="模板信息", visible=False)

                # 模板资源文件管理
                gr.Markdown("### 📁 模板资源文件")
                template_name_input = gr.Textbox(
                    label="模板名称",
                    placeholder="选择模板后自动填充...",
                    interactive=True
                )
                resource_upload = gr.File(
                    label="上传资源文件",
                    file_types=[".png", ".jpg", ".jpeg", ".mp4", ".avi", ".mov", ".mp3", ".wav", ".json"],
                    type="filepath"
                )
                with gr.Row():
                    upload_btn = gr.Button("📤 上传", variant="primary", size="sm")
                    refresh_resources_btn = gr.Button("🔄 刷新", size="sm")
                upload_result = gr.Textbox(label="上传结果", interactive=False, lines=2)

                # 资源文件列表
                gr.Markdown("### 📄 资源文件")
                resource_list = gr.Textbox(
                    label="资源文件列表",
                    placeholder="选择模板后自动显示...",
                    lines=8,
                    interactive=False,
                    elem_classes=["resource-list"]
                )

            with gr.Column(scale=2):
                # 右侧：模板编辑器
                gr.Markdown("### ✏️ 模板编辑器")
                template_editor = gr.TextArea(
                    label="模板 JSON",
                    placeholder="在此处编辑模板 JSON 内容...",
                    lines=25,
                    max_lines=35,
                    elem_classes=["json-editor"]
                )
                with gr.Row():
                    new_btn = gr.Button("➕ 新建", variant="primary", size="sm")
                    save_btn = gr.Button("💾 保存", variant="secondary", size="sm")
                    delete_btn = gr.Button("🗑️ 删除", variant="stop", size="sm")
                    format_btn = gr.Button("🎨 格式化", size="sm")
                operation_result = gr.Textbox(label="操作结果", interactive=False, lines=2)

        # 事件处理
        def refresh_template_list():
            """刷新模板列表"""
            templates = get_template_list()
            choices = [t["name"] for t in templates]
            return gr.Dropdown(choices=choices, value=None)

        def on_template_change(template_name: str):
            """模板选择变化时更新编辑器和信息"""
            if not template_name:
                return "", "", {}, []

            template = get_template_detail(template_name)
            if template:
                json_str = json.dumps(template, indent=2, ensure_ascii=False)
                resources = get_template_resources(template_name)
                return json_str, template_name, template, resources
            return "", "", {}, []

        def on_new_template():
            """新建模板"""
            new_template = {
                "name": "新模板",
                "description": "模板描述",
                "version": "1.0",
                "character": "",
                "theme": "",
                "parameters": {},
                "tasks": []
            }
            json_str = json.dumps(new_template, indent=2, ensure_ascii=False)
            return json_str, ""

        def on_save_template(template_name: str, template_json: str):
            """保存模板"""
            if not template_name:
                return "错误: 请输入模板名称"
            return save_template(template_name, template_json, is_new=True)

        def on_update_template(template_name: str, template_json: str):
            """更新模板"""
            if not template_name:
                return "错误: 请选择模板"
            return save_template(template_name, template_json, is_new=False)

        def on_delete_template(template_name: str):
            """删除模板"""
            result = delete_template(template_name)
            # 刷新模板列表
            templates = get_template_list()
            choices = [t["name"] for t in templates]
            return result, gr.Dropdown(choices=choices, value=None), "", "", {}

        def on_upload_resource(template_name: str, file: Optional[str]):
            """上传资源文件"""
            if not template_name:
                return "错误: 请输入模板名称"
            if not file:
                return "错误: 请选择文件"
            result = upload_template_resource(template_name, file)
            # 刷新资源列表
            resources = get_template_resources(template_name)
            return result, "\n".join(resources) if resources else ""

        def on_refresh_resources(template_name: str):
            """刷新资源文件列表"""
            if not template_name:
                return ""
            resources = get_template_resources(template_name)
            return "\n".join(resources) if resources else ""

        # 绑定事件
        refresh_btn.click(
            refresh_template_list,
            outputs=[template_dropdown]
        )

        template_dropdown.change(
            on_template_change,
            inputs=[template_dropdown],
            outputs=[template_editor, template_name_input, template_info, resource_list]
        )

        new_btn.click(
            on_new_template,
            outputs=[template_editor, template_name_input]
        )

        save_btn.click(
            on_save_template,
            inputs=[template_name_input, template_editor],
            outputs=[operation_result]
        )

        # 双击保存按钮更新现有模板
        save_btn.click(
            on_update_template,
            inputs=[template_dropdown, template_editor],
            outputs=[operation_result]
        )

        delete_btn.click(
            on_delete_template,
            inputs=[template_dropdown],
            outputs=[operation_result, template_dropdown, template_editor, template_name_input, template_info]
        )

        format_btn.click(
            format_json,
            inputs=[template_editor],
            outputs=[template_editor]
        )

        upload_btn.click(
            on_upload_resource,
            inputs=[template_name_input, resource_upload],
            outputs=[upload_result, resource_list]
        )

        refresh_resources_btn.click(
            on_refresh_resources,
            inputs=[template_name_input],
            outputs=[resource_list]
        )

        # 初始化
        template_manager_ui.load(
            refresh_template_list,
            outputs=[template_dropdown]
        )

    return template_manager_ui