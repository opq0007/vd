"""
邮件发送界面

提供便捷的邮件发送功能界面。
"""

import gradio as gr
from modules.email_module import email_module
from utils import Logger


def create_email_interface():
    """
    创建邮件发送界面

    Returns:
        Gradio界面组件
    """

    def test_smtp_connection():
        """测试SMTP连接"""
        try:
            success, message = email_module.test_connection()
            if success:
                status_msg = "✅ " + message
                status_class = "success"
            else:
                status_msg = "❌ " + message
                status_class = "error"
            return status_msg, status_class
        except Exception as e:
            Logger.error(f"测试SMTP连接失败: {str(e)}")
            return "❌ 连接测试失败: " + str(e), "error"

    def send_email(to_address, subject, content, content_type, attachment_mode, attachment_files, attachment_paths):
        """
        发送邮件

        Args:
            to_address: 收件人邮箱
            subject: 邮件主题
            content: 邮件内容
            content_type: 内容类型
            attachment_mode: 附件模式（upload/path）
            attachment_files: 上传的附件文件列表
            attachment_paths: 附件路径列表（多行文本）

        Returns:
            tuple: (状态消息, 状态类)
        """
        try:
            # 处理附件
            attachments = None
            if attachment_mode == "upload":
                # 上传模式：处理上传的文件
                attachment_path_list = []
                if attachment_files:
                    if isinstance(attachment_files, list):
                        attachment_path_list = [f.name for f in attachment_files if f]
                    elif attachment_files:
                        attachment_path_list = [attachment_files.name]
                attachments = {"mode": "upload", "files": attachment_path_list}
            elif attachment_mode == "path":
                # 路径模式：解析路径列表
                attachment_path_list = []
                if attachment_paths:
                    lines = attachment_paths.strip().split('\n')
                    for line in lines:
                        line = line.strip()
                        if line:
                            attachment_path_list.append(line)
                attachments = {"mode": "path", "files": attachment_path_list}

            Logger.info(f"准备发送邮件到: {to_address}, 附件模式: {attachment_mode}")
            
            # 发送邮件
            success, message = email_module.send_email(
                to_address=to_address,
                subject=subject,
                content=content,
                content_type=content_type,
                attachments=attachments
            )

            if success:
                status_msg = "✅ " + message
                status_class = "success"
                Logger.info(f"邮件发送成功: {message}")
            else:
                status_msg = "❌ " + message
                status_class = "error"
                Logger.error(f"邮件发送失败: {message}")

            return status_msg, status_class

        except Exception as e:
            error_msg = f"❌ 发生异常: {str(e)}"
            Logger.error(f"发送邮件时发生异常: {str(e)}")
            return error_msg, "error"

    with gr.Column():
        gr.Markdown("## 📧 邮件发送")
        gr.Markdown("使用 SMTP 协议发送邮件，支持添加附件。")

        with gr.Row():
            # 左侧：发送配置
            with gr.Column(scale=1):
                gr.Markdown("### 📮 发送配置")

                with gr.Accordion("SMTP 连接测试", open=True):
                    gr.Markdown("**提示**: 请先测试SMTP连接，确保配置正确后再发送邮件。")
                    test_btn = gr.Button("🔍 测试SMTP连接", variant="secondary")
                    test_result = gr.Textbox(
                        label="测试结果",
                        interactive=False,
                        lines=2
                    )

            # 右侧：邮件信息
            with gr.Column(scale=2):
                gr.Markdown("### ✉️ 邮件信息")

                with gr.Row():
                    to_address = gr.Textbox(
                        label="收件人邮箱",
                        placeholder="example@example.com"
                    )
                    subject = gr.Textbox(
                        label="邮件主题",
                        placeholder="请输入邮件主题"
                    )

                content_type = gr.Radio(
                    label="内容类型",
                    choices=["plain", "html"],
                    value="plain",
                    info="plain: 纯文本 | html: HTML格式"
                )

                content = gr.Textbox(
                    label="邮件内容",
                    placeholder="请输入邮件内容...",
                    lines=8
                )

                with gr.Row():
                    attachment_mode = gr.Radio(
                        label="附件模式",
                        choices=["upload", "path"],
                        value="upload",
                        info="upload: 上传文件 | path: 指定文件路径"
                    )

                # 附件文件上传（upload模式）
                with gr.Group(visible=True) as upload_group:
                    gr.Markdown(
                        "⚠️ **附件大小限制**: 腾讯邮箱限制单个邮件附件总大小不超过 **50MB**。"
                        "\n\n如果附件超过50MB，请：\n"
                        "1. 压缩文件后重试\n"
                        "2. 将文件上传到云盘，在邮件中提供下载链接\n"
                        "3. 使用超大附件功能"
                    )
                    attachment_files = gr.File(
                        label="附件（可多选）",
                        file_count="multiple",
                        file_types=[".*"]
                    )

                # 附件路径输入（path模式）
                with gr.Group(visible=False) as path_group:
                    gr.Markdown(
                        "⚠️ **附件大小限制**: 腾讯邮箱限制单个邮件附件总大小不超过 **50MB**。"
                        "\n\n如果附件超过50MB，请：\n"
                        "1. 压缩文件后重试\n"
                        "2. 将文件上传到云盘，在邮件中提供下载链接\n"
                        "3. 使用超大附件功能"
                    )
                    attachment_paths = gr.Textbox(
                        label="附件路径列表",
                        placeholder="每行输入一个文件路径\n例如:\nD:\\path\\to\\file1.mp4\nD:\\path\\to\\file2.pdf",
                        lines=5
                    )

        # 发送按钮和结果
        with gr.Row():
            send_btn = gr.Button("📤 发送邮件", variant="primary", size="lg")

        result_status = gr.Textbox(
            label="发送状态",
            interactive=False,
            lines=3
        )

        # 绑定事件
        test_btn.click(
            fn=test_smtp_connection,
            outputs=[test_result]
        )

        # 附件模式切换事件
        def update_attachment_visibility(mode):
            return gr.Group(visible=(mode == "upload")), gr.Group(visible=(mode == "path"))

        attachment_mode.change(
            fn=update_attachment_visibility,
            inputs=[attachment_mode],
            outputs=[upload_group, path_group]
        )

        send_btn.click(
            fn=send_email,
            inputs=[to_address, subject, content, content_type, attachment_mode, attachment_files, attachment_paths],
            outputs=[result_status]
        )

    return test_btn, send_btn