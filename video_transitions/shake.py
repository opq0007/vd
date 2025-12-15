"""
抖动转场效果
"""

import numpy as np
import torch
from typing import Dict, Any
from .base import BaseTransition
from .registry import register_transition


@register_transition("shake", "Effects")
class ShakeTransition(BaseTransition):
    """抖动转场效果"""
    
    def get_params(self) -> Dict[str, Any]:
        return {
            "shake_type": {
                "type": "choice",
                "default": "random",
                "options": ["random", "horizontal", "vertical", "rotation", "zoom"],
                "description": "抖动类型"
            },
            "total_frames": {"type": "int", "default": 30, "min": 4, "max": 120},
            "fps": {"type": "int", "default": 30, "min": 15, "max": 60},
            "shake_intensity": {"type": "float", "default": 1.0, "min": 0.1, "max": 3.0},
            "width": {"type": "int", "default": 640, "min": 320, "max": 1920},
            "height": {"type": "int", "default": 640, "min": 240, "max": 1080}
        }
    
    async def apply_transition(
        self,
        video1: torch.Tensor,
        video2: torch.Tensor,
        shake_type: str = "random",
        total_frames: int = 30,
        fps: int = 30,
        shake_intensity: float = 1.0,
        width: int = 640,
        height: int = 640,
        **kwargs
    ) -> torch.Tensor:
        """应用抖动转场效果"""
        
        frames1 = self.extract_frames(video1)
        frames2 = self.extract_frames(video2)
        
        output_frames = []
        
        for i in range(total_frames):
            progress = i / (total_frames - 1) if total_frames > 1 else 0
            
            # 根据进度选择源视频
            if progress < 0.5:
                source_frame = self.get_frame_at_progress(frames1, progress * 2)
            else:
                source_frame = self.get_frame_at_progress(frames2, (progress - 0.5) * 2)
            
            source_frame = self.resize_frame(source_frame, width, height)
            
            # 应用抖动效果
            shaken_frame = self._apply_shake_effect(
                source_frame, shake_type, shake_intensity
            )
            
            output_frames.append(shaken_frame)
        
        return self.frames_to_tensor(output_frames)
    
    def _apply_shake_effect(
        self,
        frame: torch.Tensor,
        shake_type: str,
        intensity: float
    ) -> torch.Tensor:
        """应用抖动效果"""
        import cv2
        
        f = self.tensor_to_numpy(frame)
        height, width = f.shape[:2]
        
        # 生成随机抖动参数
        if shake_type == "horizontal":
            dx = np.random.randn() * intensity * 10
            dy = 0
            angle = 0
            scale = 1.0
        elif shake_type == "vertical":
            dx = 0
            dy = np.random.randn() * intensity * 10
            angle = 0
            scale = 1.0
        elif shake_type == "rotation":
            dx = 0
            dy = 0
            angle = np.random.randn() * intensity * 5
            scale = 1.0
        elif shake_type == "zoom":
            dx = 0
            dy = 0
            angle = 0
            scale = 1.0 + np.random.randn() * intensity * 0.1
        else:  # random
            dx = np.random.randn() * intensity * 10
            dy = np.random.randn() * intensity * 10
            angle = np.random.randn() * intensity * 5
            scale = 1.0 + np.random.randn() * intensity * 0.1
        
        # 创建变换矩阵
        center = (width // 2, height // 2)
        M = cv2.getRotationMatrix2D(center, angle, scale)
        M[0, 2] += dx
        M[1, 2] += dy
        
        # 应用变换
        result = cv2.warpAffine(f, M, (width, height), borderMode=cv2.BORDER_REPLICATE)
        
        return self.numpy_to_tensor(result)