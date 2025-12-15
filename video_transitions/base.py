"""
视频转场效果基类

定义所有转场效果的通用接口和基础功能。
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import torch
from pathlib import Path


class BaseTransition(ABC):
    """视频转场效果基类"""
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.category = "VideoTransition"
        
    @abstractmethod
    def get_params(self) -> Dict[str, Any]:
        """获取转场参数配置"""
        pass
    
    @abstractmethod
    async def apply_transition(
        self, 
        video1: torch.Tensor, 
        video2: torch.Tensor, 
        total_frames: int = 30,
        fps: int = 30,
        **kwargs
    ) -> torch.Tensor:
        """
        应用转场效果
        
        Args:
            video1: 第一个视频的tensor [B, H, W, C]
            video2: 第二个视频的tensor [B, H, W, C] 
            total_frames: 转场总帧数
            fps: 帧率
            **kwargs: 其他参数
            
        Returns:
            转场后的视频tensor [B, H, W, C]
        """
        pass
    
    def extract_frames(self, video_tensor: torch.Tensor) -> List[torch.Tensor]:
        """从视频tensor中提取帧列表"""
        frames = []
        
        if video_tensor.dim() == 4:
            batch_size = video_tensor.shape[0]
            for i in range(batch_size):
                frame = video_tensor[i]
                frames.append(frame)
        else:
            frames.append(video_tensor)
            
        return frames
    
    def frames_to_tensor(self, frames: List[torch.Tensor]) -> torch.Tensor:
        """将帧列表转换为视频tensor"""
        return torch.stack(frames)
    
    def tensor_to_numpy(self, tensor: torch.Tensor) -> np.ndarray:
        """将tensor转换为numpy数组"""
        if tensor.requires_grad:
            tensor = tensor.detach()
        
        # 转换为HWC格式的numpy数组
        if tensor.dim() == 4:
            # [B, H, W, C] -> [H, W, C]
            numpy_array = tensor[0].cpu().numpy()
        else:
            # [H, W, C]
            numpy_array = tensor.cpu().numpy()
            
        # 确保值在0-255范围内
        if numpy_array.max() <= 1.0:
            numpy_array = (numpy_array * 255).astype(np.uint8)
        else:
            numpy_array = numpy_array.astype(np.uint8)
            
        return numpy_array
    
    def numpy_to_tensor(self, numpy_array: np.ndarray) -> torch.Tensor:
        """将numpy数组转换为tensor"""
        # 归一化到0-1范围
        if numpy_array.max() > 1.0:
            numpy_array = numpy_array.astype(np.float32) / 255.0
            
        # 转换为tensor [H, W, C]
        tensor = torch.from_numpy(numpy_array)
        
        return tensor
    
    def parse_color(self, color_str: str) -> Tuple[int, int, int]:
        """解析颜色字符串为RGB元组"""
        if color_str.startswith('#'):
            # 移除#号
            color_str = color_str[1:]
            
        if len(color_str) == 6:
            # 十六进制颜色
            r = int(color_str[0:2], 16)
            g = int(color_str[2:4], 16) 
            b = int(color_str[4:6], 16)
        elif color_str.lower() == 'black':
            r, g, b = 0, 0, 0
        elif color_str.lower() == 'white':
            r, g, b = 255, 255, 255
        elif color_str.lower() == 'red':
            r, g, b = 255, 0, 0
        elif color_str.lower() == 'green':
            r, g, b = 0, 255, 0
        elif color_str.lower() == 'blue':
            r, g, b = 0, 0, 255
        else:
            # 默认黑色
            r, g, b = 0, 0, 0
            
        return (r, g, b)
    
    def validate_params(self, **kwargs) -> None:
        """验证参数有效性"""
        total_frames = kwargs.get('total_frames', 30)
        fps = kwargs.get('fps', 30)
        width = kwargs.get('width', 640)
        height = kwargs.get('height', 640)
        
        if not (1 <= total_frames <= 300):
            raise ValueError("total_frames必须在1-300之间")
        if not (15 <= fps <= 60):
            raise ValueError("fps必须在15-60之间")
        if not (320 <= width <= 3840):
            raise ValueError("width必须在320-3840之间")
        if not (240 <= height <= 2160):
            raise ValueError("height必须在240-2160之间")
    
    def get_frame_at_progress(self, frames: List[torch.Tensor], progress: float) -> torch.Tensor:
        """根据进度获取对应帧"""
        if len(frames) == 1:
            return frames[0]
        
        frame_index = min(int(progress * (len(frames) - 1)), len(frames) - 1)
        return frames[frame_index]
    
    def resize_frame(self, frame: torch.Tensor, width: int, height: int) -> torch.Tensor:
        """调整帧尺寸"""
        import torch.nn.functional as F
        
        # 转换为numpy
        frame_np = self.tensor_to_numpy(frame)
        
        # 检查是否需要调整尺寸
        current_height, current_width = frame_np.shape[:2]
        if current_width == width and current_height == height:
            return frame  # 尺寸匹配，直接返回
        
        # 使用OpenCV调整尺寸
        import cv2
        resized = cv2.resize(frame_np, (width, height), interpolation=cv2.INTER_LINEAR)
        
        # 转换回tensor
        return self.numpy_to_tensor(resized)
    
    def ensure_same_size(self, frame1: torch.Tensor, frame2: torch.Tensor) -> tuple:
        """确保两个帧具有相同尺寸"""
        # 获取两个帧的尺寸
        f1_np = self.tensor_to_numpy(frame1)
        f2_np = self.tensor_to_numpy(frame2)
        
        h1, w1 = f1_np.shape[:2]
        h2, w2 = f2_np.shape[:2]
        
        # 如果尺寸不同，调整到较小的尺寸
        if (h1 != h2) or (w1 != w2):
            target_height = min(h1, h2)
            target_width = min(w1, w2)
            
            import cv2
            if (h1 != target_height) or (w1 != target_width):
                f1_np = cv2.resize(f1_np, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
            if (h2 != target_height) or (w2 != target_width):
                f2_np = cv2.resize(f2_np, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
            
            frame1 = self.numpy_to_tensor(f1_np)
            frame2 = self.numpy_to_tensor(f2_np)
        
        return frame1, frame2