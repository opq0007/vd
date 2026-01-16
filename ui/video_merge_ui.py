"""
视频合并 UI 组件

提供多个视频文件合并成一个视频文件的界面。
"""

import gradio as gr
from typing import Tuple, Optional
from pathlib import Path

from modules.video_merge_module import video_merge_module
from utils.logger import Logger


def create_video_merge_interface() -> gr.Blocks:
    """
    创建视频合并界面

    Returns:
        gr.Blocks: Gradio 界面块
    """
    with gr.Blocks() as video_merge_interface:
        gr.Markdown("## 视频合并")
        gr.Markdown("将多个视频文件合并成一个大的视频文件")

        with gr.Row():
            with gr.Column():
                # 输入文件区域
                gr.Markdown("### 📤 输入视频路径")
                gr.Markdown("支持本地路径和网络URL路径，每行一个路径")

                video_paths_input = gr.Textbox(
                    label="视频文件路径",
                    lines=10,
                    placeholder="输入视频文件路径，每行一个，例如：\n/path/to/video1.mp4\nhttps://example.com/video2.mp4\nC:/videos/video3.mp4",
                    info="支持 http/https URL 或本地文件路径，兼容 Windows (C:/) 和 Linux (/) 路径"
                )

                gr.Markdown("*提示：视频将按照输入顺序进行合并*")

                merge_btn = gr.Button("🎬 合并视频", variant="primary")

            with gr.Column():
                # 输出结果区域
                gr.Markdown("### 📝 合并结果")

                job_id_display = gr.Textbox(label="任务ID", interactive=False)
                status_info = gr.HTML("<div>等待提交任务...</div>")
                result_status = gr.JSON(label="详细状态", visible=False)

                gr.Markdown("#### 🎬 合并后的视频")
                video_output = gr.File(label="下载合并后的视频文件", visible=False)

                gr.Markdown("#### 📊 合并信息")
                merge_info = gr.Textbox(
                    label="合并信息",
                    lines=5,
                    interactive=False,
                    visible=False
                )

        # 绑定事件
        merge_btn.click(
            fn=process_video_merge,
            inputs=[video_paths_input],
            outputs=[
                job_id_display,
                status_info,
                result_status,
                video_output,
                merge_info
            ]
        )

    return video_merge_interface


async def process_video_merge(
    video_paths: str
) -> Tuple[str, str, dict, Optional[str], str]:
    """
    处理视频合并

    Args:
        video_paths: 视频文件路径列表，用换行符分隔

    Returns:
        Tuple: (任务ID, 状态信息, 详细状态, 视频文件, 合并信息)
    """
    try:
        # 参数验证：检查是否有输入路径
        if not video_paths or not video_paths.strip():
            status_html = """
            <div style="color: red;">
                <h3>❌ 处理失败</h3>
                <p>错误: 请提供至少一个视频文件路径</p>
            </div>
            """
            return (
                "error",
                status_html,
                {"success": False, "error": "请提供至少一个视频文件路径"},
                None,
                ""
            )

        Logger.info(f"开始处理视频合并")

        # 执行视频合并
        result = await video_merge_module.merge_videos(
            video_paths=video_paths,
            out_basename=None
        )

        # 生成任务ID
        job_id = result.get("out_basename", "unknown")

        # 构建状态信息
        if result["success"]:
            status_html = f"""
            <div style="color: green;">
                <h3>✅ 处理完成</h3>
                <p>任务ID: {job_id}</p>
                <p>合并视频数量: {result.get('input_count', 0)}</p>
            </div>
            """

            # 构建合并信息
            merge_info_text = f"""任务ID: {job_id}
合并视频数量: {result.get('input_count', 0)}
输出文件: {result.get('output_path', '')}"""
        else:
            status_html = f"""
            <div style="color: red;">
                <h3>❌ 处理失败</h3>
                <p>错误: {result.get('error', '未知错误')}</p>
            </div>
            """
            merge_info_text = f"""任务ID: {job_id}
错误: {result.get('error', '未知错误')}"""

        # 确保文件路径是绝对路径
        output_path = result.get("output_path")
        if output_path:
            output_path = str(Path(output_path).absolute())

        return (
            job_id,
            status_html,
            result,
            output_path,
            merge_info_text
        )

    except Exception as e:
        Logger.error(f"Video merge processing error: {e}")
        import traceback
        Logger.error(traceback.format_exc())

        status_html = f"""
        <div style="color: red;">
            <h3>❌ 处理失败</h3>
            <p>错误: {str(e)}</p>
        </div>
        """

        return (
            "error",
            status_html,
            {"success": False, "error": str(e)},
            None,
            f"错误: {str(e)}"
        )
