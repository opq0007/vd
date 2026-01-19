"""
视频转场功能集成模块

提供简化的转场功能接口，便于在主应用中调用。
"""

import asyncio
import torch
import numpy as np
from pathlib import Path
from typing import Tuple, Optional
import time
import cv2

from .factory import TransitionFactory


class TransitionProcessor:
    """转场处理器"""
    
    def __init__(self):
        self.factory = TransitionFactory()
    
    async def process_transition(
        self,
        video1_path: str,
        video2_path: str,
        transition_name: str,
        total_frames: int = 30,
        fps: int = 30,
        width: int = 640,
        height: int = 640,
        output_dir: Optional[str] = None,  # 可选的输出目录
        output_basename: Optional[str] = None,  # 可选的输出文件名前缀
        **kwargs
    ) -> Tuple[Optional[str], str]:
        """
        处理转场效果
        
        Args:
            video1_path: 第一个视频/图片路径
            video2_path: 第二个视频/图片路径
            transition_name: 转场效果名称
            total_frames: 转场帧数
            fps: 帧率
            width: 输出宽度
            height: 输出高度
            output_dir: 可选的输出目录（如果提供，则使用该目录）
            output_basename: 可选的输出文件名前缀（如果提供，则使用该前缀）
            **kwargs: 其他参数
            
        Returns:
            Tuple[输出路径, 状态信息]
        """
        
        try:
            # 加载媒体文件
            video1_tensor = await self._load_media(video1_path, width, height)
            video2_tensor = await self._load_media(video2_path, width, height)
            
            # 创建转场效果
            transition = self.factory.create_transition(transition_name)
            
            # 应用转场效果
            result_tensor = await transition.apply_transition(
                video1_tensor,
                video2_tensor,
                total_frames=total_frames,
                fps=fps,
                width=width,
                height=height,
                **kwargs
            )
            
            # 保存视频
            output_path = await self._save_video(result_tensor, fps, width, height, output_dir, output_basename)
            
            return output_path, "转场视频生成成功"
            
        except Exception as e:
            return None, f"转场生成失败: {str(e)}"
    
    async def _load_media(self, file_path: str, width: int, height: int) -> torch.Tensor:
        """加载媒体文件（视频或图片）"""
        file_path = Path(file_path)
        
        # 检查文件是否存在
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 检查是否是目录
        if file_path.is_dir():
            raise ValueError(f"路径是目录而不是文件: {file_path}")
        
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
        height: int,
        output_dir: Optional[str] = None,  # 可选的输出目录
        output_basename: Optional[str] = None  # 可选的输出文件名前缀
    ) -> str:
        """保存视频文件"""
        from datetime import datetime
        from utils.video_utils import VideoUtils
        
        # 确定输出目录
        if output_dir:
            output_dir_path = Path(output_dir)
        else:
            # 如果没有提供，使用默认的 output 目录
            output_dir_path = Path("output")
        
        # 创建输出目录
        output_dir_path.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        if output_basename:
            # 使用提供的前缀
            output_path = output_dir_path / f"{output_basename}.mp4"
        else:
            # 使用默认的命名风格
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            output_path = output_dir_path / f"transition_{timestamp}.mp4"
        
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
    
    def get_available_transitions(self) -> dict:
        """获取可用的转场效果"""
        return self.factory.get_available_transitions()
    
    def get_transition_params(self, transition_name: str) -> dict:
        """获取转场效果的参数配置"""
        return self.factory.get_transition_params(transition_name)


# 全局转场处理器实例
transition_processor = TransitionProcessor()