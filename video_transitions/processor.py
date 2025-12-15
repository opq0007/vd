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

from video_transitions import TransitionFactory


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
            output_path = await self._save_video(result_tensor, fps, width, height)
            
            return output_path, "转场视频生成成功"
            
        except Exception as e:
            return None, f"转场生成失败: {str(e)}"
    
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
        from datetime import datetime
        
        # 创建输出目录
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_path = output_dir / f"transition_{timestamp}.mp4"
        
        # 设置视频编码器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(
            str(output_path),
            fourcc,
            fps,
            (width, height)
        )
        
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