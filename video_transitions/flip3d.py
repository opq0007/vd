"""
3D翻转转场效果
"""

import numpy as np
import torch
from typing import Dict, Any
from .base import BaseTransition
from .registry import register_transition


@register_transition("flip3d", "3D")
class Flip3DTransition(BaseTransition):
    """3D翻转转场效果"""
    
    def get_params(self) -> Dict[str, Any]:
        return {
            "flip_direction": {
                "type": "choice",
                "default": "horizontal",
                "options": ["horizontal", "vertical", "diagonal"],
                "description": "翻转方向"
            },
            "total_frames": {"type": "int", "default": 30, "min": 4, "max": 120},
            "fps": {"type": "int", "default": 30, "min": 15, "max": 60},
            "perspective_strength": {"type": "float", "default": 1.0, "min": 0.5, "max": 2.0},
            "width": {"type": "int", "default": 640, "min": 320, "max": 1920},
            "height": {"type": "int", "default": 640, "min": 240, "max": 1080}
        }
    
    async def apply_transition(
        self,
        video1: torch.Tensor,
        video2: torch.Tensor,
        flip_direction: str = "horizontal",
        total_frames: int = 30,
        fps: int = 30,
        perspective_strength: float = 1.0,
        width: int = 640,
        height: int = 640,
        **kwargs
    ) -> torch.Tensor:
        """应用3D翻转转场效果"""
        
        frames1 = self.extract_frames(video1)
        frames2 = self.extract_frames(video2)
        
        output_frames = []
        
        for i in range(total_frames):
            progress = i / (total_frames - 1) if total_frames > 1 else 0
            
            frame1 = self.get_frame_at_progress(frames1, progress)
            frame2 = self.get_frame_at_progress(frames2, progress)
            
            frame1 = self.resize_frame(frame1, width, height)
            frame2 = self.resize_frame(frame2, width, height)
            
            # 应用3D翻转效果
            blended_frame = self._apply_3d_flip_effect(
                frame1, frame2, progress, flip_direction, perspective_strength
            )
            
            output_frames.append(blended_frame)
        
        return self.frames_to_tensor(output_frames)
    
    def _apply_3d_flip_effect(
        self,
        frame1: torch.Tensor,
        frame2: torch.Tensor,
        progress: float,
        flip_direction: str,
        perspective_strength: float
    ) -> torch.Tensor:
        """应用3D翻转效果"""
        import cv2
        
        f1 = self.tensor_to_numpy(frame1)
        f2 = self.tensor_to_numpy(frame2)
        height, width = f1.shape[:2]
        
        # 计算翻转角度
        flip_angle = progress * 180
        
        # 根据翻转角度选择源图像和透明度
        if flip_angle <= 90:
            # 前半段：使用frame1，从正常到变窄
            current_frame = f1
            width_scale = 1 - (flip_angle / 90) * 0.8
            height_scale = 1.0  # 高度保持不变
        else:
            # 后半段：使用frame2，从窄到正常
            current_frame = f2
            width_scale = ((flip_angle - 90) / 90) * 0.8
            height_scale = 1.0  # 高度保持不变
        
        # 确保最后几帧恢复正常
        if progress >= 0.95:
            width_scale = 1.0
            height_scale = 1.0
        
        # 创建透视变换
        if flip_direction == "horizontal":
            # 水平翻转
            width_scale = max(width_scale, 0.2)  # 确保最小缩放比例
            pts1 = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
            pts2 = np.float32([
                [width * (1 - width_scale) / 2, 0],
                [width * (1 + width_scale) / 2, 0],
                [width * (1 + width_scale) / 2, height],
                [width * (1 - width_scale) / 2, height]
            ])
                
        elif flip_direction == "vertical":
            # 垂直翻转
            height_scale = max(height_scale, 0.2)  # 确保最小缩放比例
            pts1 = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
            pts2 = np.float32([
                [0, height * (1 - height_scale) / 2],
                [width, height * (1 - height_scale) / 2],
                [width, height * (1 + height_scale) / 2],
                [0, height * (1 + height_scale) / 2]
            ])
                
        else:  # diagonal
            # 对角线翻转 - 使用更平滑的缩放
            scale = abs(np.cos(np.radians(flip_angle))) * 0.7 + 0.3  # 调整缩放范围
            scale = max(scale, 0.3)  # 确保最小缩放比例
            pts1 = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
            pts2 = np.float32([
                [width * (1 - scale) / 2, height * (1 - scale) / 2],
                [width * (1 + scale) / 2, height * (1 - scale) / 2],
                [width * (1 + scale) / 2, height * (1 + scale) / 2],
                [width * (1 - scale) / 2, height * (1 + scale) / 2]
            ])
        
        # 应用透视变换
        M = cv2.getPerspectiveTransform(pts1, pts2)
        result = cv2.warpPerspective(current_frame, M, (width, height), borderMode=cv2.BORDER_REPLICATE)
        
        return self.numpy_to_tensor(result)