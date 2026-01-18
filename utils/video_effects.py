"""
视频效果处理类

提供花字、插图、水印等视频效果处理功能。
"""

import os
import time
import tempfile
import numpy as np
import torch
import cv2
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

from utils.logger import Logger
from utils.file_utils import FileUtils
from utils.system_utils import SystemUtils
from utils.media_processor import MediaProcessor
from utils.font_manager import font_manager


class VideoEffectsProcessor:
    """视频效果处理类"""

    _current_job_id = None

    @staticmethod
    def parse_color(color_input) -> tuple:
        """
        解析各种格式的颜色输入

        Args:
            color_input: 颜色输入，可以是十六进制字符串、RGBA字符串、RGB字符串或元组

        Returns:
            tuple: RGB元组 (R, G, B)
        """
        try:
            Logger.info(f"parse_color - 输入: {color_input}, 类型: {type(color_input)}")
            
            if color_input is None:
                return (255, 255, 255)

            if isinstance(color_input, (tuple, list)):
                if len(color_input) >= 3:
                    # 检查是否是 Gradio 的 RGBA 格式（浮点数 0-1）
                    if all(0 <= c <= 1 for c in color_input[:3]):
                        # 转换为 0-255 的整数
                        result = tuple(int(c * 255) for c in color_input[:3])
                        Logger.info(f"parse_color - RGBA浮点数转换: {color_input} -> {result}")
                        return result
                    else:
                        # 假设已经是 0-255 的整数
                        result = tuple(int(c) for c in color_input[:3])
                        Logger.info(f"parse_color - RGB整数转换: {color_input} -> {result}")
                        return result

            if isinstance(color_input, str):
                color_input = color_input.strip().lower()
                Logger.info(f"parse_color - 字符串处理: '{color_input}'")

                if color_input.startswith('#'):
                    color_input = color_input[1:]
                    if len(color_input) == 6:
                        r = int(color_input[0:2], 16)
                        g = int(color_input[2:4], 16)
                        b = int(color_input[4:6], 16)
                        result = (r, g, b)
                        Logger.info(f"parse_color - 十六进制转换: #{color_input} -> {result}")
                        return result

                if color_input.startswith('rgb'):
                    import re
                    match = re.search(r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', color_input)
                    if match:
                        result = tuple(map(int, match.groups()))
                        Logger.info(f"parse_color - RGB字符串转换: {color_input} -> {result}")
                        return result

                if color_input.startswith('rgba'):
                    import re
                    # 匹配 RGBA 格式，支持整数和浮点数
                    match = re.search(r'rgba\s*\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)', color_input)
                    if match:
                        r, g, b, a = map(float, match.groups())
                        result = (int(r), int(g), int(b))
                        Logger.info(f"parse_color - RGBA字符串转换: {color_input} -> {result}")
                        return result

                color_map = {
                    'black': (0, 0, 0),
                    'white': (255, 255, 255),
                    'red': (255, 0, 0),
                    'green': (0, 255, 0),
                    'blue': (0, 0, 255),
                    'yellow': (255, 255, 0),
                    'cyan': (0, 255, 255),
                    'magenta': (255, 0, 255),
                    'orange': (255, 165, 0),
                    'purple': (128, 0, 128),
                }

                result = color_map.get(color_input, (255, 255, 255))
                Logger.info(f"parse_color - 颜色名称转换: '{color_input}' -> {result}")
                return result

            result = (255, 255, 255)
            Logger.info(f"parse_color - 使用默认白色: {result}")
            return result

        except Exception as e:
            Logger.warning(f"颜色解析失败: {color_input}, 使用默认白色, 错误: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            return (255, 255, 255)

    @staticmethod
    def create_text_image(
        text: str,
        font_size: int = 48,
        font_name: Optional[str] = None,
        text_color: str = '#FFFFFF',
        bg_color: str = '#000000',
        bg_alpha: int = 128,
        padding: int = 20,
        output_path: Optional[Path] = None
    ) -> np.ndarray:
        """
        创建带文字的图像

        Args:
            text: 要显示的文字
            font_size: 字体大小
            font_name: 字体名称（可选）
            text_color: 文字颜色
            bg_color: 背景颜色
            bg_alpha: 背景透明度 (0-255)
            padding: 内边距
            output_path: 输出路径（可选）

        Returns:
            np.ndarray: 图像数组
        """
        try:
            # 解析颜色
            text_rgb = VideoEffectsProcessor.parse_color(text_color)
            bg_rgb = VideoEffectsProcessor.parse_color(bg_color)

            # 创建字体
            try:
                # 使用字体管理器加载字体
                if font_name:
                    font = font_manager.load_font(font_name, font_size)
                    if font is None:
                        Logger.error(f"字体加载失败: {font_name}")
                        raise ValueError(f"无法加载字体: {font_name}")
                else:
                    # 使用默认字体
                    default_font_name = font_manager.get_default_font()
                    if default_font_name:
                        font = font_manager.load_font(default_font_name, font_size)
                        Logger.info(f"使用默认字体: {default_font_name}")
                    else:
                        Logger.error("没有可用的字体文件")
                        raise ValueError("没有可用的字体文件，请将字体文件放入 fonts 目录")

                # 验证字体对象
                if font is None:
                    raise ValueError("字体对象为 None")

                # 测试字体是否可用
                test_bbox = font.getbbox("测试")
                Logger.info(f"字体测试成功: font_name={font_name}, test_bbox={test_bbox}")

            except Exception as e:
                Logger.error(f"字体加载异常: {e}")
                import traceback
                Logger.error(traceback.format_exc())
                raise ValueError(f"字体加载失败: {e}")

            # 计算文本尺寸
            temp_img = Image.new('RGBA', (1, 1))
            temp_draw = ImageDraw.Draw(temp_img)
            bbox = temp_draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # 创建图像
            img_width = text_width + padding * 2
            img_height = text_height + padding * 2

            img = Image.new('RGBA', (img_width, img_height), (*bg_rgb, bg_alpha))
            draw = ImageDraw.Draw(img)

            # 绘制文字
            draw.text((padding, padding), text, font=font, fill=(*text_rgb, 255))

            # 保存图像
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                img.save(output_path)
                Logger.info(f"文字图像已保存: {output_path}")

            # 转换为numpy数组
            img_array = np.array(img)

            return img_array

        except Exception as e:
            Logger.error(f"创建文字图像失败: {e}")
            raise

    @staticmethod
    def add_watermark(
        image: np.ndarray,
        watermark_text: str,
        position: str = 'bottom_right',
        opacity: float = 0.5,
        font_size: int = 24
    ) -> np.ndarray:
        """
        为图像添加水印

        Args:
            image: 输入图像
            watermark_text: 水印文字
            position: 水印位置 (top_left, top_right, bottom_left, bottom_right, center)
            opacity: 透明度 (0-1)
            font_size: 字体大小

        Returns:
            np.ndarray: 带水印的图像
        """
        try:
            # 创建PIL图像
            img_pil = Image.fromarray(image)
            overlay = Image.new('RGBA', img_pil.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)

            # 加载字体
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()

            # 计算水印位置
            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            x, y = 0, 0
            if position == 'top_left':
                x, y = 10, 10
            elif position == 'top_right':
                x, y = img_pil.width - text_width - 10, 10
            elif position == 'bottom_left':
                x, y = 10, img_pil.height - text_height - 10
            elif position == 'bottom_right':
                x, y = img_pil.width - text_width - 10, img_pil.height - text_height - 10
            elif position == 'center':
                x, y = (img_pil.width - text_width) // 2, (img_pil.height - text_height) // 2

            # 绘制水印
            alpha = int(255 * opacity)
            draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, alpha))

            # 合并图像
            watermarked = Image.alpha_composite(img_pil.convert('RGBA'), overlay)

            return np.array(watermarked)

        except Exception as e:
            Logger.error(f"添加水印失败: {e}")
            return image

    @staticmethod
    def apply_filter(image: np.ndarray, filter_type: str = 'none', intensity: float = 1.0) -> np.ndarray:
        """
        应用滤镜效果

        Args:
            image: 输入图像
            filter_type: 滤镜类型 (none, grayscale, sepia, blur, brightness, contrast)
            intensity: 强度 (0-2)

        Returns:
            np.ndarray: 处理后的图像
        """
        try:
            if filter_type == 'none':
                return image

            img_pil = Image.fromarray(image)

            if filter_type == 'grayscale':
                img_pil = img_pil.convert('L').convert('RGB')

            elif filter_type == 'sepia':
                img_array = np.array(img_pil)
                r = img_array[:, :, 0]
                g = img_array[:, :, 1]
                b = img_array[:, :, 2]

                sepia_r = np.clip(0.393 * r + 0.769 * g + 0.189 * b, 0, 255)
                sepia_g = np.clip(0.349 * r + 0.686 * g + 0.168 * b, 0, 255)
                sepia_b = np.clip(0.272 * r + 0.534 * g + 0.131 * b, 0, 255)

                img_array = np.dstack((sepia_r, sepia_g, sepia_b))
                img_pil = Image.fromarray(img_array.astype(np.uint8))

            elif filter_type == 'blur':
                from PIL import ImageFilter
                blur_radius = int(10 * intensity)
                img_pil = img_pil.filter(ImageFilter.GaussianBlur(radius=blur_radius))

            elif filter_type == 'brightness':
                factor = int(255 * (intensity - 1))
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Brightness(img_pil)
                img_pil = enhancer.enhance(intensity)

            elif filter_type == 'contrast':
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Contrast(img_pil)
                img_pil = enhancer.enhance(intensity)

            return np.array(img_pil)

        except Exception as e:
            Logger.error(f"应用滤镜失败: {e}")
            return image

    @staticmethod
    def time_to_seconds(time_str: str) -> float:
        """
        将时间字符串转换为秒数
        Args:
            time_str: 时间字符串，格式为 "HH:MM:SS" 或 "MM:SS" 或 "SS"

        Returns:
            float: 秒数
        """
        parts = time_str.split(':')
        if len(parts) == 3:
            hours, minutes, seconds = map(float, parts)
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:
            minutes, seconds = map(float, parts)
            return minutes * 60 + seconds
        else:
            return float(time_str)

    @staticmethod
    def check_position_overlap(x1: int, y1: int, w1: int, h1: int,
                              x2: int, y2: int, w2: int, h2: int) -> bool:
        """
        检测两个矩形区域是否重叠

        Args:
            x1, y1, w1, h1: 第一个矩形的位置和尺寸
            x2, y2, w2, h2: 第二个矩形的位置和尺寸

        Returns:
            bool: 是否重叠
        """
        # 检查两个矩形是否不重叠
        no_overlap = (x1 + w1 <= x2) or (x2 + w2 <= x1) or (y1 + h1 <= y2) or (y2 + h2 <= y1)
        return not no_overlap

    @staticmethod
    def parse_timing_config(timing_type: str, start_frame: int, end_frame: int,
                           start_time: str, end_time: str, fps: float = 30.0) -> tuple:
        """
        解析时机配置，返回开始和结束时间（秒）
        Args:
            timing_type: "帧数范围" 或 "时间戳范围"
            start_frame: 起始帧
            end_frame: 结束帧
            start_time: 起始时间字符串
            end_time: 结束时间字符串
            fps: 帧率

        Returns:
            (start_seconds, end_seconds)
        """
        if timing_type == "帧数范围":
            start_seconds = start_frame / fps
            end_seconds = end_frame / fps
        else:  # 时间戳范围
            start_seconds = VideoEffectsProcessor.time_to_seconds(start_time)
            end_seconds = VideoEffectsProcessor.time_to_seconds(end_time)

        return start_seconds, end_seconds

    @staticmethod
    def create_gradient_text_image(
        text: str,
        font_size: int,
        font_name: str = None,
        gradient_type: str = "horizontal",
        color_start: tuple = (255, 0, 0),
        color_end: tuple = (0, 0, 255),
        bg_color: tuple = None,
        stroke_enabled: bool = False,
        stroke_color: tuple = (0, 0, 0),
        stroke_width: int = 2
    ) -> np.ndarray:
        """
        使用Pillow创建渐变色文字图像

        Args:
            text: 要显示的文字
            font_size: 字体大小
            font_name: 字体名称
            gradient_type: 渐变类型 ("horizontal", "vertical", "diagonal")
            color_start: 起始颜色 (R, G, B)
            color_end: 结束颜色 (R, G, B)
            bg_color: 背景颜色 (R, G, B)，None表示透明
            stroke_enabled: 是否启用描边
            stroke_color: 描边颜色 (R, G, B)
            stroke_width: 描边宽度

        Returns:
            渐变色文字图像数组
        """
        try:
            from PIL import Image, ImageDraw, ImageFont

            # 确保文本是字符串类型
            if not isinstance(text, str):
                text = str(text)

            if not text or not text.strip():
                Logger.error(f"文本为空或只包含空白字符: '{text}'")
                raise ValueError("文本内容不能为空")

            Logger.info(f"创建渐变色文字图像: text='{text}', font_size={font_size}, gradient_type={gradient_type}")

            # 创建字体
            try:
                if font_name:
                    font = font_manager.load_font(font_name, font_size)
                    if font is not None:
                        Logger.info(f"使用 font_manager 加载字体: {font_name}")
                    else:
                        if Path(font_name).exists():
                            font = ImageFont.truetype(font_name, font_size)
                        else:
                            font = ImageFont.truetype(font_name, font_size)
                else:
                    default_font_name = font_manager.get_default_font()
                    if default_font_name:
                        font = font_manager.load_font(default_font_name, font_size)
                    else:
                        font_names = ['simhei.ttf', 'msyh.ttc', 'simhei', 'Microsoft YaHei']
                        font = None
                        for fn in font_names:
                            try:
                                font = ImageFont.truetype(fn, font_size)
                                break
                            except:
                                continue
                        if font is None:
                            font = ImageFont.load_default()

                if font is None:
                    raise ValueError("字体对象为 None")

            except Exception as e:
                Logger.error(f"字体加载异常: {e}")
                raise ValueError(f"字体加载失败: {e}")

            # 计算文本尺寸
            temp_img = Image.new('RGBA', (1, 1))
            temp_draw = ImageDraw.Draw(temp_img)
            bbox = temp_draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            Logger.info(f"文本尺寸: {text_width}x{text_height}")

            # 创建图像
            if bg_color is None:
                img = Image.new('RGBA', (text_width, text_height), (0, 0, 0, 0))
            else:
                img = Image.new('RGBA', (text_width, text_height), (*bg_color, 255))

            draw = ImageDraw.Draw(img)

            # 绘制描边
            if stroke_enabled and stroke_width > 0:
                Logger.info(f"绘制描边: stroke_enabled={stroke_enabled}, stroke_color={stroke_color}, stroke_width={stroke_width}")
                for dx in range(-stroke_width, stroke_width + 1):
                    for dy in range(-stroke_width, stroke_width + 1):
                        if dx == 0 and dy == 0:
                            continue
                        draw.text((dx, dy), text, font=font, fill=(*stroke_color, 255))

            # 创建渐变色文字
            # 1. 首先绘制一个白色的文字模板
            temp_white = Image.new('L', (text_width, text_height), 0)
            white_draw = ImageDraw.Draw(temp_white)
            white_draw.text((0, 0), text, font=font, fill=255)

            # 2. 创建渐变色背景
            gradient = np.zeros((text_height, text_width, 3), dtype=np.uint8)

            for y in range(text_height):
                for x in range(text_width):
                    # 计算渐变比例
                    if gradient_type == "horizontal":
                        ratio = x / text_width if text_width > 0 else 0
                    elif gradient_type == "vertical":
                        ratio = y / text_height if text_height > 0 else 0
                    elif gradient_type == "diagonal":
                        ratio = (x + y) / (text_width + text_height) if (text_width + text_height) > 0 else 0
                    else:
                        ratio = 0

                    # 线性插值计算颜色
                    r = int(color_start[0] + (color_end[0] - color_start[0]) * ratio)
                    g = int(color_start[1] + (color_end[1] - color_start[1]) * ratio)
                    b = int(color_start[2] + (color_end[2] - color_start[2]) * ratio)

                    gradient[y, x] = [r, g, b]

            # 3. 将渐变色应用到文字模板上
            gradient_img = Image.fromarray(gradient, mode='RGB')
            alpha = temp_white
            gradient_with_alpha = Image.composite(gradient_img, Image.new('RGBA', gradient_img.size, (0, 0, 0, 0)), alpha)

            # 4. 将渐变色文字绘制到最终图像上
            img.paste(gradient_with_alpha, (0, 0), gradient_with_alpha.split()[-1])

            # 转换为numpy数组
            img_array = np.array(img)

            # 转换为OpenCV格式（BGRA）
            if len(img_array.shape) == 3 and img_array.shape[2] == 4:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGRA)

            Logger.info(f"渐变色文字图像创建成功: shape={img_array.shape}")
            return img_array

        except Exception as e:
            Logger.error(f"创建渐变色文字图像失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            raise

    @staticmethod
    def create_text_image(text: str, font_size: int, font_name: str = None,
                         text_color: tuple = (255, 255, 255),
                         bg_color: tuple = None,
                         stroke_enabled: bool = False,
                         stroke_color: tuple = (0, 0, 0),
                         stroke_width: int = 2) -> np.ndarray:
        """
        使用Pillow创建文字图像
        Args:
            text: 要显示的文字
            font_size: 字体大小
            font_name: 字体名称
            text_color: 文字颜色 (R, G, B)
            bg_color: 背景颜色 (R, G, B)，None表示透明
            stroke_enabled: 是否启用描边
            stroke_color: 描边颜色 (R, G, B)
            stroke_width: 描边宽度

        Returns:
            文字图像数组
        """
        try:
            # 确保文本是字符串类型
            if not isinstance(text, str):
                text = str(text)

            # 检查文本是否为空或只包含空白字符
            if not text or not text.strip():
                Logger.error(f"文本为空或只包含空白字符: '{text}'")
                raise ValueError("文本内容不能为空")

            Logger.info(f"创建文字图像: text='{text}', font_size={font_size}, font_name={font_name}")

            # 创建字体
            try:
                # 优先使用 font_manager 加载字体
                if font_name:
                    font = font_manager.load_font(font_name, font_size)
                    if font is not None:
                        Logger.info(f"使用 font_manager 加载字体: {font_name}")
                    else:
                        Logger.warning(f"font_manager 加载字体失败: {font_name}, 尝试直接加载")
                        # 尝试直接加载
                        if Path(font_name).exists():
                            font = ImageFont.truetype(font_name, font_size)
                        else:
                            # 尝试作为系统字体加载
                            font = ImageFont.truetype(font_name, font_size)
                else:
                    # 使用默认字体
                    default_font_name = font_manager.get_default_font()
                    if default_font_name:
                        font = font_manager.load_font(default_font_name, font_size)
                        Logger.info(f"使用默认字体: {default_font_name}")
                    else:
                        Logger.warning("没有可用的字体文件，尝试使用系统字体")
                        # 尝试使用系统字体
                        font_names = ['simhei.ttf', 'msyh.ttc', 'simhei', 'Microsoft YaHei']
                        font = None
                        for fn in font_names:
                            try:
                                font = ImageFont.truetype(fn, font_size)
                                Logger.info(f"成功加载系统字体: {fn}")
                                break
                            except:
                                continue
                        if font is None:
                            font = ImageFont.load_default()
                            Logger.warning("使用默认字体（可能不支持中文）")

                # 验证字体对象
                if font is None:
                    raise ValueError("字体对象为 None")

            except Exception as e:
                Logger.error(f"字体加载异常: {e}")
                import traceback
                Logger.error(traceback.format_exc())
                raise ValueError(f"字体加载失败: {e}")

            # 计算文本尺寸
            temp_img = Image.new('RGBA', (1, 1))
            temp_draw = ImageDraw.Draw(temp_img)
            bbox = temp_draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            Logger.info(f"文本尺寸: {text_width}x{text_height}")

            # 创建图像 - 参考测试文件的方法
            if bg_color is None:
                # 透明背景
                img = Image.new('RGBA', (text_width, text_height), (0, 0, 0, 0))
            else:
                # 有背景色
                img = Image.new('RGBA', (text_width, text_height), (*bg_color, 255))

            draw = ImageDraw.Draw(img)

            # 绘制描边
            if stroke_enabled and stroke_width > 0:
                # 在多个方向绘制描边
                Logger.info(f"绘制描边: stroke_enabled={stroke_enabled}, stroke_color={stroke_color}, stroke_width={stroke_width}")
                for dx in range(-stroke_width, stroke_width + 1):
                    for dy in range(-stroke_width, stroke_width + 1):
                        if dx == 0 and dy == 0:
                            continue
                        draw.text((dx, dy), text, font=font, fill=(*stroke_color, 255))

            # 绘制文字 - 参考测试文件的方法
            try:
                # 使用 fill 参数指定颜色，格式为 (R, G, B, A)
                Logger.info(f"绘制文字: text='{text}', text_color={text_color}, fill=(*text_color, 255)={(*text_color, 255)}")
                draw.text((0, 0), text, font=font, fill=(*text_color, 255))
                Logger.info(f"文字绘制成功: text='{text}', color={text_color}")
            except Exception as draw_error:
                Logger.error(f"文字绘制失败: {draw_error}")
                import traceback
                Logger.error(traceback.format_exc())
                raise

            # 保存原始PIL图像用于调试（在颜色空间转换之前）
            try:
                debug_dir = Path(__file__).parent.parent / "debug"
                debug_dir.mkdir(exist_ok=True)
                debug_pil_path = debug_dir / "flower_text_pil_debug.png"
                # 直接保存 PIL 图像，保留透明通道
                img.save(debug_pil_path)
                Logger.info(f"原始PIL图像已保存: {debug_pil_path}")

                # 检查图像内容
                img_array_check = np.array(img)
                non_zero_pixels = np.count_nonzero(img_array_check[:, :, :3])
                total_pixels = img_array_check.shape[0] * img_array_check.shape[1]
                Logger.info(f"图像内容统计: 非零像素={non_zero_pixels}/{total_pixels} ({non_zero_pixels/total_pixels*100:.2f}%)")
            except Exception as save_error:
                Logger.warning(f"保存原始PIL图像失败: {save_error}")

            # 转换为numpy数组
            img_array = np.array(img)

            # 检查透明度
            if len(img_array.shape) == 3 and img_array.shape[2] == 4:
                alpha_mean = np.mean(img_array[:, :, 3])
                Logger.info(f"文字图像透明度统计: shape={img_array.shape}, alpha_mean={alpha_mean:.2f}")
                if alpha_mean < 10:
                    Logger.warning(f"文字图像透明度过低，可能无法显示: alpha_mean={alpha_mean:.2f}")

            # 转换为OpenCV格式（BGRA或BGR）
            if len(img_array.shape) == 3 and img_array.shape[2] == 4:
                # RGBA转BGRA（交换R和B通道）
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGRA)
            elif len(img_array.shape) == 3 and img_array.shape[2] == 3:
                # RGB转BGR
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

            return img_array

        except Exception as e:
            Logger.error(f"创建文字图像失败: {e}")
            raise

    @staticmethod
    def load_image(image_path: str, target_size: tuple = None, remove_bg: bool = False, output_dir: Optional[Path] = None) -> np.ndarray:
        """
        加载图片
        Args:
            image_path: 图片路径或URL
            target_size: 目标尺寸 (width, height)
            remove_bg: 是否移除背景
            output_dir: 输出目录，用于保存移除背景后的图片

        Returns:
            图片数组
        """
        try:
            Logger.info(f"load_image - image_path: {image_path}, remove_bg: {remove_bg}, target_size: {target_size}, output_dir: {output_dir}")

            # 如果是URL，先下载
            if FileUtils.is_url(image_path):
                temp_dir = Path(tempfile.gettempdir()) / "video_effects"
                temp_dir.mkdir(exist_ok=True)
                temp_image = temp_dir / f"temp_image_{int(time.time())}.jpg"
                MediaProcessor.download_from_url(image_path, temp_image)
                image_path = str(temp_image)
                Logger.info(f"Image downloaded from URL: {image_path}")

            # 如果需要移除背景
            if remove_bg:
                try:
                    Logger.info(f"Starting background removal for: {image_path}")
                    processed_path = VideoEffectsProcessor._remove_background(image_path, output_dir)
                    image_path = str(processed_path)
                    Logger.info(f"Background removed, using processed image: {image_path}")
                except Exception as e:
                    Logger.error(f"Background removal failed, using original image: {e}")
                    import traceback
                    Logger.error(traceback.format_exc())

            # 使用OpenCV加载图片以保持颜色一致性
            # 对于移除背景的PNG图片，需要使用IMREAD_UNCHANGED来保留透明通道
            # 使用 numpy.fromfile 和 cv2.imdecode 来支持中文路径
            if remove_bg and image_path.endswith('.png'):
                Logger.info(f"Loading PNG with alpha channel: {image_path}")
                img_array = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
                Logger.info(f"PNG loaded, shape: {img_array.shape if img_array is not None else None}")
            else:
                Logger.info(f"Loading standard image: {image_path}")
                img_array = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
                Logger.info(f"Image loaded, shape: {img_array.shape if img_array is not None else None}")

            if img_array is None:
                Logger.error(f"OpenCV failed to load image: {image_path}")
                # 如果OpenCV失败，尝试使用PIL
                img = Image.open(image_path)
                Logger.info(f"PIL loaded image, mode: {img.mode}")
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img_array = np.array(img)
                # PIL加载的是RGB，OpenCV需要BGR
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                Logger.info(f"Converted to BGR, shape: {img_array.shape}")

            # 调整尺寸（使用OpenCV以保持颜色）
            if target_size:
                Logger.info(f"Resizing image to: {target_size}")
                img_array = cv2.resize(img_array, target_size, interpolation=cv2.INTER_AREA)
                Logger.info(f"Resized, shape: {img_array.shape}")

            # 确保正确的颜色格式
            if len(img_array.shape) == 3:
                if img_array.shape[2] == 3:
                    # 已经是BGR格式，直接返回
                    Logger.info(f"Returning BGR image: {img_array.shape}")
                    return img_array
                elif img_array.shape[2] == 4:
                    # BGRA格式，保持透明通道
                    # 保持BGRA格式，在后续处理中正确转换颜色
                    Logger.info(f"Returning BGRA image: {img_array.shape}")
                    return img_array
            else:
                # 转换为3通道BGR
                if len(img_array.shape) == 2:
                    # 灰度图转为BGR
                    Logger.info(f"Converting grayscale to BGR")
                    return cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)

            return img_array

        except ImportError:
            Logger.error("OpenCV or PIL not installed")
            return None
        except Exception as e:
            Logger.error(f"Failed to load image: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            return None

    @staticmethod
    def _remove_background(image_path: str, output_dir: Optional[Path] = None) -> Path:
        """
        移除图片背景（基于rmbg.py实现，优化版本）
        Args:
            image_path: 图片路径
            output_dir: 输出目录，如果为None则保存在原文件同目录

        Returns:
            处理后的图片路径
        """
        try:
            Logger.info(f"_remove_background - 开始处理: {image_path}")

            # 检查rmbg模型是否存在
            rmbg_model_path = os.path.join(os.path.dirname(__file__), "..", "models", "rmbg-1.4.onnx")
            Logger.info(f"rmbg model path: {rmbg_model_path}, exists: {os.path.exists(rmbg_model_path)}")

            if not os.path.exists(rmbg_model_path):
                Logger.warning("rmbg model not found, skipping background removal")
                return Path(image_path)

            import onnxruntime as ort
            Logger.info("onnxruntime imported successfully")

            # 加载模型
            sess = ort.InferenceSession(rmbg_model_path, providers=["CPUExecutionProvider"])
            Logger.info("rmbg model loaded successfully")

            # 加载原始图片并保存原始尺寸
            original_img = Image.open(image_path).convert("RGB")
            original_size = original_img.size
            Logger.info(f"Original image loaded: {original_size}")

            # 调整图片尺寸到模型要求的 1024x1024
            if original_img.size != (1024, 1024):
                model_input_img = original_img.resize((1024, 1024), Image.LANCZOS)
                Logger.info(f"Image resized to: (1024, 1024) for model input")
            else:
                model_input_img = original_img

            # 预处理
            img = np.array(model_input_img).astype(np.float32)
            img = img.transpose(2, 0, 1) / 255.0
            mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
            std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
            img = (img - mean[:, None, None]) / std[:, None, None]
            img = img.astype(np.float32)  # 确保是 float32 类型
            img = img[None, ...]
            Logger.info(f"Image preprocessed, shape: {img.shape}, dtype: {img.dtype}")

            # 推理
            outputs = sess.run(["output"], {"input": img})
            mask = outputs[0][0][0]
            Logger.info(f"Mask generated, shape: {mask.shape}, min: {mask.min()}, max: {mask.max()}")

            # 后处理
            mask = (mask * 255).astype(np.uint8)
            mask_img = Image.fromarray(mask)

            # 将 mask 调整回原始图片尺寸
            if mask_img.size != original_size:
                mask_img = mask_img.resize(original_size, Image.LANCZOS)
                Logger.info(f"Mask resized from {mask_img.size} to {original_size}")

            # 应用 mask 到原始图片
            original_img.putalpha(mask_img)
            Logger.info("Alpha channel applied")

            # 确定输出路径
            if output_dir is None:
                output_dir = Path(image_path).parent
            else:
                output_dir = Path(output_dir)

            output_dir.mkdir(parents=True, exist_ok=True)
            output_filename = f"{Path(image_path).stem}_rmbg.png"
            output_path = output_dir / output_filename

            # 保存结果
            original_img.save(output_path)
            Logger.info(f"Background removed image saved: {output_path}")

            return output_path

        except Exception as e:
            Logger.error(f"Background removal failed: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            return Path(image_path)

    @staticmethod
    def apply_watermark_effect(frame: np.ndarray, watermark_img: np.ndarray,
                              position: str, frame_index: int, total_frames: int) -> np.ndarray:
        """
        应用水印效果
        Args:
            frame: 当前帧
            watermark_img: 水印图像
            position: 位置类型
            frame_index: 当前帧索引
            total_frames: 总帧数

        Returns:
            处理后的帧
        """
        h, w = frame.shape[:2]
        wh, ww = watermark_img.shape[:2]

        # 计算位置
        if position == "半透明浮动":
            # 半透明浮动效果
            import math
            # 水平浮动
            x = int((w - ww) // 2 + math.sin(frame_index * 0.05) * (w - ww) // 3)
            # 垂直浮动
            y = int((h - wh) // 2 + math.cos(frame_index * 0.03) * (h - wh) // 4)
        elif position == "斜向移动":
            # 斜向移动效果
            progress = (frame_index % 200) / 200.0  # 200帧一个循环
            x = int(progress * (w + ww) - ww)
            y = int(progress * (h + wh) - wh)

        else:
            # 默认位置
            x, y = w - ww - 20, h - wh - 20

        # 确保位置在有效范围内
        x = max(0, min(x, w - ww))
        y = max(0, min(y, h - wh))

        # 叠加水印
        try:
            if watermark_img.shape[2] == 4:  # RGBA
                # 处理透明度
                alpha = watermark_img[:, :, 3] / 255.0

                # 根据效果类型调整透明度
                if position == "半透明浮动":
                    alpha *= 0.5  # 降低透明度

                for c in range(3):
                    frame[y:y+wh, x:x+ww, c] = (
                        alpha * watermark_img[:, :, c] +
                        (1 - alpha) * frame[y:y+wh, x:x+ww, c]
                    )
            else:
                frame[y:y+wh, x:x+ww] = watermark_img
        except:
            pass

        return frame

    @staticmethod
    def apply_video_effects(input_path: Path, output_path: Path,
                           flower_config: dict = None,
                           image_config: dict = None,
                           video_config: dict = None,
                           watermark_config: dict = None) -> bool:
        """
        使用OpenCV应用视频效果
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            flower_config: 花字配置
            image_config: 插图配置
            video_config: 插视频配置
            watermark_config: 水印配置

        Returns:
            是否成功
        """
        try:
            # 检查是否有效果需要应用
            has_effects = flower_config or image_config or video_config or watermark_config
            if not has_effects:
                import shutil
                shutil.copy2(input_path, output_path)
                return True

            # 打开视频
            cap = cv2.VideoCapture(str(input_path))
            if not cap.isOpened():
                raise Exception(f"Cannot open video: {input_path}")

            # 获取视频信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            Logger.info(f"视频信息: {width}x{height}, {fps}fps, {total_frames}帧")

            # 创建视频写入器 - 尝试多个编码器以确保兼容性
            encoders_to_try = [
                ('XVID', 'XVID'),  # XVID编码器，兼容性好
                ('MP4V', 'MP4V'),  # MP4编码器
                ('MJPG', 'MJPG'),  # MJPEG编码器
                ('avc1', 'avc1'),  # AVC/H.264编码器
            ]

            out = None
            successful_encoder = None
            for encoder_name, fourcc_code in encoders_to_try:
                try:
                    fourcc = cv2.VideoWriter_fourcc(*fourcc_code)
                    test_out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
                    if test_out.isOpened():
                        test_out.release()
                        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
                        successful_encoder = encoder_name
                        Logger.info(f"Using video encoder: {encoder_name}")
                        break
                except Exception as e:
                    Logger.warning(f"Failed to use encoder {encoder_name}: {e}")
                    continue

            if out is None:
                # 如果所有编码器都失败，尝试使用默认编码器
                try:
                    out = cv2.VideoWriter(str(output_path), -1, fps, (width, height))
                    successful_encoder = "default"
                    Logger.info("Using default video encoder")
                except Exception as e:
                    Logger.error(f"Failed to initialize any video encoder: {e}")
                    raise Exception("无法初始化视频编码器")

            # 预处理效果资源
            flower_img = None
            flower_animation = None
            if flower_config and flower_config.get('text'):
                # 获取颜色模式
                color_mode = flower_config.get('color_mode', '单色')

                # 获取描边设置
                stroke_enabled = flower_config.get('stroke_enabled', False)
                raw_stroke_color = flower_config.get('stroke_color', (0, 0, 0))
                Logger.info(f"花字配置 - 原始描边颜色值: {raw_stroke_color}, 类型: {type(raw_stroke_color)}")
                stroke_color = VideoEffectsProcessor.parse_color(raw_stroke_color)
                Logger.info(f"花字描边颜色: {raw_stroke_color} -> {stroke_color}")
                stroke_width = flower_config.get('stroke_width', 2)

                # 根据颜色模式创建花字图像
                if color_mode == '渐变色':
                    # 渐变色模式
                    gradient_type = flower_config.get('gradient_type', '水平渐变')
                    gradient_type_map = {
                        '水平渐变': 'horizontal',
                        '垂直渐变': 'vertical',
                        '对角渐变': 'diagonal'
                    }
                    gradient_type_en = gradient_type_map.get(gradient_type, 'horizontal')

                    raw_color_start = flower_config.get('color_start', (255, 0, 0))
                    raw_color_end = flower_config.get('color_end', (0, 0, 255))
                    color_start = VideoEffectsProcessor.parse_color(raw_color_start)
                    color_end = VideoEffectsProcessor.parse_color(raw_color_end)

                    Logger.info(f"创建渐变色花字: gradient_type={gradient_type_en}, color_start={color_start}, color_end={color_end}")

                    flower_img = VideoEffectsProcessor.create_gradient_text_image(
                        flower_config['text'],
                        flower_config['size'],
                        flower_config['font'],
                        gradient_type_en,
                        color_start,
                        color_end,
                        None,  # 透明背景
                        stroke_enabled,
                        stroke_color,
                        stroke_width
                    )
                else:
                    # 单色模式
                    raw_text_color = flower_config.get('color', (255, 255, 255))
                    Logger.info(f"花字配置 - 原始颜色值: {raw_text_color}, 类型: {type(raw_text_color)}")
                    text_color = VideoEffectsProcessor.parse_color(raw_text_color)
                    Logger.info(f"花字文字颜色: {raw_text_color} -> {text_color}")

                    flower_img = VideoEffectsProcessor.create_text_image(
                        flower_config['text'],
                        flower_config['size'],
                        flower_config['font'],
                        text_color,
                        None,  # 透明背景
                        stroke_enabled,
                        stroke_color,
                        stroke_width
                    )

                if flower_img is not None:
                    Logger.info(f"花字图像创建成功: shape={flower_img.shape}, dtype={flower_img.dtype}")

                    # 保存花字图像用于调试
                    try:
                        debug_dir = Path(output_path).parent / "debug"
                        debug_dir.mkdir(exist_ok=True)
                        debug_img_path = debug_dir / "flower_text_debug.png"

                        # 使用 PIL 保存以保留透明通道
                        if flower_img.shape[2] == 4:  # BGRA
                            # 转换为 RGBA
                            flower_img_rgba = cv2.cvtColor(flower_img, cv2.COLOR_BGRA2RGBA)
                            pil_img = Image.fromarray(flower_img_rgba)
                        else:  # BGR
                            flower_img_rgb = cv2.cvtColor(flower_img, cv2.COLOR_BGR2RGB)
                            pil_img = Image.fromarray(flower_img_rgb)

                        pil_img.save(debug_img_path)
                        Logger.info(f"花字调试图像已保存: {debug_img_path}")
                    except Exception as save_error:
                        Logger.warning(f"保存花字调试图像失败: {save_error}")
                        import traceback
                        Logger.error(traceback.format_exc())

                    # 初始化动态效果
                    animation_enabled = flower_config.get('animation_enabled', False)
                    if animation_enabled:
                        animation_type = flower_config.get('animation_type', '无效果')
                        animation_type_map = {
                            '无效果': 'none',
                            '走马灯': 'marquee',
                            '心动': 'heartbeat'
                        }
                        animation_type_en = animation_type_map.get(animation_type, 'none')

                        if animation_type_en != 'none':
                            from utils.text_animation import text_animation_factory
                            flower_animation = text_animation_factory.create_animation(animation_type_en)
                            if flower_animation:
                                pass  # 动态效果已初始化
                            else:
                                Logger.warning(f"无法创建动态效果: {animation_type}")
                else:
                    Logger.error("花字图像创建失败")
            overlay_img = None
            if image_config and image_config.get('path'):
                # 获取任务目录用于保存处理后的图片
                job_dir = output_path.parent
                overlay_img = VideoEffectsProcessor.load_image(
                    image_config['path'],
                    (image_config['width'], image_config['height']),
                    image_config.get('remove_bg', False),
                    job_dir
                )

            # 插视频预处理
            video_cap = None
            if video_config and video_config.get('path'):
                video_path = Path(video_config['path'])
                if video_path.exists():
                    video_cap = cv2.VideoCapture(str(video_path))
                    if video_cap.isOpened():
                        video_fps = video_cap.get(cv2.CAP_PROP_FPS)
                        video_total_frames = int(video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        Logger.info(f"插视频已加载: {video_path}, {video_fps}fps, {video_total_frames}帧")
                    else:
                        Logger.warning(f"无法打开插视频文件: {video_path}")
                        video_cap = None
                else:
                    Logger.warning(f"插视频文件不存在: {video_path}")

            watermark_img = None
            if watermark_config and watermark_config.get('text'):
                # 获取文字颜色，支持多种格式
                raw_watermark_color = watermark_config.get('color', (255, 255, 255))
                text_color = VideoEffectsProcessor.parse_color(raw_watermark_color)
                Logger.info(f"水印文字颜色: {raw_watermark_color} -> {text_color}")
                watermark_img = VideoEffectsProcessor.create_text_image(
                    watermark_config['text'],
                    watermark_config['size'],
                    watermark_config['font'],
                    text_color,
                    None  # 透明背景
                )

            # 解析时机配置
            flower_start, flower_end = (0, 0)
            if flower_config:
                flower_start, flower_end = VideoEffectsProcessor.parse_timing_config(
                    flower_config['timing_type'],
                    flower_config['start_frame'],
                    flower_config['end_frame'],
                    flower_config['start_time'],
                    flower_config['end_time'],
                    fps
                )
                Logger.info(f"花字时机配置: {flower_start}s - {flower_end}s (类型: {flower_config.get('timing_type')})")

            overlay_start, overlay_end = (0, 0)
            if image_config:
                overlay_start, overlay_end = VideoEffectsProcessor.parse_timing_config(
                    image_config['timing_type'],
                    image_config['start_frame'],
                    image_config['end_frame'],
                    image_config['start_time'],
                    image_config['end_time'],
                    fps
                )

            watermark_start, watermark_end = (0, 0)
            if watermark_config:
                watermark_start, watermark_end = VideoEffectsProcessor.parse_timing_config(
                    watermark_config['timing_type'],
                    watermark_config['start_frame'],
                    watermark_config['end_frame'],
                    watermark_config['start_time'],
                    watermark_config['end_time'],
                    fps
                )

            # 插视频时机配置
            video_start = 0
            if video_config:
                timing_type = video_config.get('timing_type', '起始时间')
                if timing_type == "起始帧":
                    video_start = video_config['start_frame'] / fps
                else:  # 起始时间
                    video_start = VideoEffectsProcessor.time_to_seconds(video_config['start_time'])
                Logger.info(f"插视频起始时机: {video_start}s (类型: {timing_type})")

            # 处理每一帧
            frame_index = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                current_time = frame_index / fps

                # 效果应用顺序：花字 -> 插视频 -> 插图 -> 水印
                # 后应用的效果会覆盖先应用的效果（如果位置重叠）

                # 应用花字效果
                if flower_img is not None and flower_start <= current_time <= flower_end:
                    try:
                        # 应用动态效果（如果启用）
                        current_flower_img = flower_img
                        if flower_animation:
                            try:
                                # 获取动画参数
                                animation_speed = flower_config.get('animation_speed', 1.0)
                                animation_amplitude = flower_config.get('animation_amplitude', 20.0)
                                animation_direction = flower_config.get('animation_direction', 'left')

                                # 计算花字显示的起始帧
                                flower_start_frame = int(flower_start * fps)

                                # 动效的 frame_index 应该从花字开始显示的帧开始计算
                                animation_frame_index = frame_index - flower_start_frame

                                # 应用动画效果（传递所有可能的参数，让每个动效自己选择需要的）
                                current_flower_img = flower_animation.apply_animation(
                                    flower_img,
                                    animation_frame_index,
                                    total_frames,
                                    fps,
                                    speed=animation_speed,
                                    amplitude=animation_amplitude,
                                    direction=animation_direction,
                                    frequency=animation_speed,  # 使用 speed 作为 frequency
                                    scale_min=0.9,
                                    scale_max=1.1
                                )
                            except Exception as anim_error:
                                Logger.warning(f"应用动态效果失败: {anim_error}")
                                import traceback
                                Logger.error(traceback.format_exc())
                                current_flower_img = flower_img

                        fh, fw = current_flower_img.shape[:2]
                        fx, fy = flower_config['x'], flower_config['y']
                        Logger.debug(f"应用花字: frame={frame_index}, time={current_time:.2f}s, pos=({fx},{fy}), size=({fw},{fh})")

                        if fx + fw <= width and fy + fh <= height:
                            # 处理透明背景
                            if current_flower_img.shape[2] == 4:  # BGRA
                                alpha = current_flower_img[:, :, 3] / 255.0
                                alpha_mean = np.mean(alpha)
                                Logger.debug(f"花字alpha混合: alpha_mean={alpha_mean:.3f}, alpha_range=[{alpha.min():.3f}, {alpha.max():.3f}]")

                                for c in range(3):
                                    frame[fy:fy+fh, fx:fx+fw, c] = (
                                        alpha * current_flower_img[:, :, c] +
                                        (1 - alpha) * frame[fy:fy+fh, fx:fx+fw, c]
                                    )
                            else:
                                frame[fy:fy+fh, fx:fx+fw] = current_flower_img
                        else:
                            Logger.warning(f"花字位置超出视频范围: ({fx},{fy})+({fw},{fh}) > ({width},{height})")
                    except Exception as e:
                        Logger.error(f"应用花字失败: {e}")

                # 应用插视频效果
                if video_cap is not None and current_time >= video_start:
                    try:
                        # 计算要插入的视频帧索引（从起始时机开始计算）
                        video_frame_index = int((current_time - video_start) * fps)
                        video_cap.set(cv2.CAP_PROP_POS_FRAMES, video_frame_index)
                        ret_video, video_frame = video_cap.read()

                        if ret_video:
                            # 调整视频帧大小
                            target_width = video_config.get('width', 200)
                            target_height = video_config.get('height', 150)
                            video_frame_resized = cv2.resize(video_frame, (target_width, target_height))

                            vh, vw = video_frame_resized.shape[:2]
                            vx, vy = video_config['x'], video_config['y']

                            Logger.debug(f"应用插视频: frame={frame_index}, time={current_time:.2f}s, pos=({vx},{vy}), size=({vw},{vh})")

                            if vx + vw <= width and vy + vh <= height:
                                # 检测与花字的位置重叠
                                if flower_img is not None and flower_start <= current_time <= flower_end:
                                    fh, fw = flower_img.shape[:2]
                                    fx, fy = flower_config['x'], flower_config['y']
                                    if VideoEffectsProcessor.check_position_overlap(vx, vy, vw, vh, fx, fy, fw, fh):
                                        Logger.debug(f"插视频与花字位置重叠，花字会被覆盖")

                                # 直接叠加视频帧
                                frame[vy:vy+vh, vx:vx+vw] = video_frame_resized
                                Logger.debug(f"插视频已应用")
                            else:
                                Logger.warning(f"插视频位置超出视频范围: ({vx},{vy})+({vw},{vh}) > ({width},{height})")
                        else:
                            Logger.debug(f"插视频已播放结束: frame_index={video_frame_index}")
                    except Exception as e:
                        Logger.error(f"应用插视频失败: {e}")
                        import traceback
                        Logger.error(traceback.format_exc())
                        pass

                # 应用插图效果（后应用，会覆盖插视频）
                if overlay_img is not None and overlay_start <= current_time <= overlay_end:
                    try:
                        oh, ow = overlay_img.shape[:2]
                        ox, oy = image_config['x'], image_config['y']
                        Logger.debug(f"应用插图: frame={frame_index}, time={current_time:.2f}s, pos=({ox},{oy}), size=({ow},{oh}), channels={overlay_img.shape[2]}")

                        if ox + ow <= width and oy + oh <= height:
                            # 检测与插视频的位置重叠
                            if video_cap is not None and current_time >= video_start:
                                video_target_width = video_config.get('width', 200)
                                video_target_height = video_config.get('height', 150)
                                vx, vy = video_config['x'], video_config['y']
                                if VideoEffectsProcessor.check_position_overlap(ox, oy, ow, oh, vx, vy, video_target_width, video_target_height):
                                    Logger.debug(f"插图与插视频位置重叠，插视频会被覆盖")

                            # 检测与花字的位置重叠
                            if flower_img is not None and flower_start <= current_time <= flower_end:
                                fh, fw = flower_img.shape[:2]
                                fx, fy = flower_config['x'], flower_config['y']
                                if VideoEffectsProcessor.check_position_overlap(ox, oy, ow, oh, fx, fy, fw, fh):
                                    Logger.debug(f"插图与花字位置重叠，花字会被覆盖")

                            # 确保颜色空间一致
                            if overlay_img.shape[2] == 3:
                                # BGR图像，直接叠加
                                frame[oy:oy+oh, ox:ox+ow] = overlay_img
                                Logger.debug(f"插图已应用（BGR）")
                            elif overlay_img.shape[2] == 4:
                                # BGRA图像，处理透明度
                                alpha = overlay_img[:, :, 3] / 255.0
                                alpha_mean = np.mean(alpha)
                                Logger.debug(f"插图alpha混合: alpha_mean={alpha_mean:.3f}, alpha_range=[{alpha.min():.3f}, {alpha.max():.3f}]")

                                # 只在非透明区域叠加，注意BGRA到BGR的通道顺序
                                for c in range(3):
                                    frame[oy:oy+oh, ox:ox+ow, c] = (
                                        alpha * overlay_img[:, :, c] +
                                        (1 - alpha) * frame[oy:oy+oh, ox:ox+ow, c]
                                    )
                                Logger.debug(f"插图已应用（BGRA）")
                        else:
                            Logger.warning(f"插图位置超出视频范围: ({ox},{oy})+({ow},{oh}) > ({width},{height})")
                    except Exception as e:
                        Logger.error(f"Failed to apply overlay: {e}")
                        import traceback
                        Logger.error(traceback.format_exc())
                        pass

                # 应用水印效果（后应用，会覆盖所有其他效果）
                if watermark_img is not None and watermark_start <= current_time <= watermark_end:
                    frame = VideoEffectsProcessor.apply_watermark_effect(
                        frame, watermark_img,
                        watermark_config['style'],
                        frame_index, total_frames
                    )

                # 写入帧
                out.write(frame)
                frame_index += 1

            # 释放资源
            cap.release()
            if video_cap is not None:
                video_cap.release()
            out.release()

            Logger.info(f"Video effects applied successfully: {output_path}")
            return True

        except Exception as e:
            Logger.error(f"Failed to apply video effects: {e}")
            return False