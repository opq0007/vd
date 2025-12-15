"""
翻页转场效果 - 实现真实的翻书效果
"""

import numpy as np
import torch
import math
from typing import Dict, Any
from .base import BaseTransition
from .registry import register_transition


@register_transition("page_turn", "Effects")
class PageTurnTransition(BaseTransition):
    """翻页转场效果 - 模拟真实的翻书效果"""
    
    def get_params(self) -> Dict[str, Any]:
        return {
            "direction": {
                "type": "choice",
                "default": "right",
                "options": ["right", "left", "up", "down"],
                "description": "翻页方向"
            },
            "total_frames": {"type": "int", "default": 30, "min": 4, "max": 120},
            "fps": {"type": "int", "default": 30, "min": 15, "max": 60},
            "curl_strength": {"type": "float", "default": 1.0, "min": 0.5, "max": 2.0},
            "shadow_intensity": {"type": "float", "default": 0.6, "min": 0.0, "max": 1.0},
            "width": {"type": "int", "default": 640, "min": 320, "max": 1920},
            "height": {"type": "int", "default": 640, "min": 240, "max": 1080}
        }
    
    async def apply_transition(
        self,
        video1: torch.Tensor,
        video2: torch.Tensor,
        direction: str = "right",
        total_frames: int = 30,
        fps: int = 30,
        curl_strength: float = 1.0,
        shadow_intensity: float = 0.6,
        width: int = 640,
        height: int = 640,
        **kwargs
    ) -> torch.Tensor:
        """应用翻页转场效果"""
        
        frames1 = self.extract_frames(video1)
        frames2 = self.extract_frames(video2)
        
        output_frames = []
        
        for i in range(total_frames):
            progress = i / (total_frames - 1) if total_frames > 1 else 0
            
            frame1 = self.get_frame_at_progress(frames1, progress)
            frame2 = self.get_frame_at_progress(frames2, progress)
            
            frame1 = self.resize_frame(frame1, width, height)
            frame2 = self.resize_frame(frame2, width, height)
            
            # 应用翻页效果
            blended_frame = self._apply_page_turn_effect(
                frame1, frame2, progress, direction, curl_strength, shadow_intensity
            )
            
            output_frames.append(blended_frame)
        
        return self.frames_to_tensor(output_frames)
    
    def _apply_page_turn_effect(
        self,
        frame1: torch.Tensor,
        frame2: torch.Tensor,
        progress: float,
        direction: str,
        curl_strength: float,
        shadow_intensity: float
    ) -> torch.Tensor:
        """应用真实的翻页效果"""
        import cv2
        
        # 确保两个帧尺寸相同
        frame1, frame2 = self.ensure_same_size(frame1, frame2)
        
        f1 = self.tensor_to_numpy(frame1)
        f2 = self.tensor_to_numpy(frame2)
        height, width = f1.shape[:2]
        
        # 创建结果画布
        result = np.zeros_like(f1)
        
        # 计算翻页角度 (0到180度)
        flip_angle = progress * 180
        
        if direction == "right":
            result = self._apply_horizontal_page_turn(
                f1, f2, flip_angle, curl_strength, shadow_intensity, is_right_to_left=True
            )
        elif direction == "left":
            result = self._apply_horizontal_page_turn(
                f1, f2, flip_angle, curl_strength, shadow_intensity, is_right_to_left=False
            )
        elif direction == "up":
            result = self._apply_vertical_page_turn(
                f1, f2, flip_angle, curl_strength, shadow_intensity, is_top_to_bottom=True
            )
        elif direction == "down":
            result = self._apply_vertical_page_turn(
                f1, f2, flip_angle, curl_strength, shadow_intensity, is_top_to_bottom=False
            )
        
        return self.numpy_to_tensor(result)
    
    def _apply_horizontal_page_turn(
        self,
        f1: np.ndarray,
        f2: np.ndarray,
        flip_angle: float,
        curl_strength: float,
        shadow_intensity: float,
        is_right_to_left: bool
    ) -> np.ndarray:
        """应用水平翻页效果"""
        import cv2
        
        height, width = f1.shape[:2]
        result = np.zeros_like(f1)
        
        # 计算翻页进度
        progress = flip_angle / 180.0
        
        # 创建背景（显示第二页的内容）
        result[:] = f2
        
        # 计算翻页的分割线位置
        if is_right_to_left:
            # 从右向左翻页
            fold_x = int(width * (1 - progress))
        else:
            # 从左向右翻页
            fold_x = int(width * progress)
        
        # 确保fold_x在有效范围内
        fold_x = max(0, min(width, fold_x))
        
        if fold_x > 0 and fold_x < width:
            # 应用透视变换创建翻页效果
            if is_right_to_left:
                # 右侧部分翻页
                page_width = width - fold_x
                if page_width > 0:
                    # 创建翻页的透视变换
                    pts1 = np.float32([
                        [fold_x, 0],
                        [width, 0],
                        [width, height],
                        [fold_x, height]
                    ])
                    
                    # 计算卷曲效果
                    curl_amount = math.sin(math.radians(flip_angle)) * curl_strength * 50
                    pts2 = np.float32([
                        [fold_x, 0],
                        [width + curl_amount, curl_amount],
                        [width + curl_amount, height - curl_amount],
                        [fold_x, height]
                    ])
                    
                    # 应用透视变换
                    M = cv2.getPerspectiveTransform(pts1, pts2)
                    warped_page = cv2.warpPerspective(f1, M, (width, height), 
                                                    borderMode=cv2.BORDER_REPLICATE)
                    
                    # 创建翻页部分的遮罩
                    mask = np.zeros((height, width), dtype=np.uint8)
                    mask[:, fold_x:] = 255
                    
                    # 添加阴影效果
                    if shadow_intensity > 0:
                        shadow_mask = self._create_page_shadow_mask(
                            height, width, fold_x, flip_angle, shadow_intensity, is_right_to_left
                        )
                        warped_page = self._apply_shadow(warped_page, shadow_mask)
                    
                    # 合并翻页部分
                    result = np.where(mask[:, :, np.newaxis] > 0, warped_page, result)
                
                # 显示未翻页的部分
                if fold_x > 0:
                    result[:, :fold_x] = f1[:, :fold_x]
                    
            else:
                # 左侧部分翻页
                page_width = fold_x
                if page_width > 0:
                    # 创建翻页的透视变换
                    pts1 = np.float32([
                        [0, 0],
                        [fold_x, 0],
                        [fold_x, height],
                        [0, height]
                    ])
                    
                    # 计算卷曲效果
                    curl_amount = math.sin(math.radians(flip_angle)) * curl_strength * 50
                    pts2 = np.float32([
                        [-curl_amount, curl_amount],
                        [fold_x, 0],
                        [fold_x, height],
                        [-curl_amount, height - curl_amount]
                    ])
                    
                    # 应用透视变换
                    M = cv2.getPerspectiveTransform(pts1, pts2)
                    warped_page = cv2.warpPerspective(f1, M, (width, height), 
                                                    borderMode=cv2.BORDER_REPLICATE)
                    
                    # 创建翻页部分的遮罩
                    mask = np.zeros((height, width), dtype=np.uint8)
                    mask[:, :fold_x] = 255
                    
                    # 添加阴影效果
                    if shadow_intensity > 0:
                        shadow_mask = self._create_page_shadow_mask(
                            height, width, fold_x, flip_angle, shadow_intensity, is_right_to_left
                        )
                        warped_page = self._apply_shadow(warped_page, shadow_mask)
                    
                    # 合并翻页部分
                    result = np.where(mask[:, :, np.newaxis] > 0, warped_page, result)
                
                # 显示未翻页的部分
                if fold_x < width:
                    result[:, fold_x:] = f1[:, fold_x:]
        
        return result
    
    def _apply_vertical_page_turn(
        self,
        f1: np.ndarray,
        f2: np.ndarray,
        flip_angle: float,
        curl_strength: float,
        shadow_intensity: float,
        is_top_to_bottom: bool
    ) -> np.ndarray:
        """应用垂直翻页效果"""
        import cv2
        
        height, width = f1.shape[:2]
        result = np.zeros_like(f1)
        
        # 计算翻页进度
        progress = flip_angle / 180.0
        
        # 创建背景（显示第二页的内容）
        result[:] = f2
        
        # 计算翻页的分割线位置
        if is_top_to_bottom:
            # 从上向下翻页
            fold_y = int(height * progress)
        else:
            # 从下向上翻页
            fold_y = int(height * (1 - progress))
        
        # 确保fold_y在有效范围内
        fold_y = max(0, min(height, fold_y))
        
        if fold_y > 0 and fold_y < height:
            # 应用透视变换创建翻页效果
            if is_top_to_bottom:
                # 上部部分翻页
                page_height = fold_y
                if page_height > 0:
                    # 创建翻页的透视变换
                    pts1 = np.float32([
                        [0, 0],
                        [width, 0],
                        [width, fold_y],
                        [0, fold_y]
                    ])
                    
                    # 计算卷曲效果
                    curl_amount = math.sin(math.radians(flip_angle)) * curl_strength * 50
                    pts2 = np.float32([
                        [curl_amount, -curl_amount],
                        [width - curl_amount, -curl_amount],
                        [width, fold_y],
                        [0, fold_y]
                    ])
                    
                    # 应用透视变换
                    M = cv2.getPerspectiveTransform(pts1, pts2)
                    warped_page = cv2.warpPerspective(f1, M, (width, height), 
                                                    borderMode=cv2.BORDER_REPLICATE)
                    
                    # 创建翻页部分的遮罩
                    mask = np.zeros((height, width), dtype=np.uint8)
                    mask[:fold_y, :] = 255
                    
                    # 添加阴影效果
                    if shadow_intensity > 0:
                        shadow_mask = self._create_vertical_page_shadow_mask(
                            height, width, fold_y, flip_angle, shadow_intensity, is_top_to_bottom
                        )
                        warped_page = self._apply_shadow(warped_page, shadow_mask)
                    
                    # 合并翻页部分
                    result = np.where(mask[:, :, np.newaxis] > 0, warped_page, result)
                
                # 显示未翻页的部分
                if fold_y < height:
                    result[fold_y:, :] = f1[fold_y:, :]
                    
            else:
                # 下部部分翻页
                page_height = height - fold_y
                if page_height > 0:
                    # 创建翻页的透视变换
                    pts1 = np.float32([
                        [0, fold_y],
                        [width, fold_y],
                        [width, height],
                        [0, height]
                    ])
                    
                    # 计算卷曲效果
                    curl_amount = math.sin(math.radians(flip_angle)) * curl_strength * 50
                    pts2 = np.float32([
                        [0, fold_y],
                        [width, fold_y],
                        [width - curl_amount, height + curl_amount],
                        [curl_amount, height + curl_amount]
                    ])
                    
                    # 应用透视变换
                    M = cv2.getPerspectiveTransform(pts1, pts2)
                    warped_page = cv2.warpPerspective(f1, M, (width, height), 
                                                    borderMode=cv2.BORDER_REPLICATE)
                    
                    # 创建翻页部分的遮罩
                    mask = np.zeros((height, width), dtype=np.uint8)
                    mask[fold_y:, :] = 255
                    
                    # 添加阴影效果
                    if shadow_intensity > 0:
                        shadow_mask = self._create_vertical_page_shadow_mask(
                            height, width, fold_y, flip_angle, shadow_intensity, is_top_to_bottom
                        )
                        warped_page = self._apply_shadow(warped_page, shadow_mask)
                    
                    # 合并翻页部分
                    result = np.where(mask[:, :, np.newaxis] > 0, warped_page, result)
                
                # 显示未翻页的部分
                if fold_y > 0:
                    result[:fold_y, :] = f1[:fold_y, :]
        
        return result
    
    def _create_page_shadow_mask(
        self,
        height: int,
        width: int,
        fold_x: int,
        flip_angle: float,
        shadow_intensity: float,
        is_right_to_left: bool
    ) -> np.ndarray:
        """创建水平翻页的阴影遮罩"""
        shadow_mask = np.zeros((height, width, 3), dtype=np.float32)
        
        # 计算阴影宽度和强度
        shadow_width = int(30 * (1 - flip_angle / 180.0) + 5)
        shadow_width = max(5, min(50, shadow_width))
        
        # 创建渐变阴影
        if is_right_to_left and fold_x - shadow_width >= 0:
            for i in range(shadow_width):
                x_pos = fold_x - shadow_width + i
                if 0 <= x_pos < width:
                    alpha = (1 - i / shadow_width) * shadow_intensity
                    shadow_mask[:, x_pos] = np.array([0, 0, 0]) * alpha
        elif not is_right_to_left and fold_x + shadow_width < width:
            for i in range(shadow_width):
                x_pos = fold_x + i
                if 0 <= x_pos < width:
                    alpha = (i / shadow_width) * shadow_intensity
                    shadow_mask[:, x_pos] = np.array([0, 0, 0]) * alpha
        
        return shadow_mask
    
    def _create_vertical_page_shadow_mask(
        self,
        height: int,
        width: int,
        fold_y: int,
        flip_angle: float,
        shadow_intensity: float,
        is_top_to_bottom: bool
    ) -> np.ndarray:
        """创建垂直翻页的阴影遮罩"""
        shadow_mask = np.zeros((height, width, 3), dtype=np.float32)
        
        # 计算阴影高度和强度
        shadow_height = int(30 * (1 - flip_angle / 180.0) + 5)
        shadow_height = max(5, min(50, shadow_height))
        
        # 创建渐变阴影
        if is_top_to_bottom and fold_y + shadow_height < height:
            for i in range(shadow_height):
                y_pos = fold_y + i
                if 0 <= y_pos < height:
                    alpha = (i / shadow_height) * shadow_intensity
                    shadow_mask[y_pos, :] = np.array([0, 0, 0]) * alpha
        elif not is_top_to_bottom and fold_y - shadow_height >= 0:
            for i in range(shadow_height):
                y_pos = fold_y - shadow_height + i
                if 0 <= y_pos < height:
                    alpha = (1 - i / shadow_height) * shadow_intensity
                    shadow_mask[y_pos, :] = np.array([0, 0, 0]) * alpha
        
        return shadow_mask
    
    def _apply_shadow(self, image: np.ndarray, shadow_mask: np.ndarray) -> np.ndarray:
        """应用阴影效果到图像"""
        # 确保图像和遮罩的形状匹配
        if image.shape != shadow_mask.shape:
            return image
        
        # 将图像转换为float32以进行计算
        img_float = image.astype(np.float32)
        
        # 应用阴影
        shadowed = img_float * (1 - shadow_mask) + shadow_mask * 50
        
        # 确保值在有效范围内
        shadowed = np.clip(shadowed, 0, 255)
        
        return shadowed.astype(np.uint8)