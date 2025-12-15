"""
扭曲转场效果 - 基于ComfyUI-VideoTransition的OpenCV像素位移版本
"""

import numpy as np
import torch
import cv2
from typing import Dict, Any
from .base import BaseTransition
from .registry import register_transition


@register_transition("warp", "Effects")
class WarpTransition(BaseTransition):
    """扭曲转场效果 - 基于OpenCV像素位移的扭曲转场"""
    
    def get_params(self) -> Dict[str, Any]:
        return {
            "warp_type": {
                "type": "choice",
                "default": "swirl",
                "options": ["swirl", "squeeze_h", "squeeze_v", "liquid", "wave"],
                "description": "扭曲类型"
            },
            "total_frames": {"type": "int", "default": 60, "min": 4, "max": 300},
            "fps": {"type": "int", "default": 30, "min": 15, "max": 60},
            "warp_intensity": {"type": "float", "default": 0.5, "min": 0.1, "max": 2.0},
            "warp_speed": {"type": "float", "default": 1.0, "min": 0.1, "max": 3.0},
            "max_scale": {"type": "float", "default": 1.3, "min": 1.0, "max": 3.0},
            "scale_recovery": {"type": "boolean", "default": True},
            "width": {"type": "int", "default": 640, "min": 320, "max": 1920},
            "height": {"type": "int", "default": 640, "min": 240, "max": 1080}
        }
    
    async def apply_transition(
        self,
        video1: torch.Tensor,
        video2: torch.Tensor,
        warp_type: str = "swirl",
        total_frames: int = 60,
        fps: int = 30,
        warp_intensity: float = 0.5,
        warp_speed: float = 1.0,
        max_scale: float = 1.3,
        scale_recovery: bool = True,
        width: int = 640,
        height: int = 640,
        **kwargs
    ) -> torch.Tensor:
        """应用扭曲转场效果"""
        
        frames1 = self.extract_frames(video1)
        frames2 = self.extract_frames(video2)
        
        print(f"Warp transition: {warp_type}, {total_frames} frames")
        print(f"Video frames: {len(frames1)} -> {len(frames2)}")
        
        output_frames = []
        
        for i in range(total_frames):
            progress = i / (total_frames - 1) if total_frames > 1 else 0
            
            # 获取对应的帧
            frame1 = self.get_frame_at_progress(frames1, progress)
            frame2 = self.get_frame_at_progress(frames2, progress)
            
            # 调整到目标尺寸
            frame1 = self.resize_frame(frame1, width, height)
            frame2 = self.resize_frame(frame2, width, height)
            
            # 转换为numpy数组
            frame1_np = self.tensor_to_numpy(frame1)
            frame2_np = self.tensor_to_numpy(frame2)
            
            # 应用扭曲效果 - 剪映风格
            # 第一个视频：扭曲但不缩放
            frame1_warped = self._apply_warp_effect(
                frame1_np, warp_type, warp_intensity, warp_speed, 
                progress, 1.0 - progress, is_first_video=True, 
                max_scale=max_scale, scale_recovery=scale_recovery
            )
            
            # 第二个视频：反向扭曲 + 缩放恢复
            frame2_warped = self._apply_warp_effect(
                frame2_np, warp_type, warp_intensity, warp_speed, 
                progress, progress, is_first_video=False, 
                max_scale=max_scale, scale_recovery=scale_recovery
            )
            
            # 确保两个帧的尺寸一致
            if frame1_warped.shape != frame2_warped.shape:
                frame2_warped = cv2.resize(frame2_warped, 
                                         (frame1_warped.shape[1], frame1_warped.shape[0]), 
                                         interpolation=cv2.INTER_AREA)
            
            # 混合两个扭曲后的帧 - 确保无黑色背景的平滑过渡
            alpha1, alpha2 = self._calculate_blend_weights(progress)
            
            # 使用addWeighted进行混合，确保无黑色背景
            blended = cv2.addWeighted(frame1_warped, alpha1, frame2_warped, alpha2, 0)
            
            # 转换回tensor
            blended_tensor = self.numpy_to_tensor(blended)
            output_frames.append(blended_tensor)
            
            # 显示进度
            if (i + 1) % 10 == 0 or i == total_frames - 1:
                progress_percent = (i + 1) / total_frames * 100
                print(f"Processing frames {i+1}/{total_frames} ({progress_percent:.1f}%)")
        
        return self.frames_to_tensor(output_frames)
    
    def _apply_warp_effect(self, image, warp_type, intensity, speed, progress, alpha, 
                          is_first_video=True, max_scale=1.3, scale_recovery=True):
        """应用扭曲效果到单帧图像 - 剪映风格"""
        height, width = image.shape[:2]
        
        # 创建网格
        y, x = np.indices((height, width), dtype=np.float32)
        
        # 计算时间因子
        time_factor = progress * speed * np.pi * 2
        
        # 根据扭曲类型和视频类型计算位移
        if warp_type == "swirl":
            x_offset, y_offset = self._calculate_swirl_displacement(
                x, y, width, height, intensity, time_factor, progress, is_first_video
            )
        elif warp_type == "squeeze_h":
            x_offset, y_offset = self._calculate_squeeze_displacement(
                x, y, width, height, intensity, time_factor, progress, "horizontal", is_first_video
            )
        elif warp_type == "squeeze_v":
            x_offset, y_offset = self._calculate_squeeze_displacement(
                x, y, width, height, intensity, time_factor, progress, "vertical", is_first_video
            )
        elif warp_type == "liquid":
            x_offset, y_offset = self._calculate_liquid_displacement(
                x, y, width, height, intensity, time_factor, progress, is_first_video
            )
        elif warp_type == "wave":
            x_offset, y_offset = self._calculate_wave_displacement(
                x, y, width, height, intensity, time_factor, progress, is_first_video
            )
        else:
            x_offset, y_offset = np.zeros_like(x), np.zeros_like(y)
        
        # 计算新的坐标
        x_new = x + x_offset
        y_new = y + y_offset
        
        # 确保坐标在有效范围内
        x_new = np.clip(x_new, 0, width-1)
        y_new = np.clip(y_new, 0, height-1)
        
        # 应用扭曲
        warped = cv2.remap(image, x_new, y_new, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        
        # 第二个视频：应用缩放恢复效果
        if not is_first_video and scale_recovery:
            warped = self._apply_scale_recovery(warped, progress, width, height, max_scale)
        
        # 应用透明度
        if alpha < 1.0:
            warped = (warped * alpha).astype(np.uint8)
        
        return warped
    
    def _apply_scale_recovery(self, image, progress, width, height, max_scale=1.3):
        """应用缩放恢复效果 - 使用裁切方法实现第二个视频的缩放效果"""
        h, w = image.shape[:2]
        
        # 计算缩放比例：progress=0时最大(max_scale)，progress=1时正常(1.0x)
        scale = max_scale - progress * (max_scale - 1.0)
        
        # 确保缩放值在合理范围内
        scale = max(0.8, min(scale, max_scale))
        
        # 如果不需要缩放，直接返回原图
        if abs(scale - 1.0) < 0.01:
            return image
        
        # 使用裁切方法：从中心裁切出缩放后的区域
        crop_scale = 1.0 / scale
        crop_w = int(w * crop_scale)
        crop_h = int(h * crop_scale)
        
        # 确保裁切尺寸不超过原图
        crop_w = min(crop_w, w)
        crop_h = min(crop_h, h)
        
        # 计算裁切起始位置（居中裁切）
        start_x = (w - crop_w) // 2
        start_y = (h - crop_h) // 2
        
        # 确保裁切位置在有效范围内
        start_x = max(0, min(start_x, w - crop_w))
        start_y = max(0, min(start_y, h - crop_h))
        
        # 裁切图像
        cropped = image[start_y:start_y + crop_h, start_x:start_x + crop_w]
        
        # 将裁切后的图像缩放回原始尺寸
        result = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_AREA)
        
        return result
    
    def _calculate_blend_weights(self, progress):
        """计算叠化权重 - 确保无黑色背景的平滑过渡"""
        # 确保progress在有效范围内
        progress = max(0.0, min(progress, 1.0))
        
        # 使用更平滑的过渡曲线，避免突然的切换
        # 第一个视频：从1.0平滑过渡到0.0
        alpha1 = 1.0 - progress
        
        # 第二个视频：从0.0平滑过渡到1.0
        alpha2 = progress
        
        # 应用S型曲线让过渡更自然
        def smoothstep(t):
            return 3 * t * t - 2 * t * t * t
        
        # 对alpha2应用smoothstep，让过渡更自然
        alpha2 = smoothstep(alpha2)
        alpha1 = 1.0 - alpha2
        
        # 确保权重在合理范围内，并且总和为1
        alpha1 = max(0.0, min(alpha1, 1.0))
        alpha2 = max(0.0, min(alpha2, 1.0))
        
        # 最终确保alpha总和为1，避免黑色背景
        total_alpha = alpha1 + alpha2
        if total_alpha > 0:
            alpha1 = alpha1 / total_alpha
            alpha2 = alpha2 / total_alpha
        
        return alpha1, alpha2
    
    def _calculate_swirl_displacement(self, x, y, width, height, intensity, time_factor, progress, is_first_video=True):
        """计算旋涡扭曲的位移 - 剪映风格"""
        center_x = width / 2
        center_y = height / 2
        max_radius = np.sqrt(center_x**2 + center_y**2)
        swirl_intensity = intensity * 2
        
        # 计算到中心的距离和角度
        dx = x - center_x
        dy = y - center_y
        distance = np.sqrt(dx**2 + dy**2)
        angle = np.arctan2(dy, dx)
        
        # 计算影响因子
        influence = np.where(distance > 0, 
                           np.clip(1.0 - distance / max_radius, 0, 1), 0)
        influence = influence * influence * (3 - 2 * influence)
        
        if is_first_video:
            # 第一个视频：逐渐增强的扭曲
            rotation_factor = progress
            rotation_direction = 1
        else:
            # 第二个视频：反向扭曲恢复
            rotation_factor = 1.0 - progress
            rotation_direction = -1
        
        # 计算扭转角度
        twist_angle = (distance / max_radius) * swirl_intensity * np.pi * influence * rotation_factor * rotation_direction
        
        # 计算新坐标
        cos_theta = np.cos(twist_angle)
        sin_theta = np.sin(twist_angle)
        x_new = center_x + dx * cos_theta - dy * sin_theta
        y_new = center_x + dx * sin_theta + dy * cos_theta
        
        # 计算位移
        x_offset = x_new - x
        y_offset = y_new - y
        
        return x_offset, y_offset
    
    def _calculate_squeeze_displacement(self, x, y, width, height, intensity, time_factor, progress, direction, is_first_video=True):
        """计算挤压扭曲的位移 - 剪映风格"""
        if is_first_video:
            # 第一个视频：逐渐增强的挤压
            squeeze_intensity = intensity * progress * 58
        else:
            # 第二个视频：反向挤压恢复
            squeeze_intensity = intensity * (1.0 - progress) * 58
        
        if direction == "horizontal":
            center_x = width / 2
            squeeze = np.sin((x - center_x) / width * np.pi * 3) * squeeze_intensity
            x_offset = squeeze
            y_offset = np.zeros_like(x)
        else:  # vertical
            center_y = height / 2
            squeeze = np.sin((y - center_y) / height * np.pi * 3) * squeeze_intensity
            x_offset = np.zeros_like(x)
            y_offset = squeeze
        
        return x_offset, y_offset
    
    def _calculate_liquid_displacement(self, x, y, width, height, intensity, time_factor, progress, is_first_video=True):
        """计算液体扭曲的位移 - 剪映风格"""
        if is_first_video:
            # 第一个视频：逐渐增强的液体效果
            liquid_intensity = intensity * progress * 30
        else:
            # 第二个视频：反向液体恢复
            liquid_intensity = intensity * (1.0 - progress) * 30
        
        # 多方向波动
        wave1 = np.sin(x * 0.02 + time_factor) * liquid_intensity
        wave2 = np.cos(y * 0.02 + time_factor * 0.7) * liquid_intensity * 0.8
        
        # 添加额外的液体波动层
        wave3 = np.sin(x * 0.03 + time_factor * 1.3) * liquid_intensity * 0.4
        wave4 = np.cos(y * 0.03 + time_factor * 0.5) * liquid_intensity * 0.3
        
        x_offset = wave1 + wave3
        y_offset = wave2 + wave4
        
        return x_offset, y_offset
    
    def _calculate_wave_displacement(self, x, y, width, height, intensity, time_factor, progress, is_first_video=True):
        """计算波浪扭曲的位移 - 剪映风格"""
        if is_first_video:
            # 第一个视频：逐渐增强的波浪
            wave_intensity = intensity * progress * 40
        else:
            # 第二个视频：反向波浪恢复
            wave_intensity = intensity * (1.0 - progress) * 40
        
        # 波浪形扭曲
        wave1 = np.sin(x * 0.03 + time_factor) * wave_intensity
        wave2 = np.sin(x * 0.05 + time_factor * 1.5) * wave_intensity * 0.6
        
        # 添加垂直方向的波浪
        wave3 = np.sin(y * 0.02 + time_factor * 0.8) * wave_intensity * 0.4
        
        x_offset = wave3  # 垂直波浪影响x方向
        y_offset = wave1 + wave2  # 水平波浪影响y方向
        
        return x_offset, y_offset