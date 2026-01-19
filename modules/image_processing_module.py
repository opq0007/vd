"""
图像处理模块 (Image Processing Module)

提供图像去背景、图片混合等图像处理功能。
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from PIL import Image
import numpy as np
import onnxruntime as ort

from config import config
from utils.logger import Logger
from utils.file_utils import FileUtils


class ImageProcessingModule:
    """图像处理模块"""

    def __init__(self):
        self.config = config
        self._rmbg_session = None
        self._rmbg_model_path = None

    def _get_rmbg_model_path(self) -> Path:
        """获取RMBG模型路径"""
        if self._rmbg_model_path is None:
            # 模型存储在 models/ 目录下，文件名为 rmbg-1.4.onnx
            model_path = Path(config.MODELS_DIR) / "rmbg-1.4.onnx"
            
            self._rmbg_model_path = model_path
        
        return self._rmbg_model_path

    def _load_rmbg_model(self):
        """加载RMBG模型"""
        if self._rmbg_session is None:
            model_path = self._get_rmbg_model_path()
            
            if not model_path.exists():
                raise FileNotFoundError(
                    f"RMBG模型文件不存在: {model_path}\n"
                    f"请从以下地址下载模型文件并放置到 {model_path.parent} 目录:\n"
                    f"https://modelscope.cn/models/AI-ModelScope/RMBG-1.4/resolve/master/onnx/model.onnx\n"
                    f"下载后请将文件重命名为 rmbg-1.4.onnx"
                )
            
            Logger.info(f"加载RMBG模型: {model_path}")
            
            # 创建ONNX Runtime会话
            providers = ['CPUExecutionProvider']
            if ort.get_device() == 'GPU':
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            
            self._rmbg_session = ort.InferenceSession(str(model_path), providers=providers)
            Logger.info("RMBG模型加载成功")

    def _preprocess_image(self, image: Image.Image) -> np.ndarray:
        """预处理图像用于RMBG模型"""
        # 转换为RGB
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 调整大小为1024x1024
        image = image.resize((1024, 1024), Image.BILINEAR)
        
        # 转换为numpy数组并归一化
        img_array = np.array(image).astype(np.float32) / 255.0
        
        # 转换为CHW格式
        img_array = img_array.transpose(2, 0, 1)
        
        # 添加批次维度
        img_array = np.expand_dims(img_array, axis=0)
        
        return img_array

    def _postprocess_mask(self, mask: np.ndarray, original_size: Tuple[int, int]) -> Image.Image:
        """后处理mask输出"""
        # 移除批次和通道维度
        mask = mask.squeeze()
        
        # 调整大小为原始尺寸
        mask = (mask * 255).astype(np.uint8)
        mask_image = Image.fromarray(mask)
        mask_image = mask_image.resize(original_size, Image.BILINEAR)
        
        return mask_image

    async def remove_background(
        self,
        image_path: str,
        input_type: str = "path",
        output_path: Optional[str] = None,
        job_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        去除图片背景
        
        Args:
            image_path: 输入图片路径（上传文件路径或URL/本地路径）
            input_type: 输入类型 (upload/path)
            output_path: 输出图片路径（可选）
            job_dir: 任务目录（可选）
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            # 创建任务目录（如果未提供）
            if job_dir is None:
                job_dir = FileUtils.create_job_dir()
            else:
                job_dir = Path(job_dir)
                job_dir.mkdir(parents=True, exist_ok=True)
            
            # 处理输入文件
            local_image_path = None
            if input_type == "path":
                # 处理路径输入（URL或本地路径）
                local_image_path = FileUtils.process_path_input(image_path, job_dir)
                Logger.info(f"处理图片路径: {image_path} -> {local_image_path}")
            else:
                # 上传文件，直接使用
                local_image_path = Path(image_path)
            
            # 验证文件存在
            if not local_image_path.exists():
                raise FileNotFoundError(f"图片文件不存在: {local_image_path}")
            
            # 加载模型
            self._load_rmbg_model()
            
            # 打开原始图片
            original_image = Image.open(local_image_path)
            original_size = original_image.size
            
            # 预处理
            input_array = self._preprocess_image(original_image)
            
            # 推理
            input_name = self._rmbg_session.get_inputs()[0].name
            output_name = self._rmbg_session.get_outputs()[0].name
            
            mask = self._rmbg_session.run([output_name], {input_name: input_array})[0]
            
            # 后处理mask
            mask_image = self._postprocess_mask(mask, original_size)
            
            # 将原始图片转为RGBA
            original_image = original_image.convert('RGBA')
            
            # 应用mask
            output_image = Image.new('RGBA', original_size)
            for x in range(original_size[0]):
                for y in range(original_size[1]):
                    r, g, b, a = original_image.getpixel((x, y))
                    mask_val = mask_image.getpixel((x, y))
                    output_image.putpixel((x, y), (r, g, b, mask_val))
            
            # 保存结果
            if output_path is None:
                output_path = job_dir / f"removed_bg_{FileUtils.generate_job_id()}.png"
            
            output_image.save(output_path)
            
            Logger.info(f"背景去除成功: {output_path}")
            
            return {
                "success": True,
                "output_path": str(output_path),
                "original_size": original_size
            }
            
        except Exception as e:
            Logger.error(f"背景去除失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }

    async def blend_images(
        self,
        base_image_path: str,
        overlay_image_path: str,
        input_type: str = "path",
        position_x: int = 0,
        position_y: int = 0,
        scale: float = 1.0,
        width: Optional[int] = None,
        height: Optional[int] = None,
        remove_bg: bool = False,
        output_path: Optional[str] = None,
        job_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        图片混合：将第二张图片叠加到第一张图片上
        
        Args:
            base_image_path: 基础图片路径（上传文件路径或URL/本地路径）
            overlay_image_path: 叠加图片路径（上传文件路径或URL/本地路径）
            input_type: 输入类型 (upload/path)
            position_x: 叠加位置的X坐标
            position_y: 叠加位置的Y坐标
            scale: 叠加图片的缩放比例（当width和height都为None时使用）
            width: 叠加图片的宽度（直接指定，优先级高于scale）
            height: 叠加图片的高度（直接指定，优先级高于scale）
            remove_bg: 是否去除叠加图片的背景
            output_path: 输出图片路径（可选）
            job_dir: 任务目录（可选）
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            # 创建任务目录（如果未提供）
            if job_dir is None:
                job_dir = FileUtils.create_job_dir()
            else:
                job_dir = Path(job_dir)
                job_dir.mkdir(parents=True, exist_ok=True)
            
            # 处理输入文件
            local_base_image_path = None
            local_overlay_image_path = None
            
            if input_type == "path":
                # 处理路径输入（URL或本地路径）
                local_base_image_path = FileUtils.process_path_input(base_image_path, job_dir)
                local_overlay_image_path = FileUtils.process_path_input(overlay_image_path, job_dir)
                Logger.info(f"处理图片路径 - base: {base_image_path} -> {local_base_image_path}")
                Logger.info(f"处理图片路径 - overlay: {overlay_image_path} -> {local_overlay_image_path}")
            else:
                # 上传文件，直接使用
                local_base_image_path = Path(base_image_path)
                local_overlay_image_path = Path(overlay_image_path)
            
            # 验证文件存在
            if not local_base_image_path.exists():
                raise FileNotFoundError(f"基础图片文件不存在: {local_base_image_path}")
            if not local_overlay_image_path.exists():
                raise FileNotFoundError(f"叠加图片文件不存在: {local_overlay_image_path}")
            
            # 加载基础图片
            base_image = Image.open(local_base_image_path).convert('RGBA')
            base_width, base_height = base_image.size
            
            # 处理叠加图片
            overlay_image = Image.open(local_overlay_image_path)
            
            # 如果需要去背景
            if remove_bg:
                Logger.info("去除叠加图片背景...")
                bg_removed_result = await self.remove_background(
                    str(local_overlay_image_path),
                    input_type="upload",  # 已经是本地文件，直接使用
                    job_dir=job_dir
                )
                
                if bg_removed_result["success"]:
                    overlay_image = Image.open(bg_removed_result["output_path"])
                else:
                    Logger.warning(f"去背景失败，使用原始图片: {bg_removed_result.get('error')}")
            
            # 转换为RGBA
            if overlay_image.mode != 'RGBA':
                overlay_image = overlay_image.convert('RGBA')
            
            # 调整叠加图片尺寸
            original_size = overlay_image.size
            
            # 优先使用直接指定的宽高
            if width is not None and height is not None:
                new_size = (width, height)
                overlay_image = overlay_image.resize(new_size, Image.LANCZOS)
                Logger.info(f"叠加图片调整尺寸: {original_size} -> {new_size} (直接指定)")
            elif scale != 1.0:
                # 使用缩放比例
                new_size = (
                    int(original_size[0] * scale),
                    int(original_size[1] * scale)
                )
                overlay_image = overlay_image.resize(new_size, Image.LANCZOS)
                Logger.info(f"叠加图片缩放: {original_size} -> {new_size} (缩放比例: {scale})")
            
            overlay_width, overlay_height = overlay_image.size
            
            # 创建新的画布
            result_image = Image.new('RGBA', (base_width, base_height))
            result_image.paste(base_image, (0, 0))
            
            # 叠加图片（使用alpha通道）
            result_image.paste(
                overlay_image,
                (position_x, position_y),
                overlay_image
            )
            
            # 保存结果
            if output_path is None:
                output_path = job_dir / f"blended_{FileUtils.generate_job_id()}.png"
            
            result_image.save(output_path)
            
            Logger.info(f"图片混合成功: {output_path}")
            
            return {
                "success": True,
                "output_path": str(output_path),
                "base_size": (base_width, base_height),
                "overlay_size": (overlay_width, overlay_height),
                "position": (position_x, position_y),
                "scale": scale,
                "width": width,
                "height": height,
                "background_removed": remove_bg
            }
            
        except Exception as e:
            Logger.error(f"图片混合失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }

    async def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            Dict[str, Any]: 模型信息
        """
        try:
            model_path = self._get_rmbg_model_path()
            
            info = {
                "rmbg_model_path": str(model_path),
                "rmbg_model_exists": model_path.exists(),
                "supported_formats": ['.png', '.jpg', '.jpeg', '.bmp', '.webp']
            }
            
            if model_path.exists():
                info["rmbg_model_size_mb"] = round(model_path.stat().st_size / (1024 * 1024), 2)
            
            return info
            
        except Exception as e:
            Logger.error(f"获取模型信息失败: {e}")
            return {
                "error": str(e)
            }


# 创建全局服务实例
image_processing_module = ImageProcessingModule()
