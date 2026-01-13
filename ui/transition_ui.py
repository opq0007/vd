"""
视频转场 UI 组件

提供视频转场特效界面。
"""

import gradio as gr
from typing import Tuple, Optional

from modules.transition_module import transition_module
from utils.logger import Logger


def create_transition_interface() -> gr.Blocks:
    """
    创建视频转场界面

    Returns:
        gr.Blocks: Gradio 界面块
    """
    with gr.Blocks() as transition_interface:
        gr.Markdown("## 视频转场特效")
        gr.Markdown("为图片或视频之间添加专业的转场效果")

        with gr.Row():
            with gr.Column():
                # 输入文件选择
                gr.Markdown("### 📁 输入文件")
                with gr.Row():
                    video1_input = gr.File(
                        label="第一个视频/图片",
                        file_types=[".mp4", ".avi", ".mov", ".png", ".jpg", ".jpeg"]
                    )
                    video2_input = gr.File(
                        label="第二个视频/图片",
                        file_types=[".mp4", ".avi", ".mov", ".png", ".jpg", ".jpeg"]
                    )

            with gr.Column():
                # 转场效果选择
                gr.Markdown("### 🎨 转场效果")

                # 获取可用的转场效果
                available_transitions = transition_module.get_available_transitions()

                # 按分类组织转场效果
                categories = {}
                for name, info in available_transitions.items():
                    category = info.get('category', 'General')
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(name)

                # 创建分类下拉框
                category_dropdown = gr.Dropdown(
                    label="效果分类",
                    choices=list(categories.keys()),
                    value=list(categories.keys())[0] if categories else "Basic"
                )

                # 创建转场效果下拉框
                default_category = list(categories.keys())[0] if categories else "Basic"
                default_transitions = categories.get(default_category, [])
                transition_dropdown = gr.Dropdown(
                    label="转场效果",
                    choices=default_transitions,
                    value=default_transitions[0] if default_transitions else None
                )

        # 参数配置区域
        gr.Markdown("### ⚙️ 参数配置")

        with gr.Row():
            with gr.Column():
                # 基础参数
                total_frames = gr.Slider(
                    label="转场帧数",
                    minimum=4,
                    maximum=300,
                    value=30,
                    step=1
                )
                fps = gr.Slider(
                    label="帧率 (FPS)",
                    minimum=15,
                    maximum=60,
                    value=30,
                    step=1
                )
                width = gr.Slider(
                    label="输出宽度",
                    minimum=320,
                    maximum=1920,
                    value=640,
                    step=32
                )
                height = gr.Slider(
                    label="输出高度",
                    minimum=240,
                    maximum=1080,
                    value=640,
                    step=32
                )

            with gr.Column():
                # 动态参数区域
                with gr.Group(visible=False) as effect_params_group:
                    # Warp 参数
                    with gr.Group(visible=False) as warp_params_row:
                        warp_type = gr.Dropdown(
                            label="扭曲类型",
                            choices=["swirl", "squeeze_h", "squeeze_v", "liquid", "wave"],
                            value="swirl"
                        )
                        warp_intensity = gr.Slider(
                            label="扭曲强度",
                            minimum=0.1,
                            maximum=2.0,
                            value=0.5,
                            step=0.1
                        )
                        warp_speed = gr.Slider(
                            label="扭曲速度",
                            minimum=0.1,
                            maximum=3.0,
                            value=1.0,
                            step=0.1
                        )

                    # Shake 参数
                    with gr.Group(visible=False) as shake_params_row:
                        shake_type = gr.Dropdown(
                            label="震动类型",
                            choices=["random", "horizontal", "vertical", "circular"],
                            value="random"
                        )
                        shake_intensity = gr.Slider(
                            label="震动强度",
                            minimum=0.1,
                            maximum=3.0,
                            value=1.0,
                            step=0.1
                        )

                    # Explosion 参数
                    with gr.Group(visible=False) as explosion_params_row:
                        explosion_strength = gr.Slider(
                            label="爆炸强度",
                            minimum=0.1,
                            maximum=3.0,
                            value=1.0,
                            step=0.1
                        )

                    # Flip3D 参数
                    with gr.Group(visible=False) as flip3d_params_row:
                        flip3d_direction = gr.Dropdown(
                            label="翻转方向",
                            choices=["horizontal", "vertical", "diagonal"],
                            value="horizontal"
                        )
                        perspective_strength = gr.Slider(
                            label="透视强度",
                            minimum=0.5,
                            maximum=2.0,
                            value=1.0,
                            step=0.1
                        )

                    # Blinds 参数
                    with gr.Group(visible=False) as blinds_params_row:
                        blinds_direction = gr.Dropdown(
                            label="百叶窗方向",
                            choices=["horizontal", "vertical", "diagonal"],
                            value="horizontal"
                        )
                        slat_count = gr.Slider(
                            label="百叶窗数量",
                            minimum=5,
                            maximum=20,
                            value=10,
                            step=1
                        )

                    # Page Turn 参数
                    with gr.Group(visible=False) as page_turn_params_row:
                        page_turn_direction = gr.Dropdown(
                            label="翻页方向",
                            choices=["right", "left", "up", "down"],
                            value="right"
                        )
                        curl_strength = gr.Slider(
                            label="卷曲强度",
                            minimum=0.5,
                            maximum=2.0,
                            value=1.0,
                            step=0.1
                        )
                        shadow_intensity = gr.Slider(
                            label="阴影强度",
                            minimum=0.0,
                            maximum=1.0,
                            value=0.6,
                            step=0.1
                        )

        # 生成按钮
        generate_btn = gr.Button("🎬 生成转场视频", variant="primary")

        # 输出区域
        gr.Markdown("### 📤 输出结果")
        with gr.Row():
            output_video = gr.Video(label="转场视频")
            status_output = gr.Textbox(label="状态", interactive=False)

        # 绑定事件
        def update_transitions(category):
            """更新转场效果列表"""
            return gr.Dropdown(choices=categories.get(category, []),
                            value=categories.get(category, [])[0] if categories.get(category) else None)

        def update_effect_params(transition_name):
            """根据选择的转场效果显示相应的参数配置"""
            # 默认所有参数组都隐藏
            effect_params_visible = False
            warp_params_visible = False
            shake_params_visible = False
            explosion_params_visible = False
            flip3d_params_visible = False
            blinds_params_visible = False
            page_turn_params_visible = False

            # 根据转场效果显示相应参数
            if transition_name == "warp":
                effect_params_visible = True
                warp_params_visible = True
            elif transition_name == "shake":
                effect_params_visible = True
                shake_params_visible = True
            elif transition_name == "explosion":
                effect_params_visible = True
                explosion_params_visible = True
            elif transition_name == "flip3d":
                effect_params_visible = True
                flip3d_params_visible = True
            elif transition_name == "blinds":
                effect_params_visible = True
                blinds_params_visible = True
            elif transition_name == "page_turn":
                effect_params_visible = True
                page_turn_params_visible = True

            return (
                gr.Group(visible=effect_params_visible),
                gr.Group(visible=warp_params_visible),
                gr.Group(visible=shake_params_visible),
                gr.Group(visible=explosion_params_visible),
                gr.Group(visible=flip3d_params_visible),
                gr.Group(visible=blinds_params_visible),
                gr.Group(visible=page_turn_params_visible),
            )

        category_dropdown.change(
            fn=update_transitions,
            inputs=[category_dropdown],
            outputs=[transition_dropdown]
        )

        transition_dropdown.change(
            fn=update_effect_params,
            inputs=[transition_dropdown],
            outputs=[
                effect_params_group,
                warp_params_row,
                shake_params_row,
                explosion_params_row,
                flip3d_params_row,
                blinds_params_row,
                page_turn_params_row,
            ]
        )

        generate_btn.click(
            fn=apply_transition_ui,
            inputs=[
                video1_input,
                video2_input,
                transition_dropdown,
                total_frames,
                fps,
                width,
                height,
                warp_type,
                warp_intensity,
                warp_speed,
                shake_type,
                shake_intensity,
                explosion_strength,
                flip3d_direction,
                perspective_strength,
                blinds_direction,
                slat_count,
                page_turn_direction,
                curl_strength,
                shadow_intensity,
            ],
            outputs=[output_video, status_output]
        )

    return transition_interface


