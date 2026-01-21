"""
API 路由模块

定义所有 API 路由端点。
"""

from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import config
from api.auth import AuthService, verify_token
from api.response_formatter import response_formatter
from modules.whisper_service import whisper_service
from modules.tts_onnx_module import tts_onnx_module
from modules.subtitle_module import subtitle_module
from modules.transition_module import transition_module
from modules.video_editor_module import video_editor_module
from modules.image_processing_module import image_processing_module
from utils.logger import Logger
from utils.media_processor import MediaProcessor
import os


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
        try:
            if AuthService.verify_user(request.username, request.password):
                access_token = AuthService.create_access_token(
                    data={"sub": request.username}
                )
                return response_formatter.success(
                    data={
                        "access_token": access_token,
                        "token_type": "bearer"
                    },
                    message="登录成功"
                )
            else:
                return response_formatter.error(
                    message="用户名或密码错误",
                    error_code="INVALID_CREDENTIALS"
                )
        except Exception as e:
            return response_formatter.wrap_exception(e, "登录失败")

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
        try:
            model_info = whisper_service.get_model_info()
            return response_formatter.success(
                data=model_info,
                message="获取模型信息成功"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "获取模型信息失败")

    # ==================== 健康检查 ====================
    @api_router.get("/health")
    async def health_check() -> Dict[str, Any]:
        """
        健康检查

        Returns:
            Dict[str, Any]: 健康状态
        """
        try:
            return response_formatter.success(
                data={
                    "status": "healthy",
                    "service": "whisper-api"
                },
                message="服务正常"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "健康检查失败")

    # ==================== 语音转文字 ====================
    @api_router.post("/transcribe")
    async def transcribe(
        audio: UploadFile = File(...),
        model_name: str = Form('small'),
        device: str = Form('cpu'),
        compute_type: str = Form(None),
        beam_size: int = Form(5),
        task: str = Form("transcribe"),
        word_timestamps: bool = Form(True),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        语音转文字

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
        try:
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

            return response_formatter.success(
                data={
                    "segments": [
                        {
                            "start": seg.start,
                            "end": seg.end,
                            "text": seg.text,
                            "words": seg.words if hasattr(seg, 'words') else []
                        }
                        for seg in segments
                    ]
                },
                message="语音转文字成功"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "语音转文字失败")

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
        try:
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

            # 检查合成结果
            if result.get("success", False):
                return response_formatter.success(
                    data=result,
                    message="语音合成成功"
                )
            else:
                return response_formatter.error(
                    message=result.get("error", "语音合成失败"),
                    error_code="TTS_SYNTHESIZE_FAILED"
                )
        except Exception as e:
            return response_formatter.wrap_exception(e, "语音合成失败")

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
        try:
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

            # 检查结果
            if result.get("success", False):
                return response_formatter.success(
                    data=result,
                    message="保存参考音频特征成功"
                )
            else:
                return response_formatter.error(
                    message=result.get("error", "保存参考音频特征失败"),
                    error_code="SAVE_REF_AUDIO_FAILED"
                )
        except Exception as e:
            return response_formatter.wrap_exception(e, "保存参考音频特征失败")

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
        try:
            model_info = tts_onnx_module.get_model_info()
            return response_formatter.success(
                data=model_info,
                message="获取 TTS 模型信息成功"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "获取 TTS 模型信息失败")

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
        try:
            features = tts_onnx_module.list_ref_features()
            return response_formatter.success(
                data=features,
                message="获取参考音频特征列表成功"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "获取参考音频特征列表失败")

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
        bilingual: bool = Form(False),
        word_timestamps: bool = Form(True),
        burn_subtitles: str = Form("hard"),
        beam_size: int = Form(5),
        subtitle_bottom_margin: int = Form(50),
        out_basename: str = Form(None),
        # 音频音量控制
        audio_volume: float = Form(1.0),
        # 原音频保留配置
        keep_original_audio: bool = Form(True),
        # LLM 字幕纠错配置
        enable_llm_correction: bool = Form(True),
        reference_text: str = Form(None),
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

    # ==================== 文件操作 ====================
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
        try:
            from utils.file_utils import FileUtils

            # 确保上传目录存在
            upload_dir = Path(config.UPLOAD_FOLDER)
            upload_dir.mkdir(parents=True, exist_ok=True)

            # 生成安全的文件名
            filename = file.filename
            if not filename:
                return response_formatter.error(
                    message="文件名不能为空",
                    error_code="INVALID_FILENAME"
                )

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

            return response_formatter.success(
                data={
                    "filename": file_path.name,
                    "filepath": str(file_path.absolute()),
                    "size": file_path.stat().st_size
                },
                message="文件上传成功"
            )

        except Exception as e:
            Logger.error(f"文件上传失败: {e}")
            return response_formatter.wrap_exception(e, "文件上传失败")

    # ==================== 视频转场 ====================
    @api_router.post("/transition/apply")
    async def apply_transition(
        video1: UploadFile = File(...),
        video2: UploadFile = File(...),
        transition_name: str = Form("crossfade"),
        total_frames: int = Form(100),
        fps: int = Form(25),
        width: int = Form(600),
        height: int = Form(800),
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
        try:
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

            # 检查结果
            if result.get("success", False):
                return response_formatter.success(
                    data=result,
                    message="转场效果应用成功"
                )
            else:
                return response_formatter.error(
                    message=result.get("error", "转场效果应用失败"),
                    error_code="TRANSITION_APPLY_FAILED"
                )
        except Exception as e:
            return response_formatter.wrap_exception(e, "转场效果应用失败")

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
        try:
            transitions = transition_module.get_available_transitions()
            return response_formatter.success(
                data={"transitions": transitions},
                message="获取转场效果列表成功"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "获取转场效果列表失败")

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
        try:
            params = transition_module.get_transition_params(transition_name)
            return response_formatter.success(
                data={"params": params},
                message="获取转场参数配置成功"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "获取转场参数配置失败")

    # ==================== 视频编辑 ====================
    @api_router.post("/video_editor/apply_effects")
    async def apply_video_effects(
        input_type: str = Form("upload"),
        video_file: UploadFile = File(None),
        video_path: str = Form(None),
        audio_file: UploadFile = File(None),
        audio_path: str = Form(None),
        # 花字配置
        flower_text: str = Form(None),
        flower_font: str = Form("Microsoft YaHei"),
        flower_size: int = Form(40),
        flower_color: str = Form("#FFFFFF"),
        flower_color_mode: str = Form("单色"),
        flower_gradient_type: str = Form("水平渐变"),
        flower_color_start: str = Form("#FF0000"),
        flower_color_end: str = Form("#0000FF"),
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
        flower_animation_enabled: bool = Form(False),
        flower_animation_type: str = Form("无效果"),
        flower_animation_speed: float = Form(1.0),
        flower_animation_amplitude: float = Form(20.0),
        flower_animation_direction: str = Form("left"),
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
        # 插视频配置
        video_path_to_insert: str = Form(None),
        video_x: int = Form(10),
        video_y: int = Form(10),
        video_width: int = Form(200),
        video_height: int = Form(150),
        video_timing_type: str = Form("时间戳范围"),
        video_start_frame: int = Form(0),
        video_end_frame: int = Form(999999),
        video_start_time: str = Form("00:00:00"),
        video_end_time: str = Form("99:59:59"),
        # 水印配置
        watermark_text: str = Form(None),
        watermark_font: str = Form("黑体.TTF"),
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
            audio_file: 上传的音频文件
            audio_path: 音频文件路径
            flower_text: 花字文字
            flower_font: 花字字体
            flower_size: 花字大小
            flower_color: 花字颜色
            flower_color_mode: 花字颜色模式
            flower_gradient_type: 渐变类型
            flower_color_start: 渐变起始颜色
            flower_color_end: 渐变结束颜色
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
            flower_animation_enabled: 是否启用花字动画
            flower_animation_type: 花字动画类型
            flower_animation_speed: 花字动画速度
            flower_animation_amplitude: 花字动画幅度
            flower_animation_direction: 花字动画方向
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
            video_path_to_insert: 插入的视频路径
            video_x: 插视频X坐标
            video_y: 插视频Y坐标
            video_width: 插视频宽度
            video_height: 插视频高度
            video_timing_type: 插视频时机类型
            video_start_frame: 插视频起始帧
            video_end_frame: 插视频结束帧
            video_start_time: 插视频起始时间
            video_end_time: 插视频结束时间
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
        try:
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
                    'color_mode': flower_color_mode,
                    'color': flower_color,
                    'gradient_type': flower_gradient_type,
                    'color_start': flower_color_start,
                    'color_end': flower_color_end,
                    'x': flower_x,
                    'y': flower_y,
                    'timing_type': flower_timing_type,
                    'start_frame': flower_start_frame,
                    'end_frame': flower_end_frame,
                    'start_time': flower_start_time,
                    'end_time': flower_end_time,
                    'stroke_enabled': flower_stroke_enabled,
                    'stroke_color': flower_stroke_color,
                    'stroke_width': flower_stroke_width,
                    'animation_enabled': flower_animation_enabled,
                    'animation_type': flower_animation_type,
                    'animation_speed': flower_animation_speed,
                    'animation_amplitude': flower_animation_amplitude,
                    'animation_direction': flower_animation_direction
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

            # 准备插视频配置
            video_config = None
            if video_path_to_insert and video_path_to_insert.strip():
                video_config = {
                    'path': video_path_to_insert,
                    'x': video_x,
                    'y': video_y,
                    'width': video_width,
                    'height': video_height,
                    'timing_type': video_timing_type,
                    'start_frame': video_start_frame,
                    'end_frame': video_end_frame,
                    'start_time': video_start_time,
                    'end_time': video_end_time
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
                audio_file=str(audio_file_path) if audio_file_path else None,
                audio_path=audio_path,
                flower_config=flower_config,
                image_config=image_config,
                video_config=video_config,
                watermark_config=watermark_config,
                out_basename=out_basename,
                job_dir=job_dir  # 传递 job_dir，确保在同一个目录下处理
            )

            # 检查结果
            if result.get("success", False):
                return response_formatter.success(
                    data=result,
                    message="视频效果应用成功"
                )
            else:
                return response_formatter.error(
                    message=result.get("error", "视频效果应用失败"),
                    error_code="VIDEO_EFFECTS_APPLY_FAILED"
                )
        except Exception as e:
            return response_formatter.wrap_exception(e, "视频效果应用失败")

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
        try:
            effects = video_editor_module.get_available_effects()
            return response_formatter.success(
                data=effects,
                message="获取视频效果列表成功"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "获取视频效果列表失败")

    @api_router.post("/video_editor/watermark")
    async def add_watermark(
        video: UploadFile = File(...),
        watermark_text: str = Form(None),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        为视频添加水印

        Args:
            video: 视频文件
            watermark_text: 水印文字
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 添加水印结果
        """
        try:
            from utils.file_utils import FileUtils
            job_dir = FileUtils.create_job_dir()
            video_path = job_dir / video.filename

            with open(video_path, "wb") as f:
                f.write(await video.read())

            # 构建水印配置
            watermark_config = None
            if watermark_text and watermark_text.strip():
                watermark_config = {
                    'text': watermark_text,
                    'font': 'Arial',
                    'size': 20,
                    'color': '#FFFFFF',
                    'timing_type': '时间戳范围',
                    'start_time': '00:00:00',
                    'end_time': '99:59:59',
                    'style': '半透明浮动'
                }

            # 使用 path 模式，避免重复复制文件
            result = await video_editor_module.apply_video_effects(
                input_type="path",
                video_path=str(video_path),
                watermark_config=watermark_config,
                out_basename="watermark",
                job_dir=job_dir
            )

            # 检查结果
            if result.get("success", False):
                return response_formatter.success(
                    data=result,
                    message="水印添加成功"
                )
            else:
                return response_formatter.error(
                    message=result.get("error", "水印添加失败"),
                    error_code="WATERMARK_ADD_FAILED"
                )
        except Exception as e:
            return response_formatter.wrap_exception(e, "水印添加失败")

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
        try:
            from utils.file_utils import FileUtils
            job_dir = FileUtils.create_job_dir()

            actual_image_path = None

            if input_type == "upload":
                if not image:
                    return response_formatter.error(
                        message="请上传图片文件",
                        error_code="NO_IMAGE_UPLOADED"
                    )
                image_file_path = job_dir / image.filename
                with open(image_file_path, "wb") as f:
                    f.write(await image.read())
                actual_image_path = str(image_file_path)
            else:  # path
                if not image_path or not image_path.strip():
                    return response_formatter.error(
                        message="请提供图片文件路径",
                        error_code="NO_IMAGE_PATH"
                    )
                actual_image_path = image_path

            result = await image_processing_module.remove_background(
                image_path=actual_image_path,
                input_type=input_type,
                job_dir=job_dir
            )

            # 检查结果
            if result.get("success", False):
                return response_formatter.success(
                    data=result,
                    message="去除图片背景成功"
                )
            else:
                return response_formatter.error(
                    message=result.get("error", "去除图片背景失败"),
                    error_code="REMOVE_BACKGROUND_FAILED"
                )
        except Exception as e:
            return response_formatter.wrap_exception(e, "去除图片背景失败")

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
        try:
            from utils.file_utils import FileUtils
            job_dir = FileUtils.create_job_dir()

            actual_base_path = None
            actual_overlay_path = None

            if input_type == "upload":
                if not base_image or not overlay_image:
                    return response_formatter.error(
                        message="请上传两张图片文件",
                        error_code="NO_IMAGES_UPLOADED"
                    )

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
                    return response_formatter.error(
                        message="请提供两张图片的文件路径",
                        error_code="NO_IMAGE_PATHS"
                    )
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

            # 检查结果
            if result.get("success", False):
                return response_formatter.success(
                    data=result,
                    message="图片混合成功"
                )
            else:
                return response_formatter.error(
                    message=result.get("error", "图片混合失败"),
                    error_code="BLEND_IMAGES_FAILED"
                )
        except Exception as e:
            return response_formatter.wrap_exception(e, "图片混合失败")

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
        try:
            model_info = await image_processing_module.get_model_info()
            return response_formatter.success(
                data=model_info,
                message="获取图像处理模型信息成功"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "获取图像处理模型信息失败")

    # ==================== 视频合并 ====================
    @api_router.post("/video_merge/merge")
    async def merge_videos(
        video_paths: str = Form(...),
        out_basename: str = Form(None),
        delete_intermediate_videos: bool = Form(True),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        合并多个视频文件

        Args:
            video_paths: 视频文件路径列表，用换行符分隔
            out_basename: 输出文件名前缀
            delete_intermediate_videos: 是否删除中间视频文件（默认为True）
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 合并结果
        """
        try:
            from modules.video_merge_module import video_merge_module

            # 执行视频合并
            result = await video_merge_module.merge_videos(
                video_paths=video_paths,
                out_basename=out_basename,
                delete_intermediate_videos=delete_intermediate_videos
            )

            # 检查结果
            if result.get("success", False):
                return response_formatter.success(
                    data=result,
                    message="视频合并成功"
                )
            else:
                return response_formatter.error(
                    message=result.get("error", "视频合并失败"),
                    error_code="MERGE_VIDEOS_FAILED"
                )

        except Exception as e:
            Logger.error(f"视频合并失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            return response_formatter.wrap_exception(e, "视频合并失败")

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
                return response_formatter.error(
                    message=f"视频文件不存在: {video_path}",
                    error_code="VIDEO_FILE_NOT_FOUND"
                )

            if not audio_file.exists():
                return response_formatter.error(
                    message=f"音频文件不存在: {audio_path}",
                    error_code="AUDIO_FILE_NOT_FOUND"
                )

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

            # 检查结果
            if result.get("success", False):
                return response_formatter.success(
                    data=result,
                    message="一站式音视频处理成功"
                )
            else:
                return response_formatter.error(
                    message=result.get("error", "一站式音视频处理失败"),
                    error_code="COMPLETE_PROCESS_FAILED"
                )

        except Exception as e:
            Logger.error(f"一站式处理失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            return response_formatter.wrap_exception(e, "一站式音视频处理失败")

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
        keep_original_audio: bool = Form(True),
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
                return response_formatter.error(
                    message=f"视频文件不存在: {video_path}",
                    error_code="VIDEO_FILE_NOT_FOUND"
                )

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
                return response_formatter.error(
                    message=f"TTS合成失败: {tts_result.get('error', '未知错误')}",
                    error_code="TTS_SYNTHESIZE_FAILED"
                )

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
                return response_formatter.error(
                    message=f"字幕生成失败: {subtitle_result.get('error', '未知错误')}",
                    error_code="SUBTITLE_GENERATE_FAILED"
                )

            subtitle_file = subtitle_result.get("subtitle_path")
            temp_video = subtitle_result.get("video_with_subtitle_path")

            if not subtitle_file:
                return response_formatter.error(
                    message="字幕生成失败：未找到字幕文件",
                    error_code="SUBTITLE_FILE_NOT_FOUND"
                )

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
                    return response_formatter.error(
                        message=f"视频文件不存在: {temp_video}",
                        error_code="VIDEO_FILE_NOT_FOUND"
                    )

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
                    return response_formatter.error(
                        message=f"字幕烧录失败: {str(e)}",
                        error_code="BURN_SUBTITLE_FAILED"
                    )
            else:
                # 不烧录字幕，直接使用合成的视频
                if not temp_video or not Path(temp_video).exists():
                    return response_formatter.error(
                        message="音视频合成失败：未找到输出视频文件",
                        error_code="OUTPUT_VIDEO_NOT_FOUND"
                    )
                output_video = temp_video

            Logger.info(f"TTS+字幕+视频合成处理完成")

            # 返回所有生成的文件路径
            return response_formatter.success(
                data={
                    "audio_file": str(audio_file),
                    "subtitle_file": str(subtitle_file),
                    "output_video": str(output_video),
                    "out_basename": out_basename,
                    "duration": tts_result.get("duration", 0),
                    "sample_rate": tts_result.get("sample_rate", 0)
                },
                message="TTS+字幕+视频合成处理成功"
            )

        except Exception as e:
            Logger.error(f"TTS+字幕+视频合成处理失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            return response_formatter.wrap_exception(e, "TTS+字幕+视频合成处理失败")

    # ==================== 模板管理 ====================
    @api_router.get("/templates")
    async def get_all_templates(
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        获取所有模板的列表

        Args:
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 模板列表
        """
        try:
            from modules.template_manager import template_manager

            templates = template_manager.get_all_templates()
            return response_formatter.success(
                data={
                    "count": len(templates),
                    "templates": templates
                },
                message="获取模板列表成功"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "获取模板列表失败")

    @api_router.get("/templates/{template_name}")
    async def get_template(
        template_name: str,
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        获取指定模板的详细信息

        Args:
            template_name: 模板名称
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 模板详细信息
        """
        try:
            from modules.template_manager import template_manager

            template = template_manager.get_template(template_name)
            if not template:
                return response_formatter.error(
                    message=f"模板不存在: {template_name}",
                    error_code="TEMPLATE_NOT_FOUND"
                )

            return response_formatter.success(
                data=template,
                message="获取模板详情成功"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "获取模板详情失败")

    @api_router.post("/templates/{template_name}")
    async def save_template(
        template_name: str,
        template_data: Dict[str, Any],
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        保存模板（新建或更新）

        Args:
            template_name: 模板名称
            template_data: 模板数据
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            from modules.template_manager import template_manager

            # 验证模板数据
            required_fields = ["name", "description", "version", "tasks"]
            for field in required_fields:
                if field not in template_data:
                    return response_formatter.error(
                        message=f"缺少必需字段: {field}",
                        error_code="INVALID_TEMPLATE"
                    )

            # 保存模板
            template_manager.save_template(template_name, template_data)

            return response_formatter.success(
                message=f"模板 '{template_name}' 保存成功"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "保存模板失败")

    @api_router.delete("/templates/{template_name}")
    async def delete_template(
        template_name: str,
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        删除模板

        Args:
            template_name: 模板名称
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            from modules.template_manager import template_manager

            template_manager.delete_template(template_name)

            return response_formatter.success(
                message=f"模板 '{template_name}' 删除成功"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "删除模板失败")

    @api_router.post("/templates/{template_name}/resources")
    async def upload_template_resource(
        template_name: str,
        file: UploadFile = File(...),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        上传模板资源文件

        Args:
            template_name: 模板名称
            file: 上传的文件
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            from modules.template_manager import template_manager

            # 获取模板目录
            template = template_manager.get_template(template_name)
            if not template:
                return response_formatter.error(
                    message=f"模板不存在: {template_name}",
                    error_code="TEMPLATE_NOT_FOUND"
                )

            template_dir = Path(template.get("template_dir", ""))
            if not template_dir.exists():
                template_dir.mkdir(parents=True, exist_ok=True)

            # 保存文件
            file_path = template_dir / file.filename
            with open(file_path, "wb") as f:
                f.write(await file.read())

            return response_formatter.success(
                message=f"文件 '{file.filename}' 上传成功",
                data={"file_path": str(file_path)}
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "上传资源文件失败")

    @api_router.get("/templates/{template_name}/resources")
    async def get_template_resources(
        template_name: str,
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        获取模板资源文件列表

        Args:
            template_name: 模板名称
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 资源文件列表
        """
        try:
            from modules.template_manager import template_manager

            template = template_manager.get_template(template_name)
            if not template:
                return response_formatter.error(
                    message=f"模板不存在: {template_name}",
                    error_code="TEMPLATE_NOT_FOUND"
                )

            template_dir = Path(template.get("template_dir", ""))
            if not template_dir.exists():
                return response_formatter.success(
                    data={"count": 0, "resources": []},
                    message="模板目录不存在"
                )

            # 获取所有文件
            resources = []
            for file in template_dir.iterdir():
                if file.is_file():
                    resources.append({
                        "name": file.name,
                        "path": str(file),
                        "size": file.stat().st_size
                    })

            return response_formatter.success(
                data={
                    "count": len(resources),
                    "resources": resources
                },
                message="获取资源文件列表成功"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "获取资源文件列表失败")

    @api_router.get("/templates/{template_name}/resources/{resource_name}")
    async def download_template_resource(
        template_name: str,
        resource_name: str,
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> FileResponse:
        """
        下载模板资源文件

        Args:
            template_name: 模板名称
            resource_name: 资源文件名
            payload: 认证载荷

        Returns:
            FileResponse: 文件响应
        """
        from modules.template_manager import template_manager

        template = template_manager.get_template(template_name)
        if not template:
            raise HTTPException(status_code=404, detail=f"模板不存在: {template_name}")

        template_dir = Path(template.get("template_dir", ""))
        file_path = template_dir / resource_name

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"资源文件不存在: {resource_name}")

        return FileResponse(
            path=str(file_path),
            filename=resource_name,
            media_type="application/octet-stream"
        )

    # ==================== 综合处理（基于模板） ====================
    @api_router.get("/batch/templates")
    async def list_templates(
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        获取所有可用的模板列表

        Args:
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 模板列表
        """
        try:
            from modules.template_manager import template_manager

            templates = []
            for template_name in template_manager.get_template_names():
                template_info = template_manager.get_template_info(template_name)
                templates.append({
                    "name": template_info.get("name"),
                    "description": template_info.get("description"),
                    "version": template_info.get("version"),
                    "character": template_info.get("character"),
                    "theme": template_info.get("theme"),
                    "task_count": template_info.get("task_count"),
                    "parameters": list(template_info.get("parameters", {}).keys())
                })

            return response_formatter.success(
                data={
                    "count": len(templates),
                    "templates": templates
                },
                message="获取模板列表成功"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "获取模板列表失败")

    @api_router.get("/batch/template/{template_name}")
    async def get_template_detail(
        template_name: str,
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        获取指定模板的详细信息

        Args:
            template_name: 模板名称
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 模板详细信息
        """
        try:
            from modules.template_manager import template_manager

            template_info = template_manager.get_template_info(template_name)
            if not template_info:
                return response_formatter.error(
                    message=f"模板不存在: {template_name}",
                    error_code="TEMPLATE_NOT_FOUND"
                )

            return response_formatter.success(
                data={"template": template_info},
                message="获取模板详细信息成功"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "获取模板详细信息失败")

    @api_router.post("/batch/execute")
    async def execute_template(
        template_name: str = Form(...),
        username: str = Form(""),
        age: int = Form(6),
        theme: str = Form("生日快乐"),
        character: str = Form("奥特曼"),
        sub_character: str = Form(""),
        tts_text: str = Form(""),
        user_images: UploadFile = File(None),
        user_images_paths: str = Form(None),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        执行模板（综合处理）

        Args:
            template_name: 模板名称
            username: 用户名
            age: 年龄
            theme: 主题文字
            character: 操作模板对象
            sub_character: 二级对象
            tts_text: TTS文本内容
            user_images: 上传的用户图片文件（最多6张）
            user_images_paths: 用户图片路径（多行文本，每行一个路径）
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            from modules.task_orchestrator import task_orchestrator
            from utils.file_utils import FileUtils

            # 验证模板是否存在
            from modules.template_manager import template_manager
            if not template_manager.get_template(template_name):
                return response_formatter.error(
                    message=f"模板不存在: {template_name}",
                    error_code="TEMPLATE_NOT_FOUND"
                )

            # 创建任务目录
            job_dir = FileUtils.create_job_dir()

            # 准备参数
            parameters = {
                "username": username,
                "age": age,
                "theme": theme,
                "character": character,
                "sub_character": sub_character,
                "tts_text": tts_text,
                "user_images": []
            }

            # 处理用户图片 - 优先使用上传方式
            if user_images:
                # 处理上传的图片
                if hasattr(user_images, 'filename'):
                    # 单个文件
                    image_path = job_dir / user_images.filename
                    with open(image_path, "wb") as f:
                        f.write(await user_images.read())
                    parameters["user_images"].append(str(image_path))
            elif user_images_paths and user_images_paths.strip():
                # 使用路径输入方式
                paths = [p.strip() for p in user_images_paths.strip().split('\n') if p.strip()]
                for path in paths[:6]:  # 最多6张图片
                    parameters["user_images"].append(path)

            # 进度回调（用于日志记录）
            async def progress_callback(progress_info):
                Logger.info(f"任务进度: {progress_info['task_name']} - {progress_info['completed']}/{progress_info['total']} ({progress_info['progress']:.1%})")

            # 执行模板
            result = await task_orchestrator.execute_template(
                template_name,
                parameters,
                progress_callback
            )

            # 使用统一的结果格式化工具
            from utils.result_formatter import result_formatter
            formatted_result = result_formatter.format_template_result(result)

            # 检查结果
            if formatted_result.get("success", False):
                return response_formatter.success(
                    data=formatted_result,
                    message="模板执行成功"
                )
            else:
                return response_formatter.error(
                    message=formatted_result.get("error", "模板执行失败"),
                    error_code="TEMPLATE_EXECUTE_FAILED"
                )

        except Exception as e:
            Logger.error(f"模板执行失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            return response_formatter.wrap_exception(e, "模板执行失败")

    @api_router.post("/batch/execute_json")
    async def execute_template_json(
        request: Dict[str, Any],
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        执行模板（JSON格式，适合程序化调用）

        Args:
            request: JSON格式的请求体，包含：
                - template_name: 模板名称
                - parameters: 模板参数字典
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            from modules.task_orchestrator import task_orchestrator
            from modules.template_manager import template_manager
            from utils.file_utils import FileUtils

            template_name = request.get("template_name")
            parameters = request.get("parameters", {})

            # 验证模板是否存在
            if not template_manager.get_template(template_name):
                return response_formatter.error(
                    message=f"模板不存在: {template_name}",
                    error_code="TEMPLATE_NOT_FOUND"
                )

            # 创建任务目录
            job_dir = FileUtils.create_job_dir()
            parameters["job_dir"] = str(job_dir)

            # 进度回调（用于日志记录）
            async def progress_callback(progress_info):
                Logger.info(f"任务进度: {progress_info['task_name']} - {progress_info['completed']}/{progress_info['total']} ({progress_info['progress']:.1%})")

            # 执行模板
            result = await task_orchestrator.execute_template(
                template_name,
                parameters,
                progress_callback
            )

            # 使用统一的结果格式化工具
            from utils.result_formatter import result_formatter
            formatted_result = result_formatter.format_template_result(result)

            # 检查结果
            if formatted_result.get("success", False):
                return response_formatter.success(
                    data=formatted_result,
                    message="模板执行成功"
                )
            else:
                return response_formatter.error(
                    message=formatted_result.get("error", "模板执行失败"),
                    error_code="TEMPLATE_EXECUTE_FAILED"
                )

        except Exception as e:
            Logger.error(f"模板执行失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            return response_formatter.wrap_exception(e, "模板执行失败")

    # ==================== 文件持久化 ====================
    @api_router.get("/persistence/platforms")
    async def get_available_platforms(payload: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
        """
        获取可用的持久化平台列表

        Args:
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 可用平台列表
        """
        try:
            from modules.file_persistence import get_persistence_manager
            manager = get_persistence_manager()

            if not manager:
                return response_formatter.error(
                    message="文件持久化管理器未初始化",
                    error_code="PERSISTENCE_MANAGER_NOT_INITIALIZED"
                )

            platforms = manager.get_available_platforms()

            return response_formatter.success(
                data={
                    "platforms": platforms,
                    "count": len(platforms)
                },
                message="获取可用平台成功"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "获取可用平台失败")

    @api_router.post("/persistence/upload_file")
    async def upload_file_to_platform(
        file_path: str = Form(...),
        platform: str = Form("modelscope"),
        repo_id: str = Form(...),
        path_in_repo: str = Form(None),
        repo_type: str = Form("dataset"),
        commit_message: str = Form("Upload file"),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        上传单个文件到指定平台

        Args:
            file_path: 本地文件路径
            platform: 平台名称 (huggingface/modelscope)
            repo_id: 仓库 ID
            path_in_repo: 仓库中的文件路径（可选）
            repo_type: 仓库类型
            commit_message: 提交消息
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 上传结果
        """
        try:
            from modules.file_persistence import get_persistence_manager
            manager = get_persistence_manager()

            if not manager:
                return response_formatter.error(
                    message="文件持久化管理器未初始化",
                    error_code="PERSISTENCE_MANAGER_NOT_INITIALIZED"
                )

            result = manager.upload_single_file(
                file_path=file_path,
                platform=platform,
                repo_id=repo_id,
                path_in_repo=path_in_repo,
                repo_type=repo_type,
                commit_message=commit_message
            )

            if result.success:
                return response_formatter.success(
                    data={
                        "platform": result.platform,
                        "repo_id": result.repo_id,
                        "file_path": result.file_path,
                        "repo_url": result.repo_url,
                        "download_url": result.download_url,
                        "message": result.message
                    },
                    message="文件上传成功"
                )
            else:
                return response_formatter.error(
                    message=result.error or "文件上传失败",
                    error_code="FILE_UPLOAD_FAILED"
                )
        except Exception as e:
            return response_formatter.wrap_exception(e, "文件上传失败")

    @api_router.post("/persistence/upload_folder")
    async def upload_folder_to_platform(
        folder_path: str = Form(...),
        platform: str = Form("modelscope"),
        repo_id: str = Form(...),
        path_in_repo: str = Form(""),
        repo_type: str = Form("dataset"),
        commit_message: str = Form("Upload folder"),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        上传文件夹到指定平台

        Args:
            folder_path: 本地文件夹路径
            platform: 平台名称
            repo_id: 仓库 ID
            path_in_repo: 仓库中的文件夹路径
            repo_type: 仓库类型
            commit_message: 提交消息
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 上传结果
        """
        try:
            from modules.file_persistence import get_persistence_manager
            manager = get_persistence_manager()

            if not manager:
                return response_formatter.error(
                    message="文件持久化管理器未初始化",
                    error_code="PERSISTENCE_MANAGER_NOT_INITIALIZED"
                )

            result = manager.upload_folder(
                folder_path=folder_path,
                platform=platform,
                repo_id=repo_id,
                path_in_repo=path_in_repo,
                repo_type=repo_type,
                commit_message=commit_message
            )

            if result.success:
                return response_formatter.success(
                    data={
                        "platform": result.platform,
                        "repo_id": result.repo_id,
                        "file_path": result.file_path,
                        "repo_url": result.repo_url,
                        "download_url": result.download_url,
                        "message": result.message
                    },
                    message="文件夹上传成功"
                )
            else:
                return response_formatter.error(
                    message=result.error or "文件夹上传失败",
                    error_code="FOLDER_UPLOAD_FAILED"
                )
        except Exception as e:
            return response_formatter.wrap_exception(e, "文件夹上传失败")

    @api_router.post("/persistence/batch_upload")
    async def batch_upload_files_to_platform(
        request: Dict[str, Any],
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        批量上传多个文件到指定平台

        Args:
            request: 请求体，包含：
                - file_paths: 文件路径列表
                - platform: 平台名称
                - repo_id: 仓库 ID
                - repo_type: 仓库类型
                - commit_message: 提交消息
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 批量上传结果
        """
        try:
            from modules.file_persistence import get_persistence_manager
            manager = get_persistence_manager()

            if not manager:
                return response_formatter.error(
                    message="文件持久化管理器未初始化",
                    error_code="PERSISTENCE_MANAGER_NOT_INITIALIZED"
                )

            file_paths = request.get("file_paths", [])
            platform = request.get("platform", "modelscope")
            repo_id = request.get("repo_id")
            repo_type = request.get("repo_type", "dataset")
            commit_message = request.get("commit_message", "Batch upload files")

            if not file_paths:
                return response_formatter.error(
                    message="文件路径列表不能为空",
                    error_code="EMPTY_FILE_LIST"
                )

            results = manager.batch_upload_files(
                file_paths=file_paths,
                platform=platform,
                repo_id=repo_id,
                repo_type=repo_type,
                commit_message=commit_message
            )

            # 统计结果
            success_count = sum(1 for r in results if r.success)
            failed_count = len(results) - success_count

            return response_formatter.success(
                data={
                    "total": len(results),
                    "success": success_count,
                    "failed": failed_count,
                    "results": [
                        {
                            "file_path": os.path.basename(fp),
                            "success": r.success,
                            "platform": r.platform,
                            "repo_id": r.repo_id,
                            "file_path_in_repo": r.file_path,
                            "repo_url": r.repo_url,
                            "download_url": r.download_url,
                            "message": r.message,
                            "error": r.error
                        }
                        for fp, r in zip(file_paths, results)
                    ]
                },
                message=f"批量上传完成：成功 {success_count} 个，失败 {failed_count} 个"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "批量上传失败")

    # ==================== ComfyUI 集成 ====================
    @api_router.get("/comfyui/test")
    async def test_comfyui_connection(
        server_url: str = Query("http://127.0.0.1:8188", description="ComfyUI 服务器地址"),
        auth_token: Optional[str] = Query(None, description="ComfyUI 认证 Token"),
        username: Optional[str] = Query(None, description="ComfyUI 用户名"),
        password: Optional[str] = Query(None, description="ComfyUI 密码"),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        测试 ComfyUI 连接

        Args:
            server_url: ComfyUI 服务器地址
            auth_token: ComfyUI 认证 Token
            username: ComfyUI 用户名
            password: ComfyUI 密码
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 测试结果
        """
        try:
            from modules.comfyui_module import comfyui_module

            result = await comfyui_module.test_connection(
                server_url=server_url,
                auth_token=auth_token,
                username=username,
                password=password
            )

            return response_formatter.success(
                data=result,
                message="连接测试完成"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "连接测试失败")

    @api_router.get("/comfyui/nodes")
    async def get_comfyui_nodes(
        server_url: str = Query("http://127.0.0.1:8188", description="ComfyUI 服务器地址"),
        auth_token: Optional[str] = Query(None, description="ComfyUI 认证 Token"),
        username: Optional[str] = Query(None, description="ComfyUI 用户名"),
        password: Optional[str] = Query(None, description="ComfyUI 密码"),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        获取 ComfyUI 可用节点列表

        Args:
            server_url: ComfyUI 服务器地址
            auth_token: ComfyUI 认证 Token
            username: ComfyUI 用户名
            password: ComfyUI 密码
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 节点列表
        """
        try:
            from modules.comfyui_module import comfyui_module

            result = await comfyui_module.get_available_nodes(
                server_url=server_url,
                auth_token=auth_token,
                username=username,
                password=password
            )

            return response_formatter.success(
                data=result,
                message="获取节点列表成功"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "获取节点列表失败")

    @api_router.post("/comfyui/execute")
    async def execute_comfyui_workflow(
        workflow_json: str = Form(..., description="工作流 JSON"),
        server_url: str = Form("http://127.0.0.1:8188", description="ComfyUI 服务器地址"),
        auth_token: Optional[str] = Form(None, description="ComfyUI 认证 Token"),
        username: Optional[str] = Form(None, description="ComfyUI 用户名"),
        password: Optional[str] = Form(None, description="ComfyUI 密码"),
        timeout: int = Form(300, description="超时时间（秒）"),
        upload_files_json: Optional[str] = Form(None, description="上传文件 JSON (可选)"),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        执行 ComfyUI 工作流

        Args:
            workflow_json: 工作流 JSON 字符串
            server_url: ComfyUI 服务器地址
            auth_token: ComfyUI 认证 Token
            username: ComfyUI 用户名
            password: ComfyUI 密码
            upload_files_json: 上传文件 JSON，格式为 {"filename": "filepath"}
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            from modules.comfyui_module import comfyui_module

            # 解析上传文件
            upload_files = None
            if upload_files_json:
                try:
                    upload_files = json.loads(upload_files_json)
                except json.JSONDecodeError:
                    return response_formatter.error(
                        message="上传文件 JSON 格式无效",
                        error_code="INVALID_UPLOAD_FILES_JSON"
                    )

            result = await comfyui_module.execute_workflow_from_json(
                workflow_json=workflow_json,
                server_url=server_url,
                auth_token=auth_token,
                username=username,
                password=password,
                upload_files=upload_files,
                timeout=timeout
            )

            if result.get("success"):
                return response_formatter.success(
                    data=result,
                    message="工作流执行成功"
                )
            else:
                return response_formatter.error(
                    message=result.get("error", "工作流执行失败"),
                    error_code="WORKFLOW_EXECUTION_FAILED"
                )
        except Exception as e:
            return response_formatter.wrap_exception(e, "工作流执行失败")

    @api_router.post("/comfyui/upload")
    async def upload_file_to_comfyui(
        file: UploadFile = File(..., description="要上传的文件"),
        filename: Optional[str] = Form(None, description="上传后的文件名（可选）"),
        server_url: str = Form("http://127.0.0.1:8188", description="ComfyUI 服务器地址"),
        auth_token: Optional[str] = Form(None, description="ComfyUI 认证 Token"),
        username: Optional[str] = Form(None, description="ComfyUI 用户名"),
        password: Optional[str] = Form(None, description="ComfyUI 密码"),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        上传文件到 ComfyUI 服务器

        Args:
            file: 要上传的文件
            filename: 上传后的文件名（可选）
            server_url: ComfyUI 服务器地址
            auth_token: ComfyUI 认证 Token
            username: ComfyUI 用户名
            password: ComfyUI 密码
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 上传结果
        """
        try:
            from modules.comfyui_module import comfyui_module
            from utils.file_utils import FileUtils
            import tempfile

            # 创建临时文件保存上传的内容
            job_dir = FileUtils.create_job_dir()
            temp_path = job_dir / file.filename

            with open(temp_path, "wb") as f:
                f.write(await file.read())

            # 如果没有指定文件名，使用原文件名
            upload_filename = filename if filename else file.filename

            result = await comfyui_module.upload_file(
                filename=upload_filename,
                filepath=str(temp_path),
                server_url=server_url,
                auth_token=auth_token,
                username=username,
                password=password
            )

            if result.get("success"):
                return response_formatter.success(
                    data=result,
                    message="文件上传成功"
                )
            else:
                return response_formatter.error(
                    message=result.get("error", "文件上传失败"),
                    error_code="FILE_UPLOAD_FAILED"
                )
        except Exception as e:
            return response_formatter.wrap_exception(e, "文件上传失败")

    @api_router.get("/comfyui/info")
    async def get_comfyui_info(
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        获取 ComfyUI 模块信息

        Args:
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 模块信息
        """
        try:
            from modules.comfyui_module import comfyui_module

            model_info = comfyui_module.get_model_info()

            return response_formatter.success(
                data=model_info,
                message="获取 ComfyUI 模块信息成功"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "获取 ComfyUI 模块信息失败")

    @api_router.get("/comfyui/workflows")
    async def list_workflows(
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        获取 workflows 目录中的所有工作流模板列表

        Args:
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 工作流模板列表
        """
        try:
            from modules.comfyui_module import comfyui_module

            result = comfyui_module.list_workflows()

            if result.get("success"):
                return response_formatter.success(
                    data=result,
                    message="获取工作流列表成功"
                )
            else:
                return response_formatter.error(
                    message=result.get("error", "获取工作流列表失败"),
                    error_code="LIST_WORKFLOWS_FAILED"
                )
        except Exception as e:
            return response_formatter.wrap_exception(e, "获取工作流列表失败")

    @api_router.get("/comfyui/workflow/{workflow_name}")
    async def get_workflow_info(
        workflow_name: str,
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        获取指定工作流模板的详细信息

        Args:
            workflow_name: 工作流文件名
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 工作流详细信息
        """
        try:
            from modules.comfyui_module import comfyui_module

            result = comfyui_module.load_workflow_file(workflow_name)

            if result.get("success"):
                return response_formatter.success(
                    data=result,
                    message="获取工作流信息成功"
                )
            else:
                return response_formatter.error(
                    message=result.get("error", "获取工作流信息失败"),
                    error_code="GET_WORKFLOW_FAILED"
                )
        except Exception as e:
            return response_formatter.wrap_exception(e, "获取工作流信息失败")

    @api_router.post("/comfyui/execute_from_template")
    async def execute_workflow_from_template(
        workflow_name: str = Form(..., description="工作流文件名"),
        params: Optional[str] = Form(None, description="参数 JSON（可选）"),
        server_url: str = Form("http://127.0.0.1:8188", description="ComfyUI 服务器地址"),
        auth_token: Optional[str] = Form(None, description="ComfyUI 认证 Token"),
        username: Optional[str] = Form(None, description="ComfyUI 用户名"),
        password: Optional[str] = Form(None, description="ComfyUI 密码"),
        timeout: int = Form(300, description="超时时间（秒）"),
        upload_files_json: Optional[str] = Form(None, description="上传文件 JSON（可选）"),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        从工作流模板执行工作流，支持参数替换

        Args:
            workflow_name: 工作流文件名
            params: 参数 JSON（可选）
            server_url: ComfyUI 服务器地址
            auth_token: ComfyUI 认证 Token
            username: ComfyUI 用户名
            password: ComfyUI 密码
            timeout: 超时时间（秒）
            upload_files_json: 上传文件 JSON（可选）
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            import json
            from modules.comfyui_module import comfyui_module

            # 解析参数 JSON
            params_dict = {}
            if params:
                try:
                    params_dict = json.loads(params)
                except json.JSONDecodeError as e:
                    return response_formatter.error(
                        message=f"参数 JSON 格式无效: {str(e)}",
                        error_code="INVALID_PARAMS_JSON"
                    )

            # 解析上传文件 JSON
            upload_files = {}
            if upload_files_json:
                try:
                    upload_files = json.loads(upload_files_json)
                except json.JSONDecodeError as e:
                    return response_formatter.error(
                        message=f"上传文件 JSON 格式无效: {str(e)}",
                        error_code="INVALID_UPLOAD_FILES_JSON"
                    )

            result = await comfyui_module.execute_workflow_from_template(
                workflow_name=workflow_name,
                server_url=server_url,
                auth_token=auth_token,
                username=username,
                password=password,
                params=params_dict if params_dict else None,
                upload_files=upload_files if upload_files else None,
                timeout=timeout
            )

            if result.get("success"):
                return response_formatter.success(
                    data=result,
                    message="工作流执行成功"
                )
            else:
                return response_formatter.error(
                    message=result.get("error", "工作流执行失败"),
                    error_code="EXECUTE_WORKFLOW_FAILED"
                )
        except Exception as e:
            return response_formatter.wrap_exception(e, "执行工作流失败")

    @api_router.post("/comfyui/workflow/upload")
    async def upload_workflow_template(
        workflow_name: str = Form(..., description="工作流文件名"),
        workflow_json: str = Form(..., description="工作流 JSON"),
        overwrite: bool = Form(False, description="是否覆盖已存在"),
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        上传工作流模板到 workflows 目录

        Args:
            workflow_name: 工作流文件名
            workflow_json: 工作流 JSON
            overwrite: 是否覆盖已存在
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 上传结果
        """
        try:
            from modules.comfyui_module import comfyui_module

            result = comfyui_module.upload_workflow_template(
                workflow_name=workflow_name,
                workflow_json=workflow_json,
                overwrite=overwrite
            )

            if result.get("success"):
                return response_formatter.success(
                    data=result,
                    message="工作流模板上传成功"
                )
            else:
                return response_formatter.error(
                    message=result.get("error", "上传工作流模板失败"),
                    error_code="UPLOAD_WORKFLOW_FAILED"
                )
        except Exception as e:
            return response_formatter.wrap_exception(e, "上传工作流模板失败")

    @api_router.get("/comfyui/workflow/{workflow_name}/params")
    async def get_workflow_params(
        workflow_name: str,
        payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        获取工作流模板的参数占位符和示例

        Args:
            workflow_name: 工作流文件名
            payload: 认证载荷

        Returns:
            Dict[str, Any]: 参数信息
        """
        try:
            from modules.comfyui_module import comfyui_module

            # 加载工作流
            load_result = comfyui_module.load_workflow_file(workflow_name)
            if not load_result.get("success"):
                return response_formatter.error(
                    message=load_result.get("error", "加载工作流失败"),
                    error_code="LOAD_WORKFLOW_FAILED"
                )

            workflow = load_result.get("workflow", {})

            # 提取参数
            params_result = comfyui_module.extract_parameters(workflow)

            return response_formatter.success(
                data=params_result,
                message="获取工作流参数成功"
            )
        except Exception as e:
            return response_formatter.wrap_exception(e, "获取工作流参数失败")

    # 注册路由器到应用
    app.include_router(api_router)