"""
百叶窗转场效果

基于Chromium浏览器的百叶窗转场效果。
"""

import numpy as np
import torch
from typing import Dict, Any
from .base import BaseTransition
from .registry import register_transition


@register_transition("blinds", "3D")
class BlindsTransition(BaseTransition):
    """百叶窗转场效果"""
    
    def get_params(self) -> Dict[str, Any]:
        return {
            "direction": {
                "type": "choice",
                "default": "horizontal",
                "options": ["horizontal", "vertical", "diagonal"],
                "description": "百叶窗方向"
            },
            "total_frames": {
                "type": "int",
                "default": 30,
                "min": 4,
                "max": 120,
                "description": "转场总帧数"
            },
            "fps": {
                "type": "int",
                "default": 30,
                "min": 15,
                "max": 60,
                "description": "帧率"
            },
            "slat_count": {
                "type": "int",
                "default": 10,
                "min": 5,
                "max": 20,
                "description": "百叶窗数量"
            },
            "width": {
                "type": "int",
                "default": 640,
                "min": 320,
                "max": 1920,
                "description": "输出宽度"
            },
            "height": {
                "type": "int",
                "default": 640,
                "min": 240,
                "max": 1080,
                "description": "输出高度"
            }
        }
    
    async def apply_transition(
        self,
        video1: torch.Tensor,
        video2: torch.Tensor,
        direction: str = "horizontal",
        total_frames: int = 30,
        fps: int = 30,
        slat_count: int = 10,
        width: int = 640,
        height: int = 640,
        **kwargs
    ) -> torch.Tensor:
        """应用百叶窗转场效果"""
        
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
        
        print(f"Blinds transition: {direction}, {total_frames} frames")
        
        # 生成转场帧
        output_frames = []
        
        for i in range(total_frames):
            progress = i / (total_frames - 1) if total_frames > 1 else 0
            
            # 获取对应帧
            frame1 = self.get_frame_at_progress(frames1, progress)
            frame2 = self.get_frame_at_progress(frames2, progress)
            
            # 调整帧尺寸
            frame1 = self.resize_frame(frame1, width, height)
            frame2 = self.resize_frame(frame2, width, height)
            
            # 应用百叶窗效果
            blended_frame = self._apply_blinds_effect(
                frame1, frame2, progress, direction, slat_count
            )
            
            output_frames.append(blended_frame)
        
        # 转换为tensor
        video_tensor = self.frames_to_tensor(output_frames)
        
        print(f"Blinds transition completed: {video_tensor.shape}")
        return video_tensor
    
    def _apply_blinds_effect(
        self,
        frame1: torch.Tensor,
        frame2: torch.Tensor,
        progress: float,
        direction: str,
        slat_count: int
    ) -> torch.Tensor:
        """应用百叶窗效果"""
        
        import cv2
        
        f1 = self.tensor_to_numpy(frame1)
        f2 = self.tensor_to_numpy(frame2)
        height, width = f1.shape[:2]
        
        # 创建遮罩
        mask = np.zeros((height, width), dtype=np.uint8)
        
        if direction == "horizontal":
            slat_height = height // slat_count
            for i in range(slat_count):
                y_start = i * slat_height
                y_end = y_start + slat_height
                
                # 计算当前百叶窗的开放程度
                open_progress = max(0, min(1, progress * slat_count - i))
                if open_progress > 0:
                    mask[y_start:y_end, :] = int(255 * open_progress)
        
        elif direction == "vertical":
            slat_width = width // slat_count
            for i in range(slat_count):
                x_start = i * slat_width
                x_end = x_start + slat_width
                
                # 计算当前百叶窗的开放程度
                open_progress = max(0, min(1, progress * slat_count - i))
                if open_progress > 0:
                    mask[:, x_start:x_end] = int(255 * open_progress)
        
        else:  # diagonal
            # 对角线百叶窗效果
            for y in range(height):
                for x in range(width):
                    # 计算对角线位置
                    diagonal_pos = (x + y) / (width + height)
                    slat_index = int(diagonal_pos * slat_count)
                    open_progress = max(0, min(1, progress * slat_count - slat_index))
                    mask[y, x] = int(255 * open_progress)
        
        # 应用遮罩
        result = np.where(mask[:, :, np.newaxis] == 0, f1, f2)
        
        return self.numpy_to_tensor(result)