async def apply_transition_ui(
    video1_input: Optional[str],
    video2_input: Optional[str],
    transition_name: str,
    total_frames: int,
    fps: int,
    width: int,
    height: int,
    warp_type: str = "swirl",
    warp_intensity: float = 0.5,
    warp_speed: float = 1.0,
    shake_type: str = "random",
    shake_intensity: float = 1.0,
    explosion_strength: float = 1.0,
    flip3d_direction: str = "horizontal",
    perspective_strength: float = 1.0,
    blinds_direction: str = "horizontal",
    slat_count: int = 10,
    page_turn_direction: str = "right",
    curl_strength: float = 1.0,
    shadow_intensity: float = 0.6,
) -> Tuple[Optional[str], str]:
    """
    应用转场效果

    Args:
        video1_input: 第一个视频/图片路径
        video2_input: 第二个视频/图片路径
        transition_name: 转场效果名称
        total_frames: 转场帧数
        fps: 帧率
        width: 输出宽度
        height: 输出高度
        warp_type: 扭曲类型
        warp_intensity: 扭曲强度
        warp_speed: 扭曲速度
        shake_type: 震动类型
        shake_intensity: 震动强度
        explosion_strength: 爆炸强度
        flip3d_direction: 翻转方向
        perspective_strength: 透视强度
        blinds_direction: 百叶窗方向
        slat_count: 百叶窗数量
        page_turn_direction: 翻页方向
        curl_strength: 卷曲强度
        shadow_intensity: 阴影强度

    Returns:
        Tuple[Optional[str], str]: (输出视频路径, 状态消息)
    """
    if not video1_input or not video2_input:
        return None, "请选择两个输入文件"

    if not transition_name:
        return None, "请选择转场效果"

    try:
        # 基础参数
        transition_params = {
            "total_frames": total_frames,
            "fps": fps,
            "width": width,
            "height": height
        }

        # 根据转场效果添加特定参数
        if transition_name == "warp":
            transition_params.update({
                "warp_type": warp_type,
                "warp_intensity": warp_intensity,
                "warp_speed": warp_speed,
                "max_scale": 1.3,
                "scale_recovery": True
            })
        elif transition_name == "shake":
            transition_params.update({
                "shake_type": shake_type,
                "shake_intensity": shake_intensity
            })
        elif transition_name == "explosion":
            transition_params.update({
                "explosion_strength": explosion_strength
            })
        elif transition_name == "flip3d":
            transition_params.update({
                "flip_direction": flip3d_direction,
                "perspective_strength": perspective_strength
            })
        elif transition_name == "blinds":
            transition_params.update({
                "direction": blinds_direction,
                "slat_count": slat_count
            })
        elif transition_name == "page_turn":
            transition_params.update({
                "direction": page_turn_direction,
                "curl_strength": curl_strength,
                "shadow_intensity": shadow_intensity
            })

        result = await transition_module.apply_transition(
            video1_path=video1_input,
            video2_path=video2_input,
            transition_name=transition_name,
            **transition_params
        )

        if result["success"]:
            return result["output_path"], "转场视频生成成功！"
        else:
            return None, f"生成失败: {result.get('error', '未知错误')}"

    except Exception as e:
        Logger.error(f"Transition application error: {e}")
        return None, f"生成失败: {str(e)}"