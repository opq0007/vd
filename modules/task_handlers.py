"""
任务处理器注册模块

将项目中已有的模块功能注册为任务处理器。
"""

import asyncio
from pathlib import Path
from typing import Dict, Any
from utils.logger import Logger
from utils.file_utils import FileUtils


class TaskHandlers:
    """任务处理器集合"""
    
    def __init__(self):
        self._handlers = {}
        self._initialize_handlers()
    
    def _initialize_handlers(self):
        """初始化所有任务处理器"""
        self._register_tts_handler()
        self._register_subtitle_handler()
        self._register_image_process_handler()
        self._register_video_editor_handler()
        self._register_transition_handler()
        self._register_video_merge_handler()
    
    def _register_tts_handler(self):
        """注册TTS任务处理器"""
        async def tts_handler(params: Dict[str, Any]) -> Dict[str, Any]:
            """TTS任务处理器"""
            try:
                from modules.tts_onnx_module import tts_onnx_module
                
                text = params.get("text", "")
                reference_audio = params.get("reference_audio")
                feat_id = params.get("feat_id")
                task_id = params.get("task_id", "tts")
                
                # 创建输出目录（使用共享目录或创建新目录）
                job_dir = params.get("job_dir")
                if job_dir:
                    output_dir = Path(job_dir)
                    output_dir.mkdir(parents=True, exist_ok=True)
                else:
                    output_dir = FileUtils.create_job_dir()
                
                # 使用 task_id 生成文件名
                output_path = output_dir / f"{task_id}_tts.wav"
                
                # 调用TTS模块
                if feat_id:
                    # 使用预编码特征方式
                    Logger.info(f"使用预编码特征方式调用TTS: feat_id={feat_id}")
                    result = await tts_onnx_module.synthesize(
                        text=text,
                        feat_id=feat_id,
                        output_path=output_path
                    )
                else:
                    # 使用参考音频方式
                    Logger.info(f"使用参考音频方式调用TTS: reference_audio={reference_audio}")
                    result = await tts_onnx_module.synthesize(
                        text=text,
                        prompt_wav=reference_audio,
                        output_path=output_path
                )

                # 检查处理结果
                if not result.get("success", False):
                    error_msg = result.get("error", "TTS任务失败")
                    Logger.error(f"TTS任务失败: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg
                    }

                Logger.info(f"TTS任务完成: {output_path}")

                return {
                    "success": True,
                    "output": str(output_path),
                    "duration": result.get("duration", 0)
                }
                
            except Exception as e:
                Logger.error(f"TTS任务失败: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        self._handlers["tts"] = tts_handler
        Logger.info("注册TTS任务处理器")
    
    def _register_subtitle_handler(self):
        """注册字幕任务处理器"""
        async def subtitle_handler(params: Dict[str, Any]) -> Dict[str, Any]:
            """字幕任务处理器（高级功能）"""
            try:
                from modules.subtitle_module import subtitle_module
                
                # 获取输入参数
                video_input = params.get("video", "")
                audio_input = params.get("audio", "")
                subtitle_input = params.get("subtitle", "")
                reference_text = params.get("reference_text", "")
                task_id = params.get("task_id", "subtitle")
                
                # 至少需要一个输入（视频或音频）
                if not video_input and not audio_input and not subtitle_input:
                    raise ValueError("缺少输入：需要提供视频、音频或字幕文件")
                
                # 创建输出目录（使用共享目录或创建新目录）
                job_dir = params.get("job_dir")
                if job_dir:
                    output_dir = Path(job_dir)
                    output_dir.mkdir(parents=True, exist_ok=True)
                else:
                    output_dir = FileUtils.create_job_dir()
                
                # 确定输入类型
                input_type = "path"
                
                # 准备参数
                subtitle_params = {
                    "input_type": input_type,
                    "video_path": video_input if video_input else None,
                    "audio_path": audio_input if audio_input else None,
                    "subtitle_path": subtitle_input if subtitle_input else None,
                    "model_name": params.get("model_name", "small"),
                    "device": params.get("device", "cpu"),
                    "generate_subtitle": True,
                    "bilingual": params.get("bilingual", False),
                    "word_timestamps": params.get("word_timestamps", True),
                    "burn_subtitles": params.get("burn_subtitles", "hard"),
                    "beam_size": params.get("beam_size", 5),
                    "subtitle_bottom_margin": params.get("subtitle_bottom_margin", 50),
                    # 使用 task_id 生成字幕文件名
                    "out_basename": f"{task_id}_subtitle",
                    "duration_reference": params.get("duration_reference", "video"),
                    # 默认开启 LLM 纠错
                    "enable_llm_correction": params.get("enable_llm_correction", True),
                    "reference_text": reference_text if reference_text else None,
                    # 默认开启字幕显示后处理
                    "max_chars_per_line": params.get("max_chars_per_line", 20),
                    "max_lines_per_segment": params.get("max_lines_per_segment", 2),
                    # 任务目录
                    "job_dir": output_dir,
                    # 模板目录
                    "template_dir": params.get("template_dir")
                }
                
                # 调用高级字幕生成模块
                result = await subtitle_module.generate_subtitles_advanced(**subtitle_params)

                # 检查处理结果
                if not result.get("success", False):
                    error_msg = result.get("error", "字幕任务失败")
                    Logger.error(f"字幕任务失败: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg
                    }

                Logger.info(f"高级字幕任务完成: LLM纠错={subtitle_params['enable_llm_correction']}, 后处理启用")

                # 返回视频文件路径作为主要输出（因为视频才是最终需要的）
                # 字幕文件路径仍然可以通过 subtitle_path 字段获取
                return {
                    "success": True,
                    "output": result.get("video_output_path", ""),  # 主要输出：视频文件
                    "video_output": result.get("video_output_path", ""),
                    "subtitle_path": result.get("subtitle_path", ""),  # 字幕文件路径
                    "llm_corrected": subtitle_params["enable_llm_correction"]
                }
                
            except Exception as e:
                Logger.error(f"字幕任务失败: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        self._handlers["subtitle"] = subtitle_handler
        Logger.info("注册字幕任务处理器（高级功能）")
    
    def _register_image_process_handler(self):
        """注册图像处理任务处理器"""
        async def image_process_handler(params: Dict[str, Any]) -> Dict[str, Any]:
            """图像处理任务处理器"""
            try:
                from modules.image_processing_module import image_processing_module
                import shutil
                
                # 创建输出目录（使用共享目录或创建新目录）
                job_dir = params.get("job_dir")
                if job_dir:
                    output_dir = Path(job_dir)
                    output_dir.mkdir(parents=True, exist_ok=True)
                else:
                    output_dir = FileUtils.create_job_dir()
                
                task_id = params.get("task_id", "image_process")
                
                # 检查是否为图片混合模式
                base_image = params.get("base_image", "")
                overlay_images = params.get("overlay_images", [])
                
                if base_image and overlay_images:
                    # 图片混合模式
                    Logger.info(f"图片混合模式: 基础图片={base_image}, 叠加图片={overlay_images}, 类型={type(overlay_images)}")
                    
                    # 处理 overlay_images 参数
                    if isinstance(overlay_images, str):
                        # 如果是字符串，尝试解析
                        if overlay_images == "[]" or overlay_images == "" or overlay_images == "''":
                            overlay_images = []
                        else:
                            # 可能是JSON字符串或Python列表字符串表示
                            try:
                                import json
                                overlay_images = json.loads(overlay_images)
                                Logger.info(f"JSON解析后的叠加图片: {overlay_images}")
                            except Exception as json_error:
                                # JSON解析失败，尝试Python literal_eval
                                try:
                                    import ast
                                    overlay_images = ast.literal_eval(overlay_images)
                                    Logger.info(f"Python literal_eval解析后的叠加图片: {overlay_images}")
                                except Exception as ast_error:
                                    # 都解析失败，将其作为单个路径
                                    Logger.warning(f"JSON解析失败({json_error}), Python literal_eval失败({ast_error}), 将作为单个路径处理")
                                    overlay_images = [overlay_images]
                    
                    # 确保 overlay_images 是列表
                    if not isinstance(overlay_images, list):
                        overlay_images = [overlay_images] if overlay_images else []
                    
                    # 过滤掉空值、空列表和字符串"[]"
                    overlay_images = [
                        img for img in overlay_images 
                        if img and not (isinstance(img, list) and len(img) == 0) and img not in ["[]", "''"]
                    ]
                    
                    if not overlay_images:
                        Logger.warning("没有有效的叠加图片，跳过图片混合")
                        return {
                            "success": True,
                            "output": []
                        }
                    
                    Logger.info(f"过滤后的叠加图片: {overlay_images}, 数量={len(overlay_images)}")
                    
                    output_files = []
                    
                    # 对每张叠加图片进行混合
                    for i, overlay_image_path in enumerate(overlay_images):
                        # 确保路径是字符串
                        if isinstance(overlay_image_path, list):
                            if overlay_image_path:
                                overlay_image_path = overlay_image_path[0]
                            else:
                                Logger.warning(f"第{i+1}张叠加图片为空，跳过")
                                continue
                        
                        # 跳过无效路径
                        if overlay_image_path in ["[]", "''", ""] or not overlay_image_path:
                            Logger.warning(f"第{i+1}张叠加图片无效，跳过")
                            continue
                        
                        Logger.info(f"处理第{i+1}张叠加图片: {overlay_image_path}, 类型={type(overlay_image_path)}")
                        
                        # 使用 task_id 生成文件名
                        result = await image_processing_module.blend_images(
                            base_image_path=base_image,
                            overlay_image_path=overlay_image_path,
                            input_type="path",
                            position_x=params.get("position_x", 0),
                            position_y=params.get("position_y", 0),
                            scale=params.get("scale", 1.0),
                            width=params.get("width", None),
                            height=params.get("height", None),
                            remove_bg=params.get("remove_bg", False),
                            output_path=output_dir / f"{task_id}_image_process_{i}.png",
                            job_dir=output_dir
                        )
                        
                        if result["success"]:
                            output_files.append(result["output_path"])
                        else:
                            Logger.error(f"图片混合失败（第{i+1}张）: {result.get('error')}")
                    
                    Logger.info(f"图片混合任务完成: 处理了 {len(output_files)} 张图片")
                    
                    return {
                        "success": True,
                        "output": output_files
                    }
                else:
                    # 原有的图片处理模式
                    images = params.get("images", [])
                    remove_bg = params.get("remove_bg", False)
                    resize = params.get("resize", "")
                    
                    if not images:
                        raise ValueError("缺少输入图片")
                    
                    output_files = []
                    
                    # 处理每张图片
                    for i, image_path in enumerate(images):
                        # 使用 task_id 生成文件名
                        output_file = output_dir / f"{task_id}_image_process_{i}.png"
                        
                        if remove_bg:
                            # 去除背景
                            result = await image_processing_module.remove_background(
                                image_path=image_path
                            )
                            processed_path = result.get("output_path", image_path)
                            # 复制处理后的文件到输出目录
                            if processed_path and Path(processed_path).exists():
                                shutil.copy2(processed_path, output_file)
                            else:
                                # 如果处理失败，抛出异常
                                raise FileNotFoundError(f"图像处理失败，输出文件不存在: {processed_path}")
                        else:
                            # 不需要处理，直接复制原文件
                            if not Path(image_path).exists():
                                raise FileNotFoundError(f"输入图片文件不存在: {image_path}")
                            shutil.copy2(image_path, output_file)
                        
                        output_files.append(str(output_file))
                    
                    Logger.info(f"图像处理任务完成: 处理了 {len(output_files)} 张图片")
                    
                    # 返回数组（统一返回）
                    return {
                        "success": True,
                        "output": output_files
                    }
                
            except Exception as e:
                Logger.error(f"图像处理任务失败: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        self._handlers["image_process"] = image_process_handler
        Logger.info("注册图像处理任务处理器（支持图片混合）")
    
    def _register_video_editor_handler(self):
        """注册视频编辑任务处理器"""
        async def video_editor_handler(params: Dict[str, Any]) -> Dict[str, Any]:
            """视频编辑任务处理器"""
            try:
                from modules.video_editor_module import video_editor_module
                
                input_path = params.get("input", "")
                add_audio = params.get("add_audio", "")
                task_id = params.get("task_id", "video_editor")
                
                # 处理input参数（支持数组）
                if isinstance(input_path, list):
                    if input_path:
                        input_path = input_path[0]
                    else:
                        raise ValueError("输入视频路径为空")
                
                if not input_path:
                    raise ValueError("缺少输入视频路径")
                
                # 创建输出目录（使用共享目录或创建新目录）
                job_dir = params.get("job_dir")
                if job_dir:
                    output_dir = Path(job_dir)
                    output_dir.mkdir(parents=True, exist_ok=True)
                else:
                    output_dir = FileUtils.create_job_dir()
                
                # 使用 task_id 生成文件名
                output_path = output_dir / f"{task_id}_video_editor.mp4"
                
                # 准备花字配置
                flower_config = None
                text = params.get("text", "")
                if text:
                    # 获取动画配置
                    animation_param = params.get("animation")
                    animation_config = animation_param if isinstance(animation_param, dict) else {}
                    
                    # 判断是否启用动画
                    animation_enabled = bool(animation_config and animation_config.get('type') and animation_config.get('type') != 'none')
                    
                    # 获取颜色渐变配置
                    color_mode = params.get("color_mode", "单色")
                    gradient_type = params.get("gradient_type", "diagonal")
                    color_start = params.get("color_start", "#87CEEB")
                    color_end = params.get("color_end", "#FFFFFF")
                    
                    flower_config = {
                        'text': text,
                        'font': params.get("font", "微软雅黑"),
                        'size': params.get("size", 75),
                        'color': params.get("color", "#FFFFFF"),
                        'x': params.get("x", 100),
                        'y': params.get("y", 100),
                        'timing_type': '帧数范围',
                        'start_frame': 0,
                        'end_frame': 999999,
                        'start_time': '00:00:00',
                        'end_time': '99:59:59',
                        'stroke_enabled': False,
                        'stroke_color': '#000000',
                        'stroke_width': 2,
                        # 颜色渐变配置
                        'color_mode': color_mode,
                        'gradient_type': gradient_type,
                        'color_start': color_start,
                        'color_end': color_end,
                        # 动画效果配置
                        'animation_enabled': animation_enabled,
                        'animation_type': animation_config.get('type', 'none'),
                        'animation_speed': animation_config.get('speed', 1.0),
                        'animation_amplitude': animation_config.get('amplitude', 20.0),
                        'animation_direction': animation_config.get('direction', 'up')
                    }
                    
                    Logger.info(f"花字配置: 颜色模式={color_mode}, 渐变类型={gradient_type}, 动画启用={animation_enabled}, 动画类型={animation_config.get('type', 'none')}")
                
                # 准备插图配置
                image_config = None
                image = params.get("image", "")
                images = params.get("images", "")
                
                # 支持单数和复数参数名
                image_path = image if image else images
                
                # 处理数组类型的输入
                if isinstance(image_path, list):
                    if image_path:
                        image_path = image_path[0]
                    else:
                        image_path = ""
                
                if image_path:
                    image_config = {
                        'path': image_path,  # 使用 'path' 而不是 'image_path'
                        'x': params.get("x", 800),
                        'y': params.get("y", 200),
                        'width': params.get("width", 600),
                        'height': params.get("height", 600),
                        'remove_bg': params.get("remove_bg", False),
                        'timing_type': '时间戳范围',
                        'start_frame': 0,
                        'end_frame': 999999,
                        'start_time': '00:00:00',
                        'end_time': '99:59:59'
                    }
                    Logger.info(f"插图配置: image_path={image_path}, x={params.get('x', 800)}, y={params.get('y', 200)}")
                
                # 准备插视频配置
                video_config = None
                video_path = params.get("video_path", "")
                if video_path:
                    video_config = {
                        'path': video_path,
                        'x': params.get("video_x", 0),
                        'y': params.get("video_y", 0),
                        'width': params.get("video_width", 300),
                        'height': params.get("video_height", 300),
                        'timing_type': '时间戳范围',
                        'start_frame': 0,
                        'end_frame': 999999,
                        'start_time': '00:00:00',
                        'end_time': '99:59:59'
                    }
                
                # 准备音频路径
                audio_path = None
                if add_audio:
                    audio_path = add_audio
                
                # 调用视频编辑模块
                result = await video_editor_module.apply_video_effects(
                    input_type="path",
                    video_path=input_path,
                    audio_path=audio_path,
                    flower_config=flower_config,
                    image_config=image_config,
                    video_config=video_config,
                    # 使用 task_id 生成文件名
                    out_basename=f"{task_id}_video_editor",
                    job_dir=output_dir,
                    template_dir=params.get("template_dir")  # 传递模板目录
                )

                # 检查处理结果
                if not result.get("success", False):
                    error_msg = result.get("error", "视频编辑任务失败")
                    Logger.error(f"视频编辑任务失败: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg
                    }

                # 获取实际的输出文件路径
                actual_output = result.get("video_output_path", str(output_path))
                Logger.info(f"视频编辑任务完成: {actual_output}")

                return {
                    "success": True,
                    "output": actual_output
                }
                
            except Exception as e:
                Logger.error(f"视频编辑任务失败: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        self._handlers["video_editor"] = video_editor_handler
        Logger.info("注册视频编辑任务处理器")
    
    def _register_transition_handler(self):
        """注册视频转场任务处理器"""
        async def transition_handler(params: Dict[str, Any]) -> Dict[str, Any]:
            """视频转场任务处理器"""
            try:
                from modules.transition_module import transition_module
                
                video1_path = params.get("video1", "")
                video2_path = params.get("video2", "")
                transition_name = params.get("transition_name", "crossfade")
                total_frames = params.get("total_frames", 30)
                fps = params.get("fps", 30)
                width = params.get("width", 640)
                height = params.get("height", 640)
                task_id = params.get("task_id", "transition")
                
                # 处理video1参数（支持数组，取第一个元素）
                if isinstance(video1_path, list):
                    if video1_path:
                        video1_path = video1_path[0]
                    else:
                        raise ValueError("缺少第一个视频/图片路径")
                
                if not video1_path:
                    raise ValueError("缺少第一个视频/图片路径")
                
                # 处理video2_path参数（兼容字符串和数组）
                if isinstance(video2_path, str):
                    # 如果是字符串，尝试解析
                    if video2_path == "[]" or video2_path == "" or video2_path == "''":
                        video2_path = []
                    else:
                        # 可能是JSON字符串或Python列表字符串表示
                        try:
                            import json
                            video2_path = json.loads(video2_path)
                            Logger.info(f"JSON解析后的video2_path: {video2_path}")
                        except Exception as json_error:
                            # JSON解析失败，尝试Python literal_eval
                            try:
                                import ast
                                video2_path = ast.literal_eval(video2_path)
                                Logger.info(f"Python literal_eval解析后的video2_path: {video2_path}")
                            except Exception as ast_error:
                                # 都解析失败，将其作为单个路径
                                Logger.warning(f"JSON解析失败({json_error}), Python literal_eval失败({ast_error}), 将作为单个路径处理")
                                video2_path = [video2_path]
                
                # 确保 video2_path 是列表
                if not isinstance(video2_path, list):
                    video2_path = [video2_path] if video2_path else []
                
                # 过滤掉空值、空列表和字符串"[]"
                video2_path = [
                    path for path in video2_path 
                    if path and not (isinstance(path, list) and len(path) == 0) and path not in ["[]", "''"]
                ]
                
                if not video2_path:
                    raise ValueError("缺少第二个视频/图片路径")
                
                Logger.info(f"过滤后的video2_path: {video2_path}, 数量={len(video2_path)}")
                
                # 创建输出目录（使用共享目录或创建新目录）
                job_dir = params.get("job_dir")
                if job_dir:
                    output_dir = Path(job_dir)
                    output_dir.mkdir(parents=True, exist_ok=True)
                else:
                    output_dir = FileUtils.create_job_dir()
                
                # 调用视频转场模块
                # 传递 template_dir 参数，用于查找模板资源
                template_dir = params.get("template_dir")
                
                output_files = []
                
                # 遍历每个 video2_path 进行转场处理
                for i, v2_path in enumerate(video2_path):
                    # 确保路径是字符串
                    if isinstance(v2_path, list):
                        if v2_path:
                            v2_path = v2_path[0]
                        else:
                            Logger.warning(f"第{i+1}个video2_path为空，跳过")
                            continue
                    
                    # 跳过无效路径
                    if v2_path in ["[]", "''", ""] or not v2_path:
                        Logger.warning(f"第{i+1}个video2_path无效，跳过")
                        continue
                    
                    Logger.info(f"处理第{i+1}个转场: video1={video1_path}, video2={v2_path}")
                    
                    result = await transition_module.apply_transition(
                        video1_path=video1_path,
                        video2_path=v2_path,
                        transition_name=transition_name,
                        total_frames=total_frames,
                        fps=fps,
                        width=width,
                        height=height,
                        job_dir=output_dir,
                        template_dir=template_dir,
                        output_basename=f"{task_id}_transition_{i}"  # 使用 task_id 和索引作为输出文件名前缀
                    )
                    
                    if result.get("success"):
                        output_files.append(result.get("output_path", ""))
                        Logger.info(f"第{i+1}个转场任务完成: {result.get('output_path')}")
                    else:
                        Logger.error(f"第{i+1}个转场任务失败: {result.get('error')}")
                
                if not output_files:
                    return {
                        "success": False,
                        "error": "所有转场任务都失败了"
                    }
                
                Logger.info(f"视频转场任务完成: 处理了 {len(output_files)} 个转场")
                
                # 返回数组结果
                return {
                    "success": True,
                    "output": output_files
                }
                
            except Exception as e:
                Logger.error(f"视频转场任务失败: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        self._handlers["video_transition"] = transition_handler
        Logger.info("注册视频转场任务处理器（支持数组输入）")
    
    def _register_video_merge_handler(self):
        """注册视频合并任务处理器"""
        async def video_merge_handler(params: Dict[str, Any]) -> Dict[str, Any]:
            """视频合并任务处理器"""
            try:
                from modules.video_merge_module import video_merge_module
                
                videos = params.get("videos", "")
                output_name = params.get("output_name", "merged_video")
                task_id = params.get("task_id", "video_merge")
                delete_intermediate_videos = params.get("delete_intermediate_videos", True)
                
                if not videos:
                    raise ValueError("缺少输入视频路径")
                
                # 创建输出目录（使用共享目录或创建新目录）
                job_dir = params.get("job_dir")
                if job_dir:
                    output_dir = Path(job_dir)
                    output_dir.mkdir(parents=True, exist_ok=True)
                else:
                    output_dir = FileUtils.create_job_dir()
                
                # 使用 task_id 生成输出文件名
                if not output_name or output_name == "merged_video":
                    output_name = f"{task_id}_merged_video"
                
                # 调用视频合并模块
                result = await video_merge_module.merge_videos(
                    video_paths=videos,
                    out_basename=output_name,
                    job_dir=output_dir,
                    delete_intermediate_videos=delete_intermediate_videos
                )

                # 检查处理结果
                if not result.get("success", False):
                    error_msg = result.get("error", "视频合并任务失败")
                    Logger.error(f"视频合并任务失败: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg
                    }

                Logger.info(f"视频合并任务完成: {result.get('output_path', '')}, 删除中间文件: {delete_intermediate_videos}")

                return {
                    "success": True,
                    "output": result.get("output_path", "")
                }
                
            except Exception as e:
                Logger.error(f"视频合并任务失败: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        self._handlers["video_merge"] = video_merge_handler
        Logger.info("注册视频合并任务处理器")
    
    def get_handler(self, task_type: str):
        """
        获取任务处理器
        
        Args:
            task_type: 任务类型
            
        Returns:
            任务处理器函数
        """
        return self._handlers.get(task_type)
    
    def get_available_handlers(self) -> Dict[str, str]:
        """
        获取所有可用的任务处理器
        
        Returns:
            任务处理器字典 {task_type: description}
        """
        return {
            "tts": "语音合成",
            "subtitle": "字幕生成",
            "image_process": "图像处理",
            "video_editor": "视频编辑",
            "video_transition": "视频转场",
            "video_merge": "视频合并"
        }


# 创建全局任务处理器实例
task_handlers = TaskHandlers()