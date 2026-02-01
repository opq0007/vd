"""
邮件发送模块

提供邮件发送功能，支持SMTP协议发送邮件，可添加附件。
支持附件大小检查，当附件过大时提供友好的错误提示。
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formataddr
from typing import Optional, List
import logging

from config import config
from utils import Logger


class EmailModule:
    """邮件发送模块类"""

    # 腾讯邮箱附件大小限制（50MB）
    QQ_EMAIL_MAX_ATTACHMENT_SIZE = 50 * 1024 * 1024  # 50MB

    def __init__(self):
        """初始化邮件发送模块"""
        self.smtp_host = config.EMAIL_SMTP_HOST
        self.smtp_port = config.EMAIL_SMTP_PORT
        self.use_tls = config.EMAIL_SMTP_USE_TLS
        self.from_address = config.EMAIL_FROM_ADDRESS
        self.from_password = config.EMAIL_FROM_PASSWORD
        self.from_name = config.EMAIL_FROM_NAME
        self.timeout = config.EMAIL_TIMEOUT
        self.max_attachment_size = self.QQ_EMAIL_MAX_ATTACHMENT_SIZE

    def calculate_total_attachment_size(self, attachment_paths: List[str]) -> int:
        """
        计算附件总大小

        Args:
            attachment_paths: 附件文件路径列表

        Returns:
            int: 附件总大小（字节）
        """
        total_size = 0
        for path in attachment_paths:
            if os.path.exists(path):
                total_size += os.path.getsize(path)
        return total_size

    def format_size(self, size_bytes: int) -> str:
        """
        格式化文件大小显示

        Args:
            size_bytes: 文件大小（字节）

        Returns:
            str: 格式化后的大小字符串
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

    def validate_config(self) -> tuple[bool, str]:
        """
        验证邮件配置是否完整

        Returns:
            tuple: (是否有效, 错误信息)
        """
        if not self.smtp_host:
            return False, "SMTP服务器地址未配置"
        if not self.from_address:
            return False, "发件人邮箱地址未配置"
        if not self.from_password:
            return False, "发件人邮箱密码未配置"
        return True, ""

    def send_email(
        self,
        to_address: str,
        subject: str,
        content: str,
        content_type: str = "html",
        attachments: Optional[List[str] | dict] = None
    ) -> tuple[bool, str]:
        """
        发送邮件

        Args:
            to_address: 收件人邮箱地址
            subject: 邮件主题
            content: 邮件内容
            content_type: 内容类型（plain 或 html）
            attachments: 附件文件路径列表（list类型）或附件模式配置（dict类型）
                        - list类型: ["path1", "path2"] - 纯路径列表
                        - dict类型: {"mode": "upload|path", "files": ["path1", "path2"]}

        Returns:
            tuple: (是否成功, 结果信息或错误信息)
        """
        # 验证配置
        is_valid, error_msg = self.validate_config()
        if not is_valid:
            return False, f"配置错误: {error_msg}"

        # 验证收件人地址
        if not to_address or "@" not in to_address:
            return False, "收件人邮箱地址无效"

        # 处理附件参数
        attachment_paths = []
        if attachments:
            if isinstance(attachments, list):
                # list类型：直接使用路径列表
                attachment_paths = attachments
            elif isinstance(attachments, dict):
                # dict类型：从配置中提取文件路径
                mode = attachments.get("mode", "path")
                files = attachments.get("files", [])
                if mode == "upload" or mode == "path":
                    attachment_paths = files
                else:
                    Logger.warning(f"不支持的附件模式: {mode}")
            else:
                Logger.warning(f"不支持的附件参数类型: {type(attachments)}")

        # 检查附件总大小
        if attachment_paths:
            total_size = self.calculate_total_attachment_size(attachment_paths)
            if total_size > self.max_attachment_size:
                error_msg = (
                    f"附件总大小 {self.format_size(total_size)} 超过限制 "
                    f"({self.format_size(self.max_attachment_size)})。\n\n"
                    f"腾讯邮箱限制：552 Message too large\n"
                    f"改善建议：\n"
                    f"1. 缩减附件大小，删除不必要的文件\n"
                    f"2. 将大文件压缩后再发送\n"
                    f"3. 使用超大附件功能（通过文件分享链接）\n"
                    f"4. 将文件上传到云盘，在邮件中提供下载链接"
                )
                Logger.error(error_msg)
                return False, error_msg

        try:
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = formataddr((self.from_name, self.from_address))
            msg['To'] = to_address
            msg['Subject'] = subject

            # 添加邮件内容
            if content_type == "html":
                msg.attach(MIMEText(content, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(content, 'plain', 'utf-8'))

            # 添加附件
            if attachment_paths:
                for attachment_path in attachment_paths:
                    if not attachment_path:
                        continue
                    if not os.path.exists(attachment_path):
                        Logger.warning(f"附件文件不存在: {attachment_path}")
                        continue

                    try:
                        with open(attachment_path, 'rb') as f:
                            part = MIMEApplication(f.read())
                            part.add_header(
                                'Content-Disposition',
                                'attachment',
                                filename=os.path.basename(attachment_path)
                            )
                            msg.attach(part)
                            Logger.info(f"已添加附件: {attachment_path}")
                    except Exception as e:
                        Logger.error(f"添加附件失败: {attachment_path}, 错误: {str(e)}")
                        return False, f"添加附件失败: {str(e)}"

            # 连接SMTP服务器并发送邮件
            Logger.info(f"正在连接SMTP服务器: {self.smtp_host}:{self.smtp_port}")
            
            # 根据端口选择连接方式
            if self.smtp_port == 465:
                # 使用SSL连接（端口465）
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=self.timeout) as server:
                    Logger.info("已使用SSL加密连接")
                    
                    # 登录
                    server.login(self.from_address, self.from_password)
                    Logger.info(f"已登录邮箱: {self.from_address}")
                    
                    # 发送邮件
                    server.sendmail(self.from_address, to_address, msg.as_string())
                    Logger.info(f"邮件已成功发送到: {to_address}")
            else:
                # 使用STARTTLS连接（端口587）
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout) as server:
                    if self.use_tls:
                        server.starttls()
                        Logger.info("已启用STARTTLS加密")
                    
                    # 登录
                    server.login(self.from_address, self.from_password)
                    Logger.info(f"已登录邮箱: {self.from_address}")
                    
                    # 发送邮件
                    server.sendmail(self.from_address, to_address, msg.as_string())
                    Logger.info(f"邮件已成功发送到: {to_address}")

            return True, "邮件发送成功"

        except smtplib.SMTPAuthenticationError as e:
            error_msg = "SMTP认证失败，请检查邮箱账号和密码"
            Logger.error(f"{error_msg}: {str(e)}")
            return False, error_msg
        except smtplib.SMTPConnectError as e:
            error_msg = f"无法连接到SMTP服务器 {self.smtp_host}:{self.smtp_port}"
            Logger.error(f"{error_msg}: {str(e)}")
            return False, error_msg
        except smtplib.SMTPException as e:
            error_msg = f"SMTP错误: {str(e)}"
            Logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"发送邮件时发生未知错误: {str(e)}"
            Logger.error(error_msg)
            return False, error_msg

    def test_connection(self) -> tuple[bool, str]:
        """
        测试SMTP连接

        Returns:
            tuple: (是否成功, 结果信息)
        """
        is_valid, error_msg = self.validate_config()
        if not is_valid:
            return False, error_msg

        try:
            Logger.info(f"正在测试SMTP连接: {self.smtp_host}:{self.smtp_port}")
            # 根据端口选择连接方式
            if self.smtp_port == 465:
                # 使用SSL连接（端口465）
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=self.timeout) as server:
                    Logger.info("已使用SSL加密连接")
                    server.login(self.from_address, self.from_password)
                    return True, "SMTP连接测试成功"
            else:
                # 使用STARTTLS连接（端口587）
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout) as server:
                    if self.use_tls:
                        server.starttls()
                    server.login(self.from_address, self.from_password)
                    return True, "SMTP连接测试成功"
        except Exception as e:
            error_msg = f"SMTP连接测试失败: {str(e)}"
            Logger.error(error_msg)
            return False, error_msg


# 创建全局邮件模块实例
email_module = EmailModule()