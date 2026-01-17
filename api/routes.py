"""
API 路由模块

定义所有 API 路由端点。
"""

from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import config
from api.auth import AuthService, verify_token
from modules.whisper_service import whisper_service
from modules.tts_onnx_module import tts_onnx_module
from modules.subtitle_module import subtitle_module
from modules.transition_module import transition_module
from modules.video_editor_module import video_editor_module
from modules.image_processing_module import image_processing_module
from utils.logger import Logger
from utils.media_processor import MediaProcessor


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
        feat_id: str = Form(None),
        cfg_value: float = Form(2.0),
        min_len: int = Form(2),
        max_len: int = Form(2000),
        timesteps: int = Form(5),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        VoxCPM-1.5 ONNX 语音合成

        Args:
            text: 要合成的文本
            prompt_wav: 参考音频文件
            prompt_text: 参考文本
            feat_id: 预编码特征 ID
            cfg_value: CFG引导强度
            min_len: 最小生成长度
            max_len: 最大生成长度
            timesteps: Diffusion 推理步数
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
        result = await tts_onnx_module.synthesize(
            text=text,
            prompt_wav=str(prompt_wav_path) if prompt_wav_path else None,
            prompt_text=prompt_text,
            feat_id=feat_id,
            cfg_value=cfg_value,
            min_len=min_len,
            max_len=max_len,
            timesteps=timesteps,
            output_path=job_dir / "tts_output.wav"
        )

        return result

    @api_router.post("/tts/save_ref")
    async def tts_save_ref(
        feat_id: str = Form(...),
        prompt_audio: UploadFile = File(...),
        prompt_text: str = Form(None),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        保存参考音频特征

        Args:
            feat_id: 特征 ID
            prompt_audio: 参考音频文件
            prompt_text: 参考文本
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 保存结果
        """
        from utils.file_utils import FileUtils
        job_dir = FileUtils.create_job_dir()

        # 保存上传的音频
        prompt_audio_path = job_dir / prompt_audio.filename
        with open(prompt_audio_path, "wb") as f:
            f.write(await prompt_audio.read())

        # 保存特征
        result = await tts_onnx_module.save_ref_audio(
            feat_id=feat_id,
            prompt_audio_path=str(prompt_audio_path),
            prompt_text=prompt_text
        )

        return result

    @api_router.get("/tts/info")
    async def tts_info(
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        获取 TTS 模型信息

        Args:
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 模型信息
        """
        return tts_onnx_module.get_model_info()

    @api_router.get("/tts/ref_features")
    async def tts_list_ref_features(
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        获取所有已保存的参考音频特征

        Args:
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 特征列表
        """
        return tts_onnx_module.list_ref_features()

    @api_router.get("/file/download")
    async def download_file(
        file_path: str = Query(..., description="文件路径"),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> FileResponse:
        """
        下载文件（返回二进制流）

        Args:
            file_path: 文件路径
            payload: 认证载荷

        Returns:
            FileResponse: 文件二进制流
        """
        from pathlib import Path
        
        # 解析文件路径
        file_obj = Path(file_path).resolve()
        
        # 验证文件是否存在
        if not file_obj.exists():
            raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")
        
        # 验证是否为文件
        if not file_obj.is_file():
            raise HTTPException(status_code=400, detail=f"路径不是文件: {file_path}")
        
        # 安全检查：确保文件在允许的目录内
        allowed_dirs = [
            Path(config.OUTPUT_FOLDER).resolve(),
            Path(config.UPLOAD_FOLDER).resolve(),
            Path(config.DEBUG_FOLDER).resolve(),
            Path(config.MODELS_DIR).resolve(),
        ]
        
        is_allowed = any(
            str(file_obj).startswith(str(allowed_dir))
            for allowed_dir in allowed_dirs
        )
        
        if not is_allowed:
            raise HTTPException(
                status_code=403,
                detail=f"文件路径不在允许的目录内: {file_path}"
            )
        
        # 根据文件扩展名确定 media type
        media_type = "application/octet-stream"
        if file_obj.suffix.lower() in ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac']:
            media_type = "audio/mpeg"
        elif file_obj.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']:
            media_type = "video/mp4"
        elif file_obj.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif']:
            media_type = "image/jpeg"
        elif file_obj.suffix.lower() == '.srt':
            media_type = "text/plain"
        elif file_obj.suffix.lower() == '.json':
            media_type = "application/json"
        
        return FileResponse(
            path=str(file_obj),
            media_type=media_type,
            filename=file_obj.name
        )

    # ==================== 字幕生成 ====================
    @api_router.post("/subtitle/generate")
    async def generate_subtitles(
        input_type: str = Form("upload"),
        video_file: UploadFile = File(None),
        audio_file: UploadFile = File(None),
        subtitle_file: UploadFile = File(None),
        video_path: str = Form(None),
        audio_path: str = Form(None),
        subtitle_path: str = Form(None),
        model_name: str = Form("small"),
        device: str = Form("cpu"),
        generate_subtitle: bool = Form(True),
        bilingual: bool = Form(True),
        word_timestamps: bool = Form(False),
        burn_subtitles: str = Form("none"),
        beam_size: int = Form(5),
        subtitle_bottom_margin: int = Form(20),
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
                # Whisper 基础参数
                vad_filter: bool = Form(True),
                condition_on_previous_text: bool = Form(False),
                temperature: float = Form(0.0),
                # 字幕显示参数（后处理）
                max_chars_per_line: int = Form(20),
                max_lines_per_segment: int = Form(2),
        
                payload: Dict[str, Any] = Depends(verify_token)    ) -> Dict[str, Any]:
        """
        生成视频字幕（高级版）

        Args:
            input_type: 输入类型 (upload/path)
            video_file: 上传的视频文件
            audio_file: 上传的音频文件
            subtitle_file: 上传的字幕文件
            video_path: 视频文件路径
            audio_path: 音频文件路径
            subtitle_path: 字幕文件路径
            model_name: 模型名称
            device: 设备类型
            generate_subtitle: 是否生成字幕
            bilingual: 是否生成双语字幕
            word_timestamps: 是否包含词级时间戳
            burn_subtitles: 字幕烧录类型 (none/hard)
            beam_size: beam search 大小
            subtitle_bottom_margin: 字幕下沿距离（像素，默认0）
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
            vad_filter: 启用 VAD 语音活动检测（默认True）
            condition_on_previous_text: 不依赖前文分段（默认False），产生更自然的分段
            temperature: 温度参数（默认0.0），控制预测的随机性
            max_chars_per_line: 字幕每行最大字符数（默认20），超过会自动分割
            max_lines_per_segment: 字幕每段最大行数（默认2），超过会自动分割
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 字幕生成结果
        """
        from utils.file_utils import FileUtils
        job_dir = FileUtils.create_job_dir()

        # 处理上传文件
        video_file_path = None
        audio_file_path = None
        subtitle_file_path = None

        if video_file:
            video_file_path = job_dir / video_file.filename
            with open(video_file_path, "wb") as f:
                f.write(await video_file.read())

        if audio_file:
            audio_file_path = job_dir / audio_file.filename
            with open(audio_file_path, "wb") as f:
                f.write(await audio_file.read())

        if subtitle_file:
            subtitle_file_path = job_dir / subtitle_file.filename
            with open(subtitle_file_path, "wb") as f:
                f.write(await subtitle_file.read())

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
            subtitle_file=str(subtitle_file_path) if subtitle_file_path else None,
            video_path=video_path,
            audio_path=audio_path,
            subtitle_path=subtitle_path,
            model_name=model_name,
            device=device,
            generate_subtitle=generate_subtitle,
            bilingual=bilingual,
            word_timestamps=word_timestamps,
            burn_subtitles=burn_subtitles,
            beam_size=beam_size,
            subtitle_bottom_margin=subtitle_bottom_margin,
            out_basename=out_basename,
            flower_config=flower_config,
            image_config=image_config,
            watermark_config=watermark_config,
            audio_volume=audio_volume,
            keep_original_audio=keep_original_audio,
            enable_llm_correction=enable_llm_correction,
            reference_text=reference_text,
            # Whisper 基础参数
            vad_filter=vad_filter,
            condition_on_previous_text=condition_on_previous_text,
            temperature=temperature,
            # 字幕显示参数（后处理）
            max_chars_per_line=max_chars_per_line,
            max_lines_per_segment=max_lines_per_segment,
            job_dir=job_dir  # 传递 job_dir，确保在同一个目录下处理
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
            opacity=opacity,
            job_dir=job_dir  # 传递 job_dir，确保在同一个目录下处理
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
            height=height,
            job_dir=job_dir  # 传递 job_dir，确保在同一个目录下处理
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
            out_basename=out_basename,
            job_dir=job_dir  # 传递 job_dir，确保在同一个目录下处理
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

    # ==================== 文件上传 ====================
    @api_router.post("/file/upload")
    async def upload_file(
        file: UploadFile = File(...),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        文件上传接口

        Args:
            file: 上传的文件
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 包含文件路径的响应
        """
        from utils.file_utils import FileUtils

        try:
            # 确保上传目录存在
            upload_dir = Path(config.UPLOAD_FOLDER)
            upload_dir.mkdir(parents=True, exist_ok=True)

            # 生成安全的文件名
            filename = file.filename
            if not filename:
                raise HTTPException(status_code=400, detail="文件名不能为空")

            # 避免文件名冲突
            file_path = upload_dir / filename
            counter = 1
            while file_path.exists():
                name, ext = Path(filename).stem, Path(filename).suffix
                file_path = upload_dir / f"{name}_{counter}{ext}"
                counter += 1

            # 保存文件
            with open(file_path, "wb") as f:
                f.write(await file.read())

            Logger.info(f"文件上传成功: {file_path}")

            return {
                "success": True,
                "filename": file_path.name,
                "filepath": str(file_path.absolute()),
                "size": file_path.stat().st_size,
                "message": "文件上传成功"
            }

        except Exception as e:
            Logger.error(f"文件上传失败: {e}")
            raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

    # ==================== 一站式音视频合成+字幕生成+LLM纠错 ====================
    @api_router.post("/video/complete_process")
    async def complete_video_process(
        video_path: str = Form(...),
        audio_path: str = Form(...),
        model_name: str = Form("small"),
        device: str = Form("cpu"),
        beam_size: int = Form(5),
        audio_volume: float = Form(1.0),
        keep_original_audio: bool = Form(True),
        enable_llm_correction: bool = Form(False),
        reference_text: str = Form(None),
        burn_subtitles: str = Form("hard"),
        out_basename: str = Form(None),
        # Whisper 基础参数
        vad_filter: bool = Form(True),
        condition_on_previous_text: bool = Form(False),
        temperature: float = Form(0.0),
        # 字幕显示参数（后处理）
        max_chars_per_line: int = Form(20),
        max_lines_per_segment: int = Form(2),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        一站式音视频合成+字幕生成+LLM纠错

        自动进行以下操作：
        1. 以视频时长为准，自动调整音频速率来适配视频时长
        2. 将音频与视频合成
        3. 生成字幕
        4. 如果启用LLM纠错，使用智谱AI进行字幕纠错
        5. 如果需要，烧录字幕到视频

        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径
            model_name: Whisper模型名称
            device: 设备类型
            beam_size: beam search 大小
            audio_volume: 音频音量倍数（默认1.0）
            keep_original_audio: 是否保留原视频音频（默认True）
            enable_llm_correction: 是否启用LLM字幕纠错
            reference_text: 参考文本，用于字幕纠错
            burn_subtitles: 字幕烧录类型 (none/hard)
            out_basename: 输出文件名前缀
            vad_filter: 启用 VAD 语音活动检测（默认True）
            condition_on_previous_text: 不依赖前文分段（默认False），产生更自然的分段
            temperature: 温度参数（默认0.0），控制预测的随机性
            max_chars_per_line: 字幕每行最大字符数（默认20），超过会自动分割
            max_lines_per_segment: 字幕每段最大行数（默认2），超过会自动分割
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            # 验证文件路径
            video_file = Path(video_path)
            audio_file = Path(audio_path)

            if not video_file.exists():
                raise HTTPException(status_code=404, detail=f"视频文件不存在: {video_path}")

            if not audio_file.exists():
                raise HTTPException(status_code=404, detail=f"音频文件不存在: {audio_path}")

            Logger.info(f"开始一站式处理: 视频={video_path}, 音频={audio_path}")

            # 调用字幕生成模块
            result = await subtitle_module.generate_subtitles_advanced(
                input_type="path",
                video_path=video_path,
                audio_path=audio_path,
                model_name=model_name,
                device=device,
                generate_subtitle=True,
                bilingual=False,
                word_timestamps=False,
                burn_subtitles=burn_subtitles,
                beam_size=beam_size,
                out_basename=out_basename,
                flower_config=None,
                image_config=None,
                watermark_config=None,
                duration_reference="video",  # 以视频时长为准
                adjust_audio_speed=True,  # 自动调整音频语速
                audio_speed_factor=1.0,  # 自动计算语速倍数
                audio_volume=audio_volume,
                keep_original_audio=keep_original_audio,
                enable_llm_correction=enable_llm_correction,
                reference_text=reference_text,
                # Whisper 基础参数
                vad_filter=vad_filter,
                condition_on_previous_text=condition_on_previous_text,
                temperature=temperature,
                # 字幕显示参数（后处理）
                max_chars_per_line=max_chars_per_line,
                max_lines_per_segment=max_lines_per_segment
            )

            Logger.info(f"一站式处理完成: {result.get('out_basename', 'unknown')}")

            return result

        except HTTPException:
            raise
        except Exception as e:
            Logger.error(f"一站式处理失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

    @api_router.post("/video/tts_subtitle_video")
    async def tts_subtitle_video_process(
        video_path: str = Form(...),
        text_content: str = Form(...),
        feat_id: str = Form(None),
        cfg_value: float = Form(2.0),
        timesteps: int = Form(5),
        max_len: int = Form(2000),
        model_name: str = Form("small"),
        device: str = Form("cpu"),
        beam_size: int = Form(5),
        audio_volume: float = Form(1.0),
        keep_original_audio: bool = Form(False),
        enable_llm_correction: bool = Form(True),
        burn_subtitles: str = Form("hard"),
        # Whisper 基础参数
        vad_filter: bool = Form(True),
        condition_on_previous_text: bool = Form(False),
        temperature: float = Form(0.0),
        # 字幕显示参数（后处理）
        max_chars_per_line: int = Form(20),
        max_lines_per_segment: int = Form(2),
        out_basename: str = Form(None),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        文本转语音 + 字幕生成 + 音视频合成（一站式处理）

        自动进行以下操作：
        1. 使用 VoxCPM-1.5 ONNX 将文本转为语音（支持参考音频特征）
        2. 生成字幕文件（SRT格式）
        3. 如果启用LLM纠错，使用文本内容作为参考文本进行字幕纠错
        4. 将生成的音频与视频合成
        5. 如果需要，烧录字幕到视频

        Args:
            video_path: 视频文件路径
            text_content: 要合成的文本内容
            feat_id: 参考音频特征ID（可选）
            cfg_value: CFG引导强度（默认2.0）
            timesteps: Diffusion推理步数（默认5）
            max_len: 最大生成长度（默认2000）
            model_name: Whisper模型名称（默认small）
            device: 设备类型（默认cpu）
            beam_size: beam search大小（默认5）
            audio_volume: 音频音量倍数（默认1.0）
            keep_original_audio: 是否保留原视频音频（默认False）
            enable_llm_correction: 是否启用LLM字幕纠错（默认True）
            burn_subtitles: 字幕烧录类型 (none/hard，默认hard)
            out_basename: 输出文件名前缀
            vad_filter: 启用 VAD 语音活动检测（默认True）
            condition_on_previous_text: 不依赖前文分段（默认False），产生更自然的分段
            temperature: 温度参数（默认0.0），控制预测的随机性
            max_chars_per_line: 字幕每行最大字符数（默认20），超过会自动分割
            max_lines_per_segment: 字幕每段最大行数（默认2），超过会自动分割
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 处理结果，包含以下文件路径
                - audio_file: 生成的音频文件路径
                - subtitle_file: 生成的字幕文件路径
                - output_video: 合成的视频文件路径
        """
        try:
            from utils.file_utils import FileUtils
            
            # 验证视频文件路径
            video_file = Path(video_path)
            if not video_file.exists():
                raise HTTPException(status_code=404, detail=f"视频文件不存在: {video_path}")

            Logger.info(f"开始TTS+字幕+视频合成处理: 视频={video_path}, 文本长度={len(text_content)}, 特征ID={feat_id}")

            # 创建任务目录
            job_dir = FileUtils.create_job_dir()
            
            # 生成输出文件名
            if out_basename is None:
                out_basename = f"tts_video_{FileUtils.generate_job_id()}"
            
            # 1. 文本转语音（TTS）
            Logger.info("步骤1: 开始文本转语音...")
            audio_output_path = job_dir / f"{out_basename}_audio.wav"
            
            tts_result = await tts_onnx_module.synthesize(
                text=text_content,
                prompt_wav=None,
                prompt_text=None,
                feat_id=feat_id,
                cfg_value=cfg_value,
                min_len=2,
                max_len=max_len,
                timesteps=timesteps,
                output_path=audio_output_path
            )
            
            if not tts_result["success"]:
                raise HTTPException(status_code=500, detail=f"TTS合成失败: {tts_result.get('error', '未知错误')}")
            
            audio_file = tts_result["output_path"]
            Logger.info(f"TTS合成成功: {audio_file}, 时长: {tts_result.get('duration', 0):.2f}s")

            # 2. 字幕生成（使用同一个 job_dir）
            Logger.info("步骤2: 开始生成字幕...")
            subtitle_result = await subtitle_module.generate_subtitles_advanced(
                input_type="path",
                video_path=video_path,
                audio_path=audio_file,
                model_name=model_name,
                device=device,
                generate_subtitle=True,
                bilingual=False,
                word_timestamps=False,
                burn_subtitles="none",  # 先不烧录，等音视频合成后再处理
                beam_size=beam_size,
                out_basename=out_basename,
                flower_config=None,
                image_config=None,
                watermark_config=None,
                duration_reference="video",
                adjust_audio_speed=True,
                audio_speed_factor=1.0,
                audio_volume=audio_volume,
                keep_original_audio=keep_original_audio,
                enable_llm_correction=enable_llm_correction,
                reference_text=text_content,  # 使用输入的文本内容作为参考文本
                # Whisper 基础参数
                vad_filter=vad_filter,
                condition_on_previous_text=condition_on_previous_text,
                temperature=temperature,
                # 字幕显示参数（后处理）
                max_chars_per_line=max_chars_per_line,
                max_lines_per_segment=max_lines_per_segment,
                job_dir=job_dir  # 传递 job_dir，确保在同一个目录下处理
            )
            
            if not subtitle_result.get("success", False):
                raise HTTPException(status_code=500, detail=f"字幕生成失败: {subtitle_result.get('error', '未知错误')}")
            
            subtitle_file = subtitle_result.get("subtitle_path")
            temp_video = subtitle_result.get("video_with_subtitle_path")
            
            if not subtitle_file:
                raise HTTPException(status_code=500, detail="字幕生成失败：未找到字幕文件")
            
            Logger.info(f"字幕生成成功: {subtitle_file}, 临时视频: {temp_video}")

            # 3. 音视频合成（带字幕）
            Logger.info("步骤3: 开始音视频合成...")
            
            # 如果需要烧录字幕，重新处理
            if burn_subtitles == "hard":
                Logger.info("烧录字幕到视频...")
                output_video_path = job_dir / f"{out_basename}_final.mp4"
                
                # 检查临时视频文件是否存在
                if not temp_video or not Path(temp_video).exists():
                    Logger.warning(f"临时视频文件不存在: {temp_video}，使用原始视频")
                    temp_video = str(video_file)
                
                if not Path(temp_video).exists():
                    raise HTTPException(status_code=500, detail=f"视频文件不存在: {temp_video}")
                
                # 烧录字幕
                try:
                    MediaProcessor.burn_hardsub(
                        video_path=Path(temp_video),
                        srt_path=Path(subtitle_file),
                        output_path=output_video_path
                    )
                    output_video = str(output_video_path)
                    Logger.info(f"字幕烧录成功: {output_video}")
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"字幕烧录失败: {str(e)}")
            else:
                # 不烧录字幕，直接使用合成的视频
                if not temp_video or not Path(temp_video).exists():
                    raise HTTPException(status_code=500, detail="音视频合成失败：未找到输出视频文件")
                output_video = temp_video

            Logger.info(f"TTS+字幕+视频合成处理完成")

            # 返回所有生成的文件路径
            return {
                "success": True,
                "audio_file": str(audio_file),
                "subtitle_file": str(subtitle_file),
                "output_video": str(output_video),
                "out_basename": out_basename,
                "duration": tts_result.get("duration", 0),
                "sample_rate": tts_result.get("sample_rate", 0)
            }

        except HTTPException:
            raise
        except Exception as e:
            Logger.error(f"TTS+字幕+视频合成处理失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

    # ==================== 图像处理 ====================
    @api_router.post("/image/remove_background")
    async def remove_background(
        input_type: str = Form("upload"),
        image: UploadFile = File(None),
        image_path: str = Form(None),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        去除图片背景

        Args:
            input_type: 输入类型 (upload/path)
            image: 图片文件（upload模式）
            image_path: 图片文件路径（path模式，支持URL或本地路径）
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 去背景结果
        """
        from utils.file_utils import FileUtils
        job_dir = FileUtils.create_job_dir()

        actual_image_path = None

        if input_type == "upload":
            if not image:
                raise HTTPException(status_code=400, detail="请上传图片文件")
            image_file_path = job_dir / image.filename
            with open(image_file_path, "wb") as f:
                f.write(await image.read())
            actual_image_path = str(image_file_path)
        else:  # path
            if not image_path or not image_path.strip():
                raise HTTPException(status_code=400, detail="请提供图片文件路径")
            actual_image_path = image_path

        result = await image_processing_module.remove_background(
            image_path=actual_image_path,
            input_type=input_type,
            job_dir=job_dir
        )

        return result

    @api_router.post("/image/blend")
    async def blend_images(
        input_type: str = Form("upload"),
        base_image: UploadFile = File(None),
        overlay_image: UploadFile = File(None),
        base_image_path: str = Form(None),
        overlay_image_path: str = Form(None),
        position_x: int = Form(85),
        position_y: int = Form(90),
        scale: float = Form(1.0),
        width: int = Form(425),
        height: int = Form(615),
        remove_bg: bool = Form(False),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        图片混合：将第二张图片叠加到第一张图片上

        Args:
            input_type: 输入类型 (upload/path)
            base_image: 基础图片（upload模式）
            overlay_image: 叠加图片（upload模式）
            base_image_path: 基础图片路径（path模式，支持URL或本地路径）
            overlay_image_path: 叠加图片路径（path模式，支持URL或本地路径）
            position_x: X坐标
            position_y: Y坐标
            scale: 缩放比例（当width和height都为0时使用）
            width: 宽度（直接指定，优先级高于scale，0表示不指定）
            height: 高度（直接指定，优先级高于scale，0表示不指定）
            remove_bg: 是否去除叠加图片的背景
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 混合结果
        """
        from utils.file_utils import FileUtils
        job_dir = FileUtils.create_job_dir()

        actual_base_path = None
        actual_overlay_path = None

        if input_type == "upload":
            if not base_image or not overlay_image:
                raise HTTPException(status_code=400, detail="请上传两张图片文件")
            
            base_image_file_path = job_dir / base_image.filename
            overlay_image_file_path = job_dir / overlay_image.filename

            with open(base_image_file_path, "wb") as f:
                f.write(await base_image.read())

            with open(overlay_image_file_path, "wb") as f:
                f.write(await overlay_image.read())

            actual_base_path = str(base_image_file_path)
            actual_overlay_path = str(overlay_image_file_path)
        else:  # path
            if not base_image_path or not base_image_path.strip() or not overlay_image_path or not overlay_image_path.strip():
                raise HTTPException(status_code=400, detail="请提供两张图片的文件路径")
            actual_base_path = base_image_path
            actual_overlay_path = overlay_image_path

        # 处理宽高参数（0表示不指定）
        width_param = width if width > 0 else None
        height_param = height if height > 0 else None

        result = await image_processing_module.blend_images(
            base_image_path=actual_base_path,
            overlay_image_path=actual_overlay_path,
            input_type=input_type,
            position_x=position_x,
            position_y=position_y,
            scale=scale,
            width=width_param,
            height=height_param,
            remove_bg=remove_bg,
            job_dir=job_dir
        )

        return result

    @api_router.get("/image/model_info")
    async def get_image_model_info(
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        获取图像处理模型信息

        Args:
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 模型信息
        """
        return await image_processing_module.get_model_info()

    # ==================== 视频合并 ====================
    @api_router.post("/video_merge/merge")
    async def merge_videos(
        video_paths: str = Form(...),
        out_basename: str = Form(None),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        合并多个视频文件

        Args:
            video_paths: 视频文件路径列表，用换行符分隔
            out_basename: 输出文件名前缀
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 合并结果
        """
        from modules.video_merge_module import video_merge_module

        try:
            # 执行视频合并
            result = await video_merge_module.merge_videos(
                video_paths=video_paths,
                out_basename=out_basename
            )

            return result

        except Exception as e:
            Logger.error(f"视频合并失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"视频合并失败: {str(e)}")

    # 注册路由器到应用
    app.include_router(api_router)