"""
棋盘格转场效果
"""

import numpy as np
import torch
from typing import Dict, Any
from .base import BaseTransition
from .registry import register_transition


@register_transition("checkerboard", "Basic")
class CheckerboardTransition(BaseTransition):
    """棋盘格转场效果"""
    
    def get_params(self) -> Dict[str, Any]:
        return {
            "total_frames": {"type": "int", "default": 30, "min": 4, "max": 120},
            "fps": {"type": "int", "default": 30, "min": 15, "max": 60},
            "grid_size": {"type": "int", "default": 8, "min": 4, "max": 16},
            "width": {"type": "int", "default": 640, "min": 320, "max": 1920},
            "height": {"type": "int", "default": 640, "min": 240, "max": 1080}
        }
    
    async def apply_transition(
        self,
        video1: torch.Tensor,
        video2: torch.Tensor,
        total_frames: int = 30,
        fps: int = 30,
        grid_size: int = 8,
        width: int = 640,
        height: int = 640,
        **kwargs
    ) -> torch.Tensor:
        """应用棋盘格转场效果"""
        
        frames1 = self.extract_frames(video1)
        frames2 = self.extract_frames(video2)
        
        output_frames = []
        
        for i in range(total_frames):
            progress = i / (total_frames - 1) if total_frames > 1 else 0
            
            frame1 = self.get_frame_at_progress(frames1, progress)
            frame2 = self.get_frame_at_progress(frames2, progress)
            
            frame1 = self.resize_frame(frame1, width, height)
            frame2 = self.resize_frame(frame2, width, height)
            
            blended_frame = self._apply_checkerboard_effect(
                frame1, frame2, progress, grid_size
            )
            
            output_frames.append(blended_frame)
        
        return self.frames_to_tensor(output_frames)
    
    def _apply_checkerboard_effect(
        self,
        frame1: torch.Tensor,
        frame2: torch.Tensor,
        progress: float,
        grid_size: int
    ) -> torch.Tensor:
        """应用棋盘格效果"""
        
        # 确保两个帧尺寸相同
        frame1, frame2 = self.ensure_same_size(frame1, frame2)
        
        f1 = self.tensor_to_numpy(frame1)
        f2 = self.tensor_to_numpy(frame2)
        height, width = f1.shape[:2]
        
        # 创建棋盘格遮罩
        mask = np.zeros((height, width), dtype=np.uint8)
        
        cell_height = height // grid_size
        cell_width = width // grid_size
        
        # 计算当前应该显示的格子数量
        total_cells = grid_size * grid_size
        cells_to_show = int(progress * total_cells)
        
        cell_index = 0
        for row in range(grid_size):
            for col in range(grid_size):
                y_start = row * cell_height
                y_end = min(y_start + cell_height, height)
                x_start = col * cell_width
                x_end = min(x_start + cell_width, width)
                
                # 棋盘格模式：只显示同色的格子
                if (row + col) % 2 == 0:
                    if cell_index < cells_to_show:
                        mask[y_start:y_end, x_start:x_end] = 255
                    cell_index += 1
        
        # 应用遮罩
        result = np.where(mask[:, :, np.newaxis] == 0, f1, f2)
        
        return self.numpy_to_tensor(result)