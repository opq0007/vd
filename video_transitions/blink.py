"""
视频眨眼转场效果

纯Python实现的高性能眨眼转场，模拟眼睑闭合效果。
"""

import numpy as np
import torch
import cv2
from typing import Dict, Any
from .base import BaseTransition
from .registry import register_transition


@register_transition("blink", "Basic")
class BlinkTransition(BaseTransition):
    """视频眨眼转场效果"""
    
    def get_params(self) -> Dict[str, Any]:
        """获取参数配置"""
        return {
            "total_frames": {
                "type": "int",
                "default": 60,
                "min": 4,
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
            "blink_speed": {
                "type": "float",
                "default": 1.0,
                "min": 0.3,
                "max": 3.0,
                "step": 0.1,
                "description": "眨眼速度"
            },
            "blur_intensity": {
                "type": "float",
                "default": 0.8,
                "min": 0.0,
                "max": 2.0,
                "step": 0.1,
                "description": "模糊强度"
            },
            "eyelid_curve": {
                "type": "float",
                "default": 0.3,
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "description": "眼睑弧度"
            },
            "edge_feather": {
                "type": "float",
                "default": 0.2,
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "description": "边缘羽化"
            },
            "mask_color": {
                "type": "choice",
                "default": "black",
                "options": ["black", "white", "gray"],
                "description": "遮罩颜色"
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
        total_frames: int = 60,
        fps: int = 30,
        blink_speed: float = 1.0,
        blur_intensity: float = 0.8,
        eyelid_curve: float = 0.3,
        edge_feather: float = 0.2,
        mask_color: str = "black",
        width: int = 640,
        height: int = 640,
        **kwargs
    ) -> torch.Tensor:
        """应用眨眼转场效果"""
        
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
        
        print(f"Blink transition: {len(frames1)} + {len(frames2)} frames -> {total_frames} frames")
        
        # 解析遮罩颜色
        mask_rgb = self.parse_color(mask_color)
        
        # 生成转场帧
        output_frames = []
        
        # 眨眼时间点（总帧数的中间点）
        blink_midpoint = total_frames // 2
        
        for i in range(total_frames):
            # 计算眨眼进度（0-1-0的曲线）
            if i < blink_midpoint:
                # 闭眼阶段
                blink_progress = (i / blink_midpoint) ** blink_speed
            else:
                # 睁眼阶段
                blink_progress = ((total_frames - i) / blink_midpoint) ** blink_speed
            
            blink_progress = min(1.0, max(0.0, blink_progress))
            
            # 根据进度选择源视频
            if i < blink_midpoint:
                # 前半段使用第一个视频
                progress = i / (total_frames - 1) if total_frames > 1 else 0
                source_frame = self.get_frame_at_progress(frames1, progress)
            else:
                # 后半段使用第二个视频
                progress = i / (total_frames - 1) if total_frames > 1 else 0
                source_frame = self.get_frame_at_progress(frames2, progress)
            
            # 调整帧尺寸
            source_frame = self.resize_frame(source_frame, width, height)
            
            # 应用眨眼效果
            blinked_frame = self._apply_blink_effect(
                source_frame,
                blink_progress,
                blur_intensity,
                eyelid_curve,
                edge_feather,
                mask_rgb,
                width,
                height
            )
            
            output_frames.append(blinked_frame)
            
            # 显示进度
            if (i + 1) % 20 == 0 or i == total_frames - 1:
                progress_percent = (i + 1) / total_frames * 100
                print(f"Processing frames {i+1}/{total_frames} ({progress_percent:.1f}%)")
        
        # 转换为tensor
        video_tensor = self.frames_to_tensor(output_frames)
        
        print(f"Blink transition completed: {video_tensor.shape}")
        return video_tensor
    
    def _apply_blink_effect(
        self,
        frame: torch.Tensor,
        blink_progress: float,
        blur_intensity: float,
        eyelid_curve: float,
        edge_feather: float,
        mask_color: tuple,
        width: int,
        height: int
    ) -> torch.Tensor:
        """应用眨眼效果到单帧"""
        
        # 转换为numpy
        frame_np = self.tensor_to_numpy(frame)
        
        # 创建眼睑遮罩
        eyelid_mask = self._create_eyelid_mask(
            height, width, blink_progress, eyelid_curve, edge_feather
        )
        
        # 应用模糊效果（眨眼时的模糊）
        if blink_progress > 0.1:
            blur_kernel_size = int(5 + blur_intensity * blink_progress * 15)
            blur_kernel_size = blur_kernel_size if blur_kernel_size % 2 == 1 else blur_kernel_size + 1
            blurred_frame = cv2.GaussianBlur(frame_np, (blur_kernel_size, blur_kernel_size), 0)
        else:
            blurred_frame = frame_np.copy()
        
        # 创建遮罩颜色背景
        mask_background = np.full((height, width, 3), mask_color, dtype=np.uint8)
        
        # 合成最终图像
        result = np.where(eyelid_mask[:, :, np.newaxis] == 0, mask_background, blurred_frame)
        
        return self.numpy_to_tensor(result)
    
    def _create_eyelid_mask(
        self,
        height: int,
        width: int,
        blink_progress: float,
        curve_factor: float,
        edge_feather: float
    ) -> np.ndarray:
        """创建眼睑遮罩"""
        
        mask = np.ones((height, width), dtype=np.uint8) * 255
        
        # 计算眼睑闭合高度
        max_closure = height // 2
        current_closure = int(max_closure * blink_progress)
        
        if current_closure == 0:
            return mask
        
        # 创建上眼睑
        for y in range(current_closure):
            # 计算水平偏移（创建弧形效果）
            normalized_y = y / current_closure if current_closure > 0 else 0
            curve_offset = int((1.0 - normalized_y ** curve_factor) * width * 0.1)
            
            # 应用边缘羽化
            if y < edge_feather * current_closure:
                alpha = y / (edge_feather * current_closure) if edge_feather * current_closure > 0 else 1
            else:
                alpha = 1.0
            
            # 设置遮罩值
            mask[y, curve_offset:width - curve_offset] = int(255 * alpha)
        
        # 创建下眼睑
        for y in range(current_closure):
            actual_y = height - 1 - y
            normalized_y = y / current_closure if current_closure > 0 else 0
            curve_offset = int((1.0 - normalized_y ** curve_factor) * width * 0.1)
            
            # 应用边缘羽化
            if y < edge_feather * current_closure:
                alpha = y / (edge_feather * current_closure) if edge_feather * current_closure > 0 else 1
            else:
                alpha = 1.0
            
            # 设置遮罩值
            mask[actual_y, curve_offset:width - curve_offset] = int(255 * alpha)
        
        return mask