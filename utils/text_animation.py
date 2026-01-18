"""
文本动态效果模块

提供花字的动态效果系统，支持多种动画效果。
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
from utils.logger import Logger


class BaseTextAnimation(ABC):
    """文本动态效果基类"""

    def __init__(self):
        self.name = self.__class__.__name__
        self.category = "TextAnimation"

    @abstractmethod
    def get_params(self) -> Dict[str, Any]:
        """获取动画参数配置"""
        pass

    @abstractmethod
    def apply_animation(
        self,
        text_image: np.ndarray,
        frame_index: int,
        total_frames: int,
        fps: float,
        **kwargs
    ) -> np.ndarray:
        """
        应用动态效果

        Args:
            text_image: 文字图像 (H, W, 4) BGRA格式
            frame_index: 当前帧索引
            total_frames: 总帧数
            fps: 帧率
            **kwargs: 其他参数

        Returns:
            应用动画后的图像
        """
        pass

    def parse_color(self, color_str: str) -> Tuple[int, int, int]:
        """解析颜色字符串为RGB元组"""
        if color_str.startswith('#'):
            color_str = color_str[1:]

        if len(color_str) == 6:
            r = int(color_str[0:2], 16)
            g = int(color_str[2:4], 16)
            b = int(color_str[4:6], 16)
        else:
            r, g, b = 255, 255, 255

        return (r, g, b)


class MarqueeAnimation(BaseTextAnimation):
    """走马灯动效 - 文字从右向左滚动"""

    def get_params(self) -> Dict[str, Any]:
        return {
            "speed": {
                "type": "float",
                "default": 1.0,
                "min": 0.5,
                "max": 5.0,
                "description": "滚动速度（相对值，实际速度=值×100像素/秒）"
            },
            "direction": {
                "type": "choice",
                "default": "left",
                "options": ["left", "right", "up", "down"],
                "description": "滚动方向"
            }
        }

    def apply_animation(
        self,
        text_image: np.ndarray,
        frame_index: int,
        total_frames: int,
        fps: float,
        speed: float = 100.0,
        direction: str = "left",
        **kwargs
    ) -> np.ndarray:
        """应用走马灯效果"""
        try:
            import cv2

            height, width = text_image.shape[:2]

            # 计算偏移量（像素）- speed 是相对值，需要乘以 100
            actual_speed = speed * 100.0  # 实际速度（像素/秒）
            offset = (frame_index / fps) * actual_speed

            # 使用np.roll实现循环滚动（numpy内置函数，高效且可靠）
            if direction == "left":
                # 从右向左滚动
                shift_x = int(offset) % width
                result = np.roll(text_image, shift=-shift_x, axis=1)

            elif direction == "right":
                # 从左向右滚动
                shift_x = int(offset) % width
                result = np.roll(text_image, shift=shift_x, axis=1)

            elif direction == "up":
                # 从下向上滚动
                shift_y = int(offset) % height
                result = np.roll(text_image, shift=-shift_y, axis=0)

            elif direction == "down":
                # 从上向下滚动
                shift_y = int(offset) % height
                result = np.roll(text_image, shift=shift_y, axis=0)

            else:
                result = text_image.copy()

            return result

        except Exception as e:
            Logger.error(f"走马灯动效应用失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            return text_image


class HeartbeatAnimation(BaseTextAnimation):
    """心动动效 - 文字像心跳一样缩放"""

    def get_params(self) -> Dict[str, Any]:
        return {
            "scale_min": {
                "type": "float",
                "default": 0.9,
                "min": 0.5,
                "max": 1.0,
                "description": "最小缩放比例"
            },
            "scale_max": {
                "type": "float",
                "default": 1.1,
                "min": 1.0,
                "max": 2.0,
                "description": "最大缩放比例"
            },
            "speed": {
                "type": "float",
                "default": 1.0,
                "min": 0.5,
                "max": 5.0,
                "description": "心跳速度（次/秒）"
            }
        }

    def apply_animation(
        self,
        text_image: np.ndarray,
        frame_index: int,
        total_frames: int,
        fps: float,
        scale_min: float = 0.9,
        scale_max: float = 1.1,
        speed: float = 1.0,
        **kwargs
    ) -> np.ndarray:
        """应用心动效果"""
        try:
            import cv2

            height, width = text_image.shape[:2]

            # 计算心跳缩放比例
            time = frame_index / fps
            # 使用正弦函数模拟心跳节奏
            heartbeat = (np.sin(time * speed * 2 * np.pi) + 1) / 2  # 0-1
            scale = scale_min + (scale_max - scale_min) * heartbeat

            # 计算新尺寸
            new_width = int(width * scale)
            new_height = int(height * scale)

            # 缩放图像
            scaled = cv2.resize(text_image, (new_width, new_height), interpolation=cv2.INTER_LINEAR)

            # 创建输出图像（居中）
            result = np.zeros_like(text_image)
            start_x = (width - new_width) // 2
            start_y = (height - new_height) // 2

            # 计算实际可以复制的区域
            if start_x < 0:
                src_start_x = -start_x
                dst_start_x = 0
                copy_width = min(new_width - src_start_x, width)
            else:
                src_start_x = 0
                dst_start_x = start_x
                copy_width = min(new_width, width - start_x)

            if start_y < 0:
                src_start_y = -start_y
                dst_start_y = 0
                copy_height = min(new_height - src_start_y, height)
            else:
                src_start_y = 0
                dst_start_y = start_y
                copy_height = min(new_height, height - start_y)

            # 复制缩放后的图像
            if copy_width > 0 and copy_height > 0:
                result[dst_start_y:dst_start_y + copy_height, dst_start_x:dst_start_x + copy_width] = \
                    scaled[src_start_y:src_start_y + copy_height, src_start_x:src_start_x + copy_width]

            return result

        except Exception as e:
            Logger.error(f"心动动效应用失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            return text_image


class TextAnimationFactory:
    """文本动态效果工厂类"""

    _animations = {
        "none": None,  # 无效果
        "marquee": MarqueeAnimation,
        "heartbeat": HeartbeatAnimation
    }

    @classmethod
    def register_animation(cls, name: str, animation_class: type):
        """注册新的动态效果"""
        cls._animations[name] = animation_class
        Logger.info(f"注册动态效果: {name}")

    @classmethod
    def create_animation(cls, name: str) -> Optional[BaseTextAnimation]:
        """创建动态效果实例"""
        animation_class = cls._animations.get(name)
        if animation_class and animation_class is not None:
            return animation_class()
        return None

    @classmethod
    def get_available_animations(cls) -> Dict[str, str]:
        """获取可用的动态效果列表"""
        return {
            "none": "无效果",
            "marquee": "走马灯",
            "heartbeat": "心动",
            "ecg": "心电图"
        }

    @classmethod
    def get_animation_params(cls, name: str) -> Optional[Dict[str, Any]]:
        """获取动态效果的参数配置"""
        animation = cls.create_animation(name)
        if animation:
            return animation.get_params()
        return None


# 全局工厂实例
text_animation_factory = TextAnimationFactory()