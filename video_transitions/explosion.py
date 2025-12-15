"""
爆炸转场效果
"""

import numpy as np
import torch
from typing import Dict, Any
from .base import BaseTransition
from .registry import register_transition


@register_transition("explosion", "Effects")
class ExplosionTransition(BaseTransition):
    """爆炸转场效果"""
    
    def get_params(self) -> Dict[str, Any]:
        return {
            "total_frames": {"type": "int", "default": 30, "min": 4, "max": 120},
            "fps": {"type": "int", "default": 30, "min": 15, "max": 60},
            "explosion_strength": {"type": "float", "default": 1.0, "min": 0.5, "max": 2.0},
            "width": {"type": "int", "default": 640, "min": 320, "max": 1920},
            "height": {"type": "int", "default": 640, "min": 240, "max": 1080}
        }
    
    async def apply_transition(
        self,
        video1: torch.Tensor,
        video2: torch.Tensor,
        total_frames: int = 30,
        fps: int = 30,
        explosion_strength: float = 1.0,
        width: int = 640,
        height: int = 640,
        **kwargs
    ) -> torch.Tensor:
        """应用爆炸转场效果"""
        
        frames1 = self.extract_frames(video1)
        frames2 = self.extract_frames(video2)
        
        output_frames = []
        
        for i in range(total_frames):
            progress = i / (total_frames - 1) if total_frames > 1 else 0
            
            frame1 = self.get_frame_at_progress(frames1, progress)
            frame2 = self.get_frame_at_progress(frames2, progress)
            
            frame1 = self.resize_frame(frame1, width, height)
            frame2 = self.resize_frame(frame2, width, height)
            
            if progress < 0.5:
                # 前半段：frame1爆炸消失
                blended_frame = self._apply_explosion_effect(frame1, progress * 2, explosion_strength)
            else:
                # 后半段：frame2出现
                blended_frame = self._apply_reverse_explosion_effect(frame2, (progress - 0.5) * 2, explosion_strength)
            
            output_frames.append(blended_frame)
        
        return self.frames_to_tensor(output_frames)
    
    def _apply_explosion_effect(self, frame: torch.Tensor, progress: float, strength: float) -> torch.Tensor:
        """应用爆炸效果"""
        import cv2
        
        f = self.tensor_to_numpy(frame)
        height, width = f.shape[:2]
        
        # 创建噪声位移
        noise = np.random.randn(height, width, 2) * progress * strength * 20
        
        # 应用位移
        result = np.zeros_like(f)
        for y in range(height):
            for x in range(width):
                # 计算位移后的坐标
                new_x = int(x + noise[y, x, 0])
                new_y = int(y + noise[y, x, 1])
                
                # 边界检查
                if 0 <= new_x < width and 0 <= new_y < height:
                    result[y, x] = f[new_y, new_x]
        
        return self.numpy_to_tensor(result)
    
    def _apply_reverse_explosion_effect(self, frame: torch.Tensor, progress: float, strength: float) -> torch.Tensor:
        """应用反向爆炸效果（从碎片汇聚）"""
        import cv2
        
        f = self.tensor_to_numpy(frame)
        height, width = f.shape[:2]
        
        # 创建反向噪声位移
        noise = np.random.randn(height, width, 2) * (1 - progress) * strength * 20
        
        # 应用位移
        result = np.zeros_like(f)
        for y in range(height):
            for x in range(width):
                # 计算位移后的坐标
                new_x = int(x + noise[y, x, 0])
                new_y = int(y + noise[y, x, 1])
                
                # 边界检查
                if 0 <= new_x < width and 0 <= new_y < height:
                    result[new_y, new_x] = f[y, x]
        
        return self.numpy_to_tensor(result)