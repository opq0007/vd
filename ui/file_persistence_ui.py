"""
文件持久化 UI 组件

提供将本地文件持久化到云平台的界面。
"""

import gradio as gr
from typing import List, Optional
import os

from modules.file_persistence import get_persistence_manager, UploadResult, PlatformType
from utils.logger import Logger


def parse_file_paths(text: str) -> List[str]:
    """
    解析文件路径文本

    Args:
        text: 多行文本，每行一个文件路径

    Returns:
        List[str]: 文件路径列表
    """
    if not text:
        return []

    # 分割行并去除空白
    paths = [line.strip() for line in text.strip().split('\n')]
    # 过滤空行
    paths = [path for path in paths if path]
    return paths


def upload_files_to_platform(
    file_paths_text: str,
    platform: str,
    repo_id: str,
    repo_type: str,
    commit_message: str,
    progress=gr.Progress()
) -> str:
    """
    上传文件到指定平台

    Args:
        file_paths_text: 文件路径文本（多行）
        platform: 平台名称
        repo_id: 仓库 ID
        repo_type: 仓库类型
        commit_message: 提交消息
        progress: Gradio 进度条

    Returns:
        str: 上传结果信息
    """
    try:
        # 获取持久化管理器
        manager = get_persistence_manager()
        if not manager:
            return "❌ 错误：文件持久化管理器未初始化。请检查配置文件中的 token 设置。"

        # 检查平台是否可用
        available_platforms = manager.get_available_platforms()
        if platform not in available_platforms:
            return f"❌ 错误：平台 '{platform}' 未配置或不可用。\n\n" \
                   f"可用平台：{', '.join(available_platforms) if available_platforms else '无'}\n\n" \
                   f"请在 config.py 中配置对应的 token：\n" \
                   f"  - HuggingFace: HUGGINGFACE_TOKEN\n" \
                   f"  - ModelScope: MODELSCOPE_TOKEN"

        # 解析文件路径
        file_paths = parse_file_paths(file_paths_text)
        if not file_paths:
            return "❌ 错误：未输入文件路径"

        # 验证文件是否存在
        valid_paths = []
        invalid_paths = []

        progress(0.1, desc="验证文件...")

        for path in file_paths:
            if os.path.exists(path):
                valid_paths.append(path)
            else:
                invalid_paths.append(path)

        # 初始化结果字符串
        result = ""

        if invalid_paths:
            result = f"⚠️ 警告：以下文件不存在，已跳过：\n"
            result += "\n".join(f"  - {path}" for path in invalid_paths)
            result += "\n\n"

        if not valid_paths:
            return f"{result}❌ 错误：没有有效的文件可上传"

        # 批量上传
        progress(0.2, desc="开始上传...")

        results = manager.batch_upload_files(
            file_paths=valid_paths,
            platform=platform,
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message=commit_message or "Batch upload files"
        )

        # 生成结果报告
        success_count = sum(1 for r in results if r.success)
        failed_count = len(results) - success_count

        progress(1.0, desc="上传完成！")

        result += f"📊 上传统计：\n"
        result += f"  总计：{len(results)} 个文件\n"
        result += f"  成功：{success_count} 个\n"
        result += f"  失败：{failed_count} 个\n\n"

        result += "📝 详细结果：\n"
        result += "-" * 80 + "\n"

        for i, (file_path, upload_result) in enumerate(zip(valid_paths, results), 1):
            result += f"\n[{i}] {os.path.basename(file_path)}\n"
            result += f"    状态：{'✅ 成功' if upload_result.success else '❌ 失败'}\n"

            if upload_result.success:
                result += f"    平台：{upload_result.platform}\n"
                result += f"    仓库：{upload_result.repo_id}\n"
                result += f"    仓库路径：{upload_result.file_path}\n"
                if upload_result.repo_url:
                    result += f"    仓库链接：{upload_result.repo_url}\n"
                if upload_result.download_url:
                    result += f"    下载链接：{upload_result.download_url}\n"
            else:
                result += f"    错误：{upload_result.error}\n"

        result += "\n" + "-" * 80 + "\n"

        if success_count > 0:
            result += "✅ 上传完成！"
        else:
            result += "❌ 上传失败！"

        return result

    except Exception as e:
        Logger.error(f"上传文件失败: {str(e)}")
        return f"❌ 错误：上传过程中发生异常\n\n详细信息：{str(e)}"


