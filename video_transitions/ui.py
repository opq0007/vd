"""
视频转场效果的Gradio界面
"""

import gradio as gr
import asyncio
import torch
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
import time

from video_transitions import TransitionFactory
from video_transitions.base import BaseTransition


class VideoTransitionUI:
    """视频转场效果UI类"""
    
    def __init__(self):
        self.transition_factory = TransitionFactory()
        self.available_transitions = self.transition_factory.get_available_transitions()
        self.current_transition = None
        
    def create_interface(self) -> gr.Blocks:
        """创建转场效果界面"""
        
        with gr.Blocks(title="视频转场特效") as interface:
            gr.Markdown("# 🎬 视频转场特效")
            gr.Markdown("为图片或视频之间添加专业的转场效果")
            
            with gr.Row():
                with gr.Column(scale=2):
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
                
                with gr.Column(scale=1):
                    # 预览区域
                    gr.Markdown("### 👁️ 预览")
                    preview1 = gr.Image(label="预览1", type="numpy")
                    preview2 = gr.Image(label="预览2", type="numpy")
            
            # 转场效果选择
            gr.Markdown("### 🎨 转场效果")
            
            with gr.Row():
                # 获取转场效果分类
                categories = self._get_categories()
                category_dropdown = gr.Dropdown(
                    label="效果分类",
                    choices=list(categories.keys()),
                    value="Basic"
                )
                
                transition_dropdown = gr.Dropdown(
                    label="转场效果",
                    choices=self._get_transitions_by_category("Basic"),
                    value="crossfade"
                )
            
            # 当分类改变时更新转场效果列表
            category_dropdown.change(
                fn=self._update_transitions,
                inputs=[category_dropdown],
                outputs=[transition_dropdown]
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
                    dynamic_params = gr.Column()
            
            # 当转场效果改变时更新参数
            transition_dropdown.change(
                fn=self._update_params,
                inputs=[transition_dropdown],
                outputs=[dynamic_params]
            )
            
            # 生成按钮和进度
            with gr.Row():
                generate_btn = gr.Button("🎬 生成转场视频", variant="primary")
                progress_bar = gr.Progress()
                status_text = gr.Textbox(label="状态", interactive=False)
            
            # 输出区域
            gr.Markdown("### 📤 输出结果")
            with gr.Row():
                output_video = gr.Video(label="转场视频")
                download_btn = gr.DownloadButton(
                    label="💾 下载视频",
                    visible=False
                )
            
            # 绑定事件
            video1_input.change(
                fn=self._update_preview,
                inputs=[video1_input],
                outputs=[preview1]
            )
            
            video2_input.change(
                fn=self._update_preview,
                inputs=[video2_input],
                outputs=[preview2]
            )
            
            generate_btn.click(
                fn=self.generate_transition,
                inputs=[
                    video1_input,
                    video2_input,
                    transition_dropdown,
                    total_frames,
                    fps,
                    width,
                    height
                ],
                outputs=[output_video, download_btn, status_text]
            )
        
        return interface
    
    def _get_categories(self) -> Dict[str, list]:
        """获取转场效果分类"""
        categories = {}
        for name, info in self.available_transitions.items():
            category = info.get('category', 'General')
            if category not in categories:
                categories[category] = []
            categories[category].append(name)
        return categories
    
    def _get_transitions_by_category(self, category: str) -> list:
        """根据分类获取转场效果"""
        transitions = []
        for name, info in self.available_transitions.items():
            if info.get('category', 'General') == category:
                transitions.append(name)
        return transitions
    
    def _update_transitions(self, category: str) -> gr.Dropdown:
        """更新转场效果列表"""
        transitions = self._get_transitions_by_category(category)
        return gr.Dropdown(choices=transitions, value=transitions[0] if transitions else None)
    
    def _update_params(self, transition_name: str) -> gr.Column:
        """更新参数配置界面"""
        params_info = self.transition_factory.get_transition_params(transition_name)
        
        with gr.Column() as param_col:
            for param_name, param_config in params_info.items():
                if param_name in ['total_frames', 'fps', 'width', 'height']:
                    continue  # 跳过基础参数
                
                param_type = param_config.get('type', 'string')
                default_value = param_config.get('default')
                description = param_config.get('description', '')
                
                if param_type == 'choice':
                    gr.Dropdown(
                        label=description,
                        choices=param_config.get('options', []),
                        value=default_value
                    )
                elif param_type == 'int':
                    gr.Slider(
                        label=description,
                        minimum=param_config.get('min', 0),
                        maximum=param_config.get('max', 100),
                        value=default_value,
                        step=1
                    )
                elif param_type == 'float':
                    gr.Slider(
                        label=description,
                        minimum=param_config.get('min', 0.0),
                        maximum=param_config.get('max', 1.0),
                        value=default_value,
                        step=param_config.get('step', 0.1)
                    )
                elif param_type == 'boolean':
                    gr.Checkbox(
                        label=description,
                        value=default_value
                    )
                elif param_type == 'string':
                    gr.Textbox(
                        label=description,
                        value=default_value
                    )
        
        return param_col
    
    def _update_preview(self, file_path: str) -> Optional[np.ndarray]:
        """更新预览图片"""
        if not file_path:
            return None
        
        try:
            from PIL import Image
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                # 图片文件直接显示
                image = Image.open(file_path)
                return np.array(image)
            else:
                # 视频文件显示第一帧
                import cv2
                cap = cv2.VideoCapture(file_path)
                ret, frame = cap.read()
                cap.release()
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    return frame
        except Exception as e:
            print(f"预览更新失败: {e}")
        
        return None
    
    async def generate_transition(
        self,
        video1_path: str,
        video2_path: str,
        transition_name: str,
        total_frames: int,
        fps: int,
        width: int,
        height: int,
        progress=gr.Progress()
    ) -> Tuple[Optional[str], Optional[gr.DownloadButton], str]:
        """生成转场视频"""
        
        if not video1_path or not video2_path:
            return None, gr.DownloadButton(visible=False), "请选择两个输入文件"
        
        if not transition_name:
            return None, gr.DownloadButton(visible=False), "请选择转场效果"
        
        try:
            status = "开始生成转场视频..."
            progress(0.1, desc=status)
            
            # 加载视频/图片
            video1_tensor = await self._load_media(video1_path, width, height)
            video2_tensor = await self._load_media(video2_path, width, height)
            
            progress(0.2, desc="媒体文件加载完成")
            
            # 创建转场效果实例
            transition = self.transition_factory.create_transition(transition_name)
            
            progress(0.3, desc="开始应用转场效果")
            
            # 应用转场效果
            result_tensor = await transition.apply_transition(
                video1_tensor,
                video2_tensor,
                total_frames=total_frames,
                fps=fps,
                width=width,
                height=height
            )
            
            progress(0.8, desc="转场效果应用完成")
            
            # 保存视频
            output_path = await self._save_video(result_tensor, fps, width, height)
            
            progress(1.0, desc="转场视频生成完成")
            
            # 创建下载按钮
            download_btn = gr.DownloadButton(
                label="💾 下载视频",
                value=output_path,
                visible=True
            )
            
            return output_path, download_btn, "转场视频生成成功！"
            
        except Exception as e:
            print(f"转场生成失败: {e}")
            return None, gr.DownloadButton(visible=False), f"生成失败: {str(e)}"
    
    async def _load_media(self, file_path: str, width: int, height: int) -> torch.Tensor:
        """加载媒体文件（视频或图片）"""
        file_path = Path(file_path)
        
        if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
            # 加载图片
            from PIL import Image
            image = Image.open(file_path)
            image = image.resize((width, height))
            
            # 转换为tensor
            numpy_array = np.array(image)
            if numpy_array.max() > 1.0:
                numpy_array = numpy_array.astype(np.float32) / 255.0
            
            tensor = torch.from_numpy(numpy_array)
            return tensor.unsqueeze(0)  # 添加batch维度
            
        else:
            # 加载视频
            import cv2
            cap = cv2.VideoCapture(str(file_path))
            frames = []
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 调整尺寸
                frame = cv2.resize(frame, (width, height))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # 转换为tensor
                numpy_array = frame.astype(np.float32) / 255.0
                tensor = torch.from_numpy(numpy_array)
                frames.append(tensor)
            
            cap.release()
            
            if not frames:
                raise ValueError("无法从视频文件中读取帧")
            
            return torch.stack(frames)
    
    async def _save_video(
        self,
        tensor: torch.Tensor,
        fps: int,
        width: int,
        height: int
    ) -> str:
        """保存视频文件"""
        import cv2
        from datetime import datetime
        from utils.video_utils import VideoUtils
        
        # 创建输出目录
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_path = output_dir / f"transition_{timestamp}.mp4"
        
        # 使用视频工具类创建写入器
        out = VideoUtils.create_video_writer(output_path, width, height, fps)
        
        if out is None:
            raise RuntimeError(f"无法创建视频写入器: {output_path}")
        
        # 写入帧
        for i in range(tensor.shape[0]):
            frame = tensor[i].cpu().numpy()
            frame = (frame * 255).astype(np.uint8)
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            out.write(frame_bgr)
        
        out.release()
        
        return str(output_path)