"""
基础 UI 组件

提供通用的 UI 组件和样式。
"""

import gradio as gr


def get_custom_css() -> str:
    """
    获取自定义 CSS 样式

    Returns:
        str: CSS 样式字符串
    """
    return """
    .container {
        max-width: 1200px;
        margin: 0 auto;
    }
    .upload-area {
        border: 2px dashed #ccc;
        border-radius: 10px;
        padding: 40px;
        text-align: center;
        margin: 20px 0;
        transition: border-color 0.3s;
    }
    .upload-area:hover {
        border-color: #007bff;
    }
    .result-area {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin-top: 20px;
    }
    .segment {
        background-color: white;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 10px;
        border-left: 4px solid #007bff;
    }

    /* 字体回退处理 - 避免字体文件404错误影响界面 */
    @font-face {
        font-family: 'ui-monospace';
        src: local('Consolas'), local('Monaco'), local('Courier New'), monospace;
        font-display: swap;
    }

    body, pre, code {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
                     'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
                     sans-serif, 'ui-monospace', 'Consolas', 'Monaco', 'Courier New', monospace !important;
    }

    /* 隐藏字体加载错误 */
    @font-face {
        font-family: 'ui-monospace';
        src: url('about:blank');
        unicode-range: U+0-10FFFF;
    }
    """


def create_header(title: str = "🎙️ 整合版 Whisper 语音转文字服务") -> gr.Markdown:
    """
    创建页面头部

    Args:
        title: 页面标题

    Returns:
        gr.Markdown: 头部组件
    """
    return gr.Markdown(f"# {title}")


def create_file_upload(
    label: str = "上传文件",
    file_types: list = None,
    placeholder: str = "点击或拖拽文件到此处"
) -> gr.File:
    """
    创建文件上传组件

    Args:
        label: 标签文本
        file_types: 支持的文件类型
        placeholder: 占位符文本

    Returns:
        gr.File: 文件上传组件
    """
    if file_types is None:
        file_types = [".mp4", ".avi", ".mov", ".mp3", ".wav", ".m4a"]

    return gr.File(
        label=label,
        file_types=file_types,
        placeholder=placeholder
    )


def create_result_display(label: str = "结果") -> gr.Textbox:
    """
    创建结果显示组件

    Args:
        label: 标签文本

    Returns:
        gr.Textbox: 结果显示组件
    """
    return gr.Textbox(
        label=label,
        lines=10,
        interactive=False,
        placeholder="处理结果将显示在这里..."
    )


def create_status_display(label: str = "状态") -> gr.Textbox:
    """
    创建状态显示组件

    Args:
        label: 标签文本

    Returns:
        gr.Textbox: 状态显示组件
    """
    return gr.Textbox(
        label=label,
        interactive=False,
        placeholder="等待处理..."
    )


def create_progress_bar() -> gr.Progress:
    """
    创建进度条组件

    Returns:
        gr.Progress: 进度条组件
    """
    return gr.Progress()