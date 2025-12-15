"""
视频叠化转场效果

纯Python实现的高性能叠化转场，支持多种叠化模式。
"""

import numpy as np
import torch
import cv2
from typing import Dict, Any, List, Tuple
from .base import BaseTransition
from .registry import register_transition


@register_transition("crossfade", "Basic")
class CrossfadeTransition(BaseTransition):
    """视频叠化转场效果"""
    
    def get_params(self) -> Dict[str, Any]:
        """获取参数配置"""
        return {
            "transition_mode": {
                "type": "choice",
                "default": "crossfade",
                "options": [
                    "crossfade",           # 直接叠化
                    "fade_to_black",       # 闪黑
                    "fade_to_white",       # 闪白
                    "fade_to_custom",      # 闪自定义色
                    "additive_dissolve",   # 叠加
                    "chromatic_dissolve",  # 色散叠化
                ],
                "description": "叠化模式"
            },
            "total_frames": {
                "type": "int",
                "default": 30,
                "min": 1,
                "max": 300,
                "description": "转场总帧数"
            },
            "fps": {
                "type": "int", 
                "default": 30,
                "min": 15,
                "max": 60,
                "description": "帧率"
            },
            "background_color": {
                "type": "string",
                "default": "#000000",
                "description": "背景颜色（用于fade_to_custom模式）"
            },
            "width": {
                "type": "int",
                "default": 640,
                "min": 320,
                "max": 3840,
                "description": "输出宽度"
            },
            "height": {
                "type": "int",
                "default": 640,
                "min": 240,
                "max": 2160,
                "description": "输出高度"
            }
        }
    
    async def apply_transition(
        self,
        video1: torch.Tensor,
        video2: torch.Tensor,
        total_frames: int = 30,
        fps: int = 30,
        transition_mode: str = "crossfade",
        background_color: str = "#000000",
        width: int = 640,
        height: int = 640,
        **kwargs
    ) -> torch.Tensor:
        """应用叠化转场效果"""
        
        # 验证参数
        self.validate_params(
            total_frames=total_frames,
            fps=fps,
            width=width,
            height=height
        )
        
        # 提取视频帧
        frames1 = self.extract_frames(video1)
        frames2 = self.extract_frames(video2)
        
        print(f"Crossfade transition: {len(frames1)} + {len(frames2)} frames -> {total_frames} frames")
        print(f"Mode: {transition_mode}")
        
        # 解析背景颜色
        bg_color_rgb = self.parse_color(background_color)
        
        # 生成转场帧
        output_frames = []
        
        for i in range(total_frames):
            progress = i / (total_frames - 1) if total_frames > 1 else 0
            
            # 获取对应的帧
            frame1 = self.get_frame_at_progress(frames1, progress)
            frame2 = self.get_frame_at_progress(frames2, progress)
            
            # 调整帧尺寸
            frame1 = self.resize_frame(frame1, width, height)
            frame2 = self.resize_frame(frame2, width, height)
            
            # 根据转场模式进行混合
            if transition_mode == "crossfade":
                blended_frame = self._blend_frames(frame1, frame2, progress)
            elif transition_mode == "fade_to_black":
                blended_frame = self._fade_through_color(frame1, frame2, progress, (0, 0, 0))
            elif transition_mode == "fade_to_white":
                blended_frame = self._fade_through_color(frame1, frame2, progress, (255, 255, 255))
            elif transition_mode == "fade_to_custom":
                blended_frame = self._fade_through_color(frame1, frame2, progress, bg_color_rgb)
            elif transition_mode == "additive_dissolve":
                blended_frame = self._additive_blend(frame1, frame2, progress)
            elif transition_mode == "chromatic_dissolve":
                blended_frame = self._chromatic_blend(frame1, frame2, progress)
            else:
                # 默认使用直接叠化
                blended_frame = self._blend_frames(frame1, frame2, progress)
            
            output_frames.append(blended_frame)
            
            # 显示进度
            if (i + 1) % 20 == 0 or i == total_frames - 1:
                progress_percent = (i + 1) / total_frames * 100
                print(f"Processing frames {i+1}/{total_frames} ({progress_percent:.1f}%)")
        
        # 转换为tensor
        video_tensor = self.frames_to_tensor(output_frames)
        
        print(f"Crossfade transition completed: {video_tensor.shape}")
        return video_tensor
    
    def _blend_frames(self, frame1: torch.Tensor, frame2: torch.Tensor, progress: float) -> torch.Tensor:
        """直接叠化混合"""
        # 确保两个帧尺寸相同
        frame1, frame2 = self.ensure_same_size(frame1, frame2)
        
        # 转换为numpy进行混合
        f1 = self.tensor_to_numpy(frame1)
        f2 = self.tensor_to_numpy(frame2)
        
        # 线性插值
        alpha = progress
        blended = cv2.addWeighted(f1, 1 - alpha, f2, alpha, 0)
        
        return self.numpy_to_tensor(blended)
    
    def _fade_through_color(
        self, 
        frame1: torch.Tensor, 
        frame2: torch.Tensor, 
        progress: float, 
        color: Tuple[int, int, int]
    ) -> torch.Tensor:
        """通过颜色淡入淡出"""
        # 确保两个帧尺寸相同
        frame1, frame2 = self.ensure_same_size(frame1, frame2)
        
        f1 = self.tensor_to_numpy(frame1)
        f2 = self.tensor_to_numpy(frame2)
        
        height, width = f1.shape[:2]
        color_frame = np.full((height, width, 3), color, dtype=np.uint8)
        
        if progress < 0.5:
            # 前半段：frame1 -> 颜色
            alpha = progress * 2
            result = cv2.addWeighted(f1, 1 - alpha, color_frame, alpha, 0)
        else:
            # 后半段：颜色 -> frame2
            alpha = (progress - 0.5) * 2
            result = cv2.addWeighted(color_frame, 1 - alpha, f2, alpha, 0)
        
        return self.numpy_to_tensor(result)
    
    def _additive_blend(self, frame1: torch.Tensor, frame2: torch.Tensor, progress: float) -> torch.Tensor:
        """加法混合"""
        # 确保两个帧尺寸相同
        frame1, frame2 = self.ensure_same_size(frame1, frame2)
        
        f1 = self.tensor_to_numpy(frame1).astype(np.float32)
        f2 = self.tensor_to_numpy(frame2).astype(np.float32)
        
        # 加法混合
        blended = np.clip(f1 + f2 * progress, 0, 255).astype(np.uint8)
        
        return self.numpy_to_tensor(blended)
    
    def _chromatic_blend(self, frame1: torch.Tensor, frame2: torch.Tensor, progress: float) -> torch.Tensor:
        """色散叠化（RGB通道错位）"""
        # 确保两个帧尺寸相同
        frame1, frame2 = self.ensure_same_size(frame1, frame2)
        
        f1 = self.tensor_to_numpy(frame1)
        f2 = self.tensor_to_numpy(frame2)
        
        height, width = f1.shape[:2]
        result = np.zeros_like(f1)
        
        # RGB通道错位混合
        channels = cv2.split(f1)
        channels2 = cv2.split(f2)
        
        for i, (ch1, ch2) in enumerate(zip(channels, channels2)):
            # 每个通道有不同的偏移
            offset = int((i - 1) * progress * 10)  # -10, 0, 10
            if offset != 0:
                M = np.float32([[1, 0, offset], [0, 1, 0]])
                ch2_shifted = cv2.warpAffine(ch2, M, (width, height))
            else:
                ch2_shifted = ch2
            
            # 混合通道
            result[:, :, i] = cv2.addWeighted(ch1, 1 - progress, ch2_shifted, progress, 0)
        
        return self.numpy_to_tensor(result)