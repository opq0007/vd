"""
API 路由模块

定义所有 API 路由端点。
"""

from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from pydantic import BaseModel

from config import config
from api.auth import AuthService, verify_token
from modules.whisper_service import whisper_service
from modules.tts_module import tts_module
from modules.subtitle_module import subtitle_module
from modules.transition_module import transition_module
from modules.video_editor_module import video_editor_module
from utils.logger import Logger


# 定义请求模型
class LoginRequest(BaseModel):
    username: str
    password: str


class TranscribeRequest(BaseModel):
    audio_path: str
    whisper_model: str = None
    beam_size: int = None


def register_routes(app) -> None:
    """
    注册所有 API 路由

    Args:
        app: FastAPI 应用实例
    """

    # 创建路由器
    api_router = APIRouter(prefix="/api", tags=["API"])

    # ==================== 认证相关 ====================
    @api_router.post("/login")
    async def login(request: LoginRequest) -> Dict[str, Any]:
        """
        用户登录

        Args:
            request: 登录请求

        Returns:
            Dict[str, Any]: 包含访问令牌的响应
        """
        if AuthService.verify_user(request.username, request.password):
            access_token = AuthService.create_access_token(
                data={"sub": request.username}
            )
            return {
                "access_token": access_token,
                "token_type": "bearer"
            }
        else:
            raise HTTPException(status_code=400, detail="用户名或密码错误")

    # ==================== 模型信息 ====================
    @api_router.get("/model/info")
    async def get_model_info(payload: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
        """
        获取模型信息

        Args:
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 模型信息
        """
        return whisper_service.get_model_info()

    # ==================== 健康检查 ====================
    @api_router.get("/health")
    async def health_check() -> Dict[str, str]:
        """
        健康检查

        Returns:
            Dict[str, str]: 健康状态
        """
        return {"status": "healthy", "service": "whisper-api"}

    # ==================== 语音转文字 ====================
    @api_router.post("/transcribe/basic")
    async def transcribe_basic(
        audio: UploadFile = File(...),
        beam_size: int = Form(None),
        model_name: str = Form(None),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        基础语音转文字

        Args:
            audio: 音频文件
            beam_size: beam search 大小
            model_name: 模型名称
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 转录结果
        """
        # 保存上传的文件
        from utils.file_utils import FileUtils
        job_dir = FileUtils.create_job_dir()
        audio_path = job_dir / audio.filename

        with open(audio_path, "wb") as f:
            f.write(await audio.read())

        # 执行转录
        result = await whisper_service.transcribe_basic(
            str(audio_path),
            beam_size=beam_size,
            model_name=model_name
        )

        return result

    @api_router.post("/transcribe/advanced")
    async def transcribe_advanced(
        audio: UploadFile = File(...),
        model_name: str = Form(None),
        device: str = Form(None),
        compute_type: str = Form(None),
        beam_size: int = Form(None),
        task: str = Form("transcribe"),
        word_timestamps: bool = Form(False),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        高级语音转文字

        Args:
            audio: 音频文件
            model_name: 模型名称
            device: 设备
            compute_type: 计算类型
            beam_size: beam search 大小
            task: 任务类型
            word_timestamps: 是否包含词级时间戳
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 转录结果
        """
        from utils.file_utils import FileUtils
        job_dir = FileUtils.create_job_dir()
        audio_path = job_dir / audio.filename

        with open(audio_path, "wb") as f:
            f.write(await audio.read())

        segments = await whisper_service.transcribe_advanced(
            audio_path,
            model_name=model_name,
            device=device,
            compute_type=compute_type,
            beam_size=beam_size,
            task=task,
            word_timestamps=word_timestamps
        )

        return {
            "segments": [
                {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                    "words": seg.words if hasattr(seg, 'words') else []
                }
                for seg in segments
            ]
        }

    # ==================== 语音合成 ====================
    @api_router.post("/tts/synthesize")
    async def tts_synthesize(
        text: str = Form(...),
        prompt_wav: UploadFile = File(None),
        prompt_text: str = Form(None),
        cfg_value: float = Form(2.0),
        inference_timesteps: int = Form(10),
        do_normalize: bool = Form(True),
        denoise: bool = Form(True),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        语音合成

        Args:
            text: 要合成的文本
            prompt_wav: 参考音频文件
            prompt_text: 参考文本
            cfg_value: CFG引导强度
            inference_timesteps: 推理步数
            do_normalize: 是否标准化文本
            denoise: 是否降噪
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 合成结果
        """
        from utils.file_utils import FileUtils
        job_dir = FileUtils.create_job_dir()

        # 处理参考音频
        prompt_wav_path = None
        if prompt_wav:
            prompt_wav_path = job_dir / prompt_wav.filename
            with open(prompt_wav_path, "wb") as f:
                f.write(await prompt_wav.read())

        # 执行语音合成
        result = await tts_module.synthesize(
            text=text,
            prompt_wav=str(prompt_wav_path) if prompt_wav_path else None,
            prompt_text=prompt_text,
            cfg_value=cfg_value,
            inference_timesteps=inference_timesteps,
            do_normalize=do_normalize,
            denoise=denoise,
            output_path=job_dir / "tts_output.wav"
        )

        return result

    # ==================== 字幕生成 ====================
    @api_router.post("/subtitle/generate")
    async def generate_subtitles(
        input_type: str = Form("upload"),
        video_file: UploadFile = File(None),
        audio_file: UploadFile = File(None),
        video_path: str = Form(None),
        audio_path: str = Form(None),
        model_name: str = Form("small"),
        device: str = Form("cpu"),
        generate_subtitle: bool = Form(True),
        bilingual: bool = Form(True),
        word_timestamps: bool = Form(False),
        burn_subtitles: str = Form("none"),
        beam_size: int = Form(5),
        out_basename: str = Form(None),
        # 花字配置
        flower_text: str = Form(None),
        flower_font: str = Form("Microsoft YaHei"),
        flower_size: int = Form(40),
        flower_color: str = Form("#FFFFFF"),
        flower_x: int = Form(100),
        flower_y: int = Form(100),
        flower_timing_type: str = Form("时间戳范围"),
        flower_start_frame: int = Form(0),
        flower_end_frame: int = Form(100),
        flower_start_time: str = Form("00:00:00"),
        flower_end_time: str = Form("00:00:05"),
        flower_stroke_enabled: bool = Form(False),
        flower_stroke_color: str = Form("#000000"),
        flower_stroke_width: int = Form(2),
        # 插图配置
        image_path: str = Form(None),
        image_x: int = Form(200),
        image_y: int = Form(200),
        image_width: int = Form(200),
        image_height: int = Form(150),
        image_timing_type: str = Form("时间戳范围"),
        image_start_frame: int = Form(0),
        image_end_frame: int = Form(100),
        image_start_time: str = Form("00:00:00"),
        image_end_time: str = Form("00:00:05"),
        image_remove_bg: bool = Form(True),
        # 水印配置
        watermark_text: str = Form(None),
        watermark_font: str = Form("Arial"),
        watermark_size: int = Form(20),
        watermark_color: str = Form("#FFFFFF"),
        watermark_timing_type: str = Form("时间戳范围"),
        watermark_start_frame: int = Form(0),
        watermark_end_frame: int = Form(999999),
        watermark_start_time: str = Form("00:00:00"),
        watermark_end_time: str = Form("99:59:59"),
        watermark_style: str = Form("半透明浮动"),
        # 音频音量控制
        audio_volume: float = Form(1.0),
        # 原音频保留配置
        keep_original_audio: bool = Form(True),
        # LLM 字幕纠错配置
        enable_llm_correction: bool = Form(False),
        reference_text: str = Form(None),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        生成视频字幕（高级版）

        Args:
            input_type: 输入类型 (upload/path)
            video_file: 上传的视频文件
            audio_file: 上传的音频文件
            video_path: 视频文件路径
            audio_path: 音频文件路径
            model_name: 模型名称
            device: 设备类型
            generate_subtitle: 是否生成字幕
            bilingual: 是否生成双语字幕
            word_timestamps: 是否包含词级时间戳
            burn_subtitles: 字幕烧录类型 (none/hard)
            beam_size: beam search 大小
            out_basename: 输出文件名前缀
            flower_text: 花字文字
            flower_font: 花字字体
            flower_size: 花字大小
            flower_color: 花字颜色
            flower_x: 花字X坐标
            flower_y: 花字Y坐标
            flower_timing_type: 花字时机类型
            flower_start_frame: 花字起始帧
            flower_end_frame: 花字结束帧
            flower_start_time: 花字起始时间
            flower_end_time: 花字结束时间
            flower_stroke_enabled: 是否启用花字描边
            flower_stroke_color: 花字描边颜色
            flower_stroke_width: 花字描边宽度
            image_path: 插图路径
            image_x: 插图X坐标
            image_y: 插图Y坐标
            image_width: 插图宽度
            image_height: 插图高度
            image_timing_type: 插图时机类型
            image_start_frame: 插图起始帧
            image_end_frame: 插图结束帧
            image_start_time: 插图起始时间
            image_end_time: 插图结束时间
            image_remove_bg: 是否移除插图背景（使用rmbg-1.4.onnx模型）
            watermark_text: 水印文字
            watermark_font: 水印字体
            watermark_size: 水印大小
            watermark_color: 水印颜色
            watermark_timing_type: 水印时机类型
            watermark_start_frame: 水印起始帧
            watermark_end_frame: 水印结束帧
            watermark_start_time: 水印起始时间
            watermark_end_time: 水印结束时间
            watermark_style: 水印样式
            audio_volume: 音频音量倍数（默认1.0，表示原音量；0.5表示降低一半音量；2.0表示提高一倍音量）
            keep_original_audio: 是否保留原视频音频（默认True，保留并混合；False则替换原音频）
            enable_llm_correction: 是否启用 LLM 字幕纠错（使用智谱 AI）
            reference_text: 参考文本，用于字幕纠错
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 字幕生成结果
        """
        from utils.file_utils import FileUtils
        job_dir = FileUtils.create_job_dir()

        # 处理上传文件
        video_file_path = None
        audio_file_path = None

        if video_file:
            video_file_path = job_dir / video_file.filename
            with open(video_file_path, "wb") as f:
                f.write(await video_file.read())

        if audio_file:
            audio_file_path = job_dir / audio_file.filename
            with open(audio_file_path, "wb") as f:
                f.write(await audio_file.read())

        # 准备花字配置
        flower_config = None
        if flower_text and flower_text.strip():
            flower_config = {
                'text': flower_text,
                'font': flower_font,
                'size': flower_size,
                'color': flower_color,
                'x': flower_x,
                'y': flower_y,
                'timing_type': flower_timing_type,
                'start_frame': flower_start_frame,
                'end_frame': flower_end_frame,
                'start_time': flower_start_time,
                'end_time': flower_end_time,
                'stroke_enabled': flower_stroke_enabled,
                'stroke_color': flower_stroke_color,
                'stroke_width': flower_stroke_width
            }

        # 准备插图配置
        image_config = None
        if image_path and image_path.strip():
            image_config = {
                'path': image_path,
                'x': image_x,
                'y': image_y,
                'width': image_width,
                'height': image_height,
                'remove_bg': image_remove_bg,
                'timing_type': image_timing_type,
                'start_frame': image_start_frame,
                'end_frame': image_end_frame,
                'start_time': image_start_time,
                'end_time': image_end_time
            }

        # 准备水印配置
        watermark_config = None
        if watermark_text and watermark_text.strip():
            watermark_config = {
                'text': watermark_text,
                'font': watermark_font,
                'size': watermark_size,
                'color': watermark_color,
                'timing_type': watermark_timing_type,
                'start_frame': watermark_start_frame,
                'end_frame': watermark_end_frame,
                'start_time': watermark_start_time,
                'end_time': watermark_end_time,
                'style': watermark_style
            }

        # 执行高级字幕生成
        result = await subtitle_module.generate_subtitles_advanced(
            input_type=input_type,
            video_file=str(video_file_path) if video_file_path else None,
            audio_file=str(audio_file_path) if audio_file_path else None,
            video_path=video_path,
            audio_path=audio_path,
            model_name=model_name,
            device=device,
            generate_subtitle=generate_subtitle,
            bilingual=bilingual,
            word_timestamps=word_timestamps,
            burn_subtitles=burn_subtitles,
            beam_size=beam_size,
            out_basename=out_basename,
            flower_config=flower_config,
            image_config=image_config,
            watermark_config=watermark_config,
            audio_volume=audio_volume,
            keep_original_audio=keep_original_audio,
            enable_llm_correction=enable_llm_correction,
            reference_text=reference_text
        )

        return result

    @api_router.post("/subtitle/watermark")
    async def add_watermark(
        video: UploadFile = File(...),
        watermark_text: str = Form(None),
        watermark_image: UploadFile = File(None),
        position: str = Form("bottom_right"),
        opacity: float = Form(0.5),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        为视频添加水印

        Args:
            video: 视频文件
            watermark_text: 水印文字
            watermark_image: 水印图片
            position: 水印位置
            opacity: 透明度
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 添加水印结果
        """
        from utils.file_utils import FileUtils
        job_dir = FileUtils.create_job_dir()
        video_path = job_dir / video.filename

        with open(video_path, "wb") as f:
            f.write(await video.read())

        # 处理水印图片
        watermark_image_path = None
        if watermark_image:
            watermark_image_path = job_dir / watermark_image.filename
            with open(watermark_image_path, "wb") as f:
                f.write(await watermark_image.read())

        result = await subtitle_module.add_watermark(
            video_path=video_path,
            watermark_text=watermark_text,
            watermark_image=str(watermark_image_path) if watermark_image_path else None,
            position=position,
            opacity=opacity
        )

        return result

    # ==================== 视频转场 ====================
    @api_router.post("/transition/apply")
    async def apply_transition(
        video1: UploadFile = File(...),
        video2: UploadFile = File(...),
        transition_name: str = Form("crossfade"),
        total_frames: int = Form(30),
        fps: int = Form(30),
        width: int = Form(640),
        height: int = Form(640),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        应用转场效果

        Args:
            video1: 第一个视频文件
            video2: 第二个视频文件
            transition_name: 转场效果名称
            total_frames: 转场帧数
            fps: 帧率
            width: 输出宽度
            height: 输出高度
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 转场结果
        """
        from utils.file_utils import FileUtils
        job_dir = FileUtils.create_job_dir()

        video1_path = job_dir / video1.filename
        video2_path = job_dir / video2.filename

        with open(video1_path, "wb") as f:
            f.write(await video1.read())

        with open(video2_path, "wb") as f:
            f.write(await video2.read())

        result = await transition_module.apply_transition(
            video1_path=str(video1_path),
            video2_path=str(video2_path),
            transition_name=transition_name,
            total_frames=total_frames,
            fps=fps,
            width=width,
            height=height
        )

        return result

    @api_router.get("/transition/list")
    async def list_transitions(
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        获取可用的转场效果列表

        Args:
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 转场效果列表
        """
        return {
            "transitions": transition_module.get_available_transitions()
        }

    @api_router.get("/transition/params/{transition_name}")
    async def get_transition_params(
        transition_name: str,
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        获取转场效果的参数配置

        Args:
            transition_name: 转场效果名称
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 参数配置
        """
        return {
            "params": transition_module.get_transition_params(transition_name)
        }

    # ==================== 视频编辑 ====================
    @api_router.post("/video_editor/apply_effects")
    async def apply_video_effects(
        input_type: str = Form("upload"),
        video_file: UploadFile = File(None),
        video_path: str = Form(None),
        # 花字配置
        flower_text: str = Form(None),
        flower_font: str = Form("Microsoft YaHei"),
        flower_size: int = Form(40),
        flower_color: str = Form("#FFFFFF"),
        flower_x: int = Form(100),
        flower_y: int = Form(100),
        flower_timing_type: str = Form("时间戳范围"),
        flower_start_frame: int = Form(0),
        flower_end_frame: int = Form(100),
        flower_start_time: str = Form("00:00:00"),
        flower_end_time: str = Form("00:00:05"),
        flower_stroke_enabled: bool = Form(False),
        flower_stroke_color: str = Form("#000000"),
        flower_stroke_width: int = Form(2),
        # 插图配置
        image_path: str = Form(None),
        image_x: int = Form(200),
        image_y: int = Form(200),
        image_width: int = Form(200),
        image_height: int = Form(150),
        image_timing_type: str = Form("时间戳范围"),
        image_start_frame: int = Form(0),
        image_end_frame: int = Form(100),
        image_start_time: str = Form("00:00:00"),
        image_end_time: str = Form("00:00:05"),
        image_remove_bg: bool = Form(True),
        # 水印配置
        watermark_text: str = Form(None),
        watermark_font: str = Form("Arial"),
        watermark_size: int = Form(20),
        watermark_color: str = Form("#FFFFFF"),
        watermark_timing_type: str = Form("时间戳范围"),
        watermark_start_frame: int = Form(0),
        watermark_end_frame: int = Form(999999),
        watermark_start_time: str = Form("00:00:00"),
        watermark_end_time: str = Form("99:59:59"),
        watermark_style: str = Form("半透明浮动"),
        out_basename: str = Form(None),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        应用视频效果（花字、插图、水印）

        Args:
            input_type: 输入类型 (upload/path)
            video_file: 上传的视频文件
            video_path: 视频文件路径
            flower_text: 花字文字
            flower_font: 花字字体
            flower_size: 花字大小
            flower_color: 花字颜色
            flower_x: 花字X坐标
            flower_y: 花字Y坐标
            flower_timing_type: 花字时机类型
            flower_start_frame: 花字起始帧
            flower_end_frame: 花字结束帧
            flower_start_time: 花字起始时间
            flower_end_time: 花字结束时间
            flower_stroke_enabled: 是否启用花字描边
            flower_stroke_color: 花字描边颜色
            flower_stroke_width: 花字描边宽度
            image_path: 插图路径
            image_x: 插图X坐标
            image_y: 插图Y坐标
            image_width: 插图宽度
            image_height: 插图高度
            image_timing_type: 插图时机类型
            image_start_frame: 插图起始帧
            image_end_frame: 插图结束帧
            image_start_time: 插图起始时间
            image_end_time: 插图结束时间
            image_remove_bg: 是否移除插图背景（使用rmbg-1.4.onnx模型）
            watermark_text: 水印文字
            watermark_font: 水印字体
            watermark_size: 水印大小
            watermark_color: 水印颜色
            watermark_timing_type: 水印时机类型
            watermark_start_frame: 水印起始帧
            watermark_end_frame: 水印结束帧
            watermark_start_time: 水印起始时间
            watermark_end_time: 水印结束时间
            watermark_style: 水印样式
            out_basename: 输出文件名前缀
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 视频编辑结果
        """
        from utils.file_utils import FileUtils
        job_dir = FileUtils.create_job_dir()

        # 处理上传文件
        video_file_path = None
        if video_file:
            video_file_path = job_dir / video_file.filename
            with open(video_file_path, "wb") as f:
                f.write(await video_file.read())

        # 准备花字配置
        flower_config = None
        if flower_text and flower_text.strip():
            flower_config = {
                'text': flower_text,
                'font': flower_font,
                'size': flower_size,
                'color': flower_color,
                'x': flower_x,
                'y': flower_y,
                'timing_type': flower_timing_type,
                'start_frame': flower_start_frame,
                'end_frame': flower_end_frame,
                'start_time': flower_start_time,
                'end_time': flower_end_time,
                'stroke_enabled': flower_stroke_enabled,
                'stroke_color': flower_stroke_color,
                'stroke_width': flower_stroke_width
            }

        # 准备插图配置
        image_config = None
        if image_path and image_path.strip():
            image_config = {
                'path': image_path,
                'x': image_x,
                'y': image_y,
                'width': image_width,
                'height': image_height,
                'remove_bg': image_remove_bg,
                'timing_type': image_timing_type,
                'start_frame': image_start_frame,
                'end_frame': image_end_frame,
                'start_time': image_start_time,
                'end_time': image_end_time
            }

        # 准备水印配置
        watermark_config = None
        if watermark_text and watermark_text.strip():
            watermark_config = {
                'text': watermark_text,
                'font': watermark_font,
                'size': watermark_size,
                'color': watermark_color,
                'timing_type': watermark_timing_type,
                'start_frame': watermark_start_frame,
                'end_frame': watermark_end_frame,
                'start_time': watermark_start_time,
                'end_time': watermark_end_time,
                'style': watermark_style
            }

        # 执行视频效果处理
        result = await video_editor_module.apply_video_effects(
            input_type=input_type,
            video_file=str(video_file_path) if video_file_path else None,
            video_path=video_path,
            flower_config=flower_config,
            image_config=image_config,
            watermark_config=watermark_config,
            out_basename=out_basename
        )

        return result

    @api_router.get("/video_editor/effects")
    async def get_available_effects(
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        获取可用的视频效果列表

        Args:
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 视频效果列表
        """
        return video_editor_module.get_available_effects()

    # 注册路由器到应用
    app.include_router(api_router)