def get_available_platforms() -> List[str]:
    """获取可用的平台列表"""
    manager = get_persistence_manager()
    if manager:
        return manager.get_available_platforms()
    return []


def create_file_persistence_interface() -> gr.Blocks:
    """
    创建文件持久化界面

    Returns:
        gr.Blocks: Gradio 界面块
    """
    with gr.Blocks() as file_persistence_interface:
        gr.Markdown("## ☁️ 文件持久化")
        gr.Markdown("将本地文件批量上传到云存储平台（HuggingFace、ModelScope）")

        # 获取可用平台
        available_platforms = get_available_platforms()

        if not available_platforms:
            gr.Warning("⚠️ 未配置任何平台。请在 config.py 中设置 HUGGINGFACE_TOKEN 或 MODELSCOPE_TOKEN")

        with gr.Row():
            with gr.Column(scale=2):
                # 平台选择 - 始终显示所有平台，在上传时再检查是否可用
                platform_dropdown = gr.Dropdown(
                    choices=["huggingface", "modelscope"],
                    value="modelscope",  # 默认使用 ModelScope
                    label="选择平台",
                    info="选择要上传到的云平台",
                    interactive=True
                )

                # 仓库 ID
                repo_id_input = gr.Textbox(
                    label="仓库 ID",
                    placeholder="例如: username/my-dataset",
                    info="格式: username/repo-name"
                )

                # 仓库类型
                repo_type_dropdown = gr.Dropdown(
                    choices=["dataset", "model", "space"],
                    value="dataset",
                    label="仓库类型",
                    info="选择仓库类型"
                )

                # 提交消息
                commit_message_input = gr.Textbox(
                    label="提交消息",
                    placeholder="例如: Upload generated files",
                    value="Upload files",
                    info="Git 提交消息"
                )

            with gr.Column(scale=3):
                # 文件路径输入
                file_paths_textarea = gr.Textbox(
                    label="文件路径",
                    placeholder="输入本地文件路径，每行一个路径&#10;例如:&#10;D:/output/video1.mp4&#10;D:/output/video2.mp4&#10;D:/output/audio.wav",
                    lines=10,
                    info="支持多个文件，每行一个路径"
                )

                # 上传按钮
                upload_btn = gr.Button(
                    "🚀 开始上传",
                    variant="primary",
                    size="lg"
                )

        # 结果显示
        result_output = gr.Textbox(
            label="上传结果",
            lines=20,
            interactive=False,
            placeholder="上传结果将显示在这里..."
        )

        # 绑定事件
        upload_btn.click(
            fn=upload_files_to_platform,
            inputs=[
                file_paths_textarea,
                platform_dropdown,
                repo_id_input,
                repo_type_dropdown,
                commit_message_input
            ],
            outputs=result_output
        )

        # 使用说明
        gr.Markdown("---")
        gr.Markdown("### 📖 使用说明")
        gr.Markdown("""
#### 1. 配置 Token
在 `config.py` 中配置平台 Token：
```python
HUGGINGFACE_TOKEN = "your-huggingface-token"  # 从 https://huggingface.co/settings/tokens 获取
MODELSCOPE_TOKEN = "your-modelscope-token"    # 从 https://modelscope.cn/my/myaccesstoken 获取
```

#### 2. 输入文件路径
在文件路径输入框中输入要上传的文件路径，每行一个路径。支持：
- 绝对路径：`D:/output/video1.mp4`
- 相对路径：`output/video1.mp4`

#### 3. 填写仓库信息
- **仓库 ID**：格式为 `username/repo-name`，例如 `myusername/my-dataset`
- **仓库类型**：
  - `dataset`：数据集（推荐用于存储视频、音频等文件）
  - `model`：模型
  - `space`：Space 应用

#### 4. 点击上传
点击"开始上传"按钮，系统会自动批量上传所有文件。

#### 平台说明

**HuggingFace**（推荐）：
- 公共仓库：完全免费，无存储限制
- 私有数据集：100GB 免费存储
- 单个文件最大：200GB
- 访问地址：https://huggingface.co

**ModelScope**：
- 完全免费
- 单个文件最大：50GB
- 访问地址：https://modelscope.cn

#### 注意事项
- 确保文件路径正确且文件存在
- 确保仓库 ID 格式正确（username/repo-name）
- 上传大文件可能需要较长时间，请耐心等待
- 建议使用数据集（dataset）类型存储视频、音频等文件
        """)

    return file_persistence_interface