"""
高级字幕生成模块 (Subtitle Module)

提供视频字幕生成、翻译、烧录、花字、插图、水印等完整功能。
"""

import os
import asyncio
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List

from config import config
from utils.logger import Logger
from utils.file_utils import FileUtils
from utils.media_processor import MediaProcessor
from utils.subtitle_generator import SubtitleGenerator
from utils.video_effects import VideoEffectsProcessor


class SubtitleModule:
    """高级字幕生成模块"""

    def __init__(self):
        self.config = config

    async def generate_subtitles_advanced(
        self,
        input_type: str = "upload",
        video_file: Optional[str] = None,
        audio_file: Optional[str] = None,
        subtitle_file: Optional[str] = None,
        video_path: Optional[str] = None,
        audio_path: Optional[str] = None,
        subtitle_path: Optional[str] = None,
        model_name: str = "small",
        device: str = "cpu",
        generate_subtitle: bool = True,
        bilingual: bool = True,
        word_timestamps: bool = False,
        burn_subtitles: str = "none",
        beam_size: int = 5,
        subtitle_bottom_margin: int = 20,
        out_basename: Optional[str] = None,
        # 花字配置
        flower_config: Optional[Dict[str, Any]] = None,
        # 插图配置
        image_config: Optional[Dict[str, Any]] = None,
        # 水印配置
        watermark_config: Optional[Dict[str, Any]] = None,
        # 时长基准配置
        duration_reference: str = "video",  # "video" 或 "audio"，决定以哪个为准
        # 音频语速调整配置
        adjust_audio_speed: bool = False,  # 是否自动调整音频语速
        audio_speed_factor: float = 1.0,  # 音频语速调整倍数
        # 音频音量控制配置
        audio_volume: float = 1.0,  # 音频音量倍数（默认1.0，表示原音量）
        # 原音频保留配置
        keep_original_audio: bool = True,  # 是否保留原视频音频（默认True，保留并混合；False则替换原音频）
        # LLM 字幕纠错配置
        enable_llm_correction: bool = False,  # 是否启用 LLM 字幕纠错
        reference_text: Optional[str] = None,  # 参考文本，用于字幕纠错
        # Whisper 时间戳分段优化配置
        vad_filter: bool = True,  # 启用 VAD 语音活动检测
        condition_on_previous_text: bool = False,  # 不依赖前文，产生更自然的分段
        temperature: float = 0.0,  # 温度参数，0 表示更保守
        # 字幕显示参数（后处理）
        max_chars_per_line: int = 20,  # 每行最大字符数
        max_lines_per_segment: int = 2,  # 每段最大行数
        # 任务目录配置（可选）
        job_dir: Optional[Path] = None  # 可选的任务目录，如果提供则使用该目录
    ) -> Dict[str, Any]:
        """
        高级字幕生成功能（完整版）

        Args:
            input_type: 输入类型 (upload/path/separate_audio)
            video_file: 上传的视频文件路径
            audio_file: 上传的音频文件路径
            subtitle_file: 上传的字幕文件路径
            video_path: 视频文件路径（URL或本地路径）
            audio_path: 音频文件路径（URL或本地路径）
            subtitle_path: 字幕文件路径（URL或本地路径）
            model_name: Whisper模型名称
            device: 设备类型
            generate_subtitle: 是否生成字幕
            bilingual: 是否生成双语字幕
            word_timestamps: 是否包含词级时间戳
            burn_subtitles: 字幕烧录类型 (none/hard/soft)
            beam_size: beam search 大小
            subtitle_bottom_margin: 字幕下沿距离（像素）
            out_basename: 输出文件名前缀
            flower_config: 花字配置
            image_config: 插图配置
            watermark_config: 水印配置
            duration_reference: 时长基准（video/audio）
            adjust_audio_speed: 是否自动调整音频语速
            audio_speed_factor: 音频语速调整倍数
            audio_volume: 音频音量倍数（默认1.0，表示原音量；0.5表示降低一半音量；2.0表示提高一倍音量）
            keep_original_audio: 是否保留原视频音频（默认True，保留并混合；False则替换原音频）
            enable_llm_correction: 是否启用 LLM 字幕纠错（使用智谱 AI）
            reference_text: 参考文本，用于字幕纠错

        Returns:
            Dict[str, Any]: 字幕生成结果
        """
        try:
            from modules.whisper_service import whisper_service

            # 创建任务目录（如果未提供）
            if job_dir is None:
                job_dir = FileUtils.create_job_dir()
            else:
                # 确保 job_dir 存在
                job_dir = Path(job_dir)
                job_dir.mkdir(parents=True, exist_ok=True)
            
            out_basename = out_basename or f"output_{FileUtils.generate_job_id()}"

            # 处理输入文件
            local_input = None  # 视频文件路径
            audio_input = None  # 音频文件路径
            local_subtitle = None  # 字幕文件路径

            if input_type == "upload":
                # 处理上传文件 - Gradio返回的格式可能是：
                # - 视频: 元组 (path, name) 或 字符串
                # - 音频: 元组 (path, sample_rate) 或 字符串
                Logger.info(f"Upload模式 - video_file: {video_file}, audio_file: {audio_file}")
                Logger.info(f"video_file类型: {type(video_file)}, audio_file类型: {type(audio_file)}")

                # 处理视频文件
                if video_file:
                    if isinstance(video_file, tuple):
                        video_file = video_file[0]
                    if isinstance(video_file, str):
                        video_file_path = Path(video_file)
                        local_input = job_dir / video_file_path.name
                        shutil.copy2(video_file, local_input)
                        Logger.info(f"复制视频文件: {video_file} -> {local_input}")

                # 处理音频文件（优先用于语音识别）
                if audio_file:
                    if isinstance(audio_file, tuple):
                        # Gradio 音频返回格式: (采样率, 音频数组) 或 (文件路径, 文件名)
                        if len(audio_file) == 2:
                            # 检查第一个元素是否是采样率（整数）
                            if isinstance(audio_file[0], int) and audio_file[0] > 0:
                                # 格式: (采样率, 音频数组) - 这是 numpy 数组，需要先保存为文件
                                import numpy as np
                                import soundfile as sf
                                sample_rate, audio_array = audio_file
                                audio_path = job_dir / "uploaded_audio.wav"
                                # 将 numpy 数组保存为 WAV 文件
                                sf.write(audio_path, audio_array, sample_rate)
                                audio_input = audio_path
                                Logger.info(f"从 numpy 数组保存音频文件: {audio_path}")
                            elif isinstance(audio_file[0], str):
                                # 格式: (文件路径, 文件名)
                                audio_file = audio_file[0]
                                audio_file_path = Path(audio_file)
                                audio_input = job_dir / audio_file_path.name
                                shutil.copy2(audio_file, audio_input)
                                Logger.info(f"复制音频文件: {audio_file} -> {audio_input}")
                    elif isinstance(audio_file, str):
                        audio_file_path = Path(audio_file)
                        audio_input = job_dir / audio_file_path.name
                        shutil.copy2(audio_file, audio_input)
                        Logger.info(f"复制音频文件: {audio_file} -> {audio_input}")

                # 处理字幕文件
                if subtitle_file:
                    if isinstance(subtitle_file, str):
                        subtitle_file_path = Path(subtitle_file)
                        local_subtitle = job_dir / subtitle_file_path.name
                        shutil.copy2(subtitle_file, local_subtitle)
                        Logger.info(f"复制字幕文件: {subtitle_file} -> {local_subtitle}")

                # 验证至少有一个输入文件
                if not local_input and not audio_input:
                    Logger.warning("Upload模式: video_file和audio_file都为空！")
                    raise ValueError("请上传视频或音频文件")

            elif input_type == "path":
                # 处理路径输入
                Logger.info(f"Path模式 - video_path: {video_path}, audio_path: {audio_path}")

                # 处理视频文件
                if video_path:
                    local_input = FileUtils.process_path_input(video_path, job_dir)
                    Logger.info(f"处理视频路径: {video_path} -> {local_input}")

                # 处理音频文件（优先用于语音识别）
                if audio_path:
                    audio_input = FileUtils.process_path_input(audio_path, job_dir)
                    Logger.info(f"处理音频路径: {audio_path} -> {audio_input}")

                # 处理字幕文件
                if subtitle_path:
                    local_subtitle = FileUtils.process_path_input(subtitle_path, job_dir)
                    Logger.info(f"处理字幕路径: {subtitle_path} -> {local_subtitle}")

                # 验证至少有一个输入文件
                if not local_input and not audio_input:
                    Logger.warning("Path模式: video_path和audio_path都为空！")
                    raise ValueError("请提供视频或音频文件路径")

            

            # 处理视频输出
            video_output = None
            base_video = None

            # 确定基础视频文件
            if local_input and FileUtils.is_video_file(str(local_input)):
                base_video = local_input

            # 处理音频语速调整（在转录之前完成）
            processed_audio = audio_input
            adjusted_audio_for_transcription = None
            
            if audio_input and local_input:
                # 获取音频和视频时长
                audio_duration = MediaProcessor.get_media_duration(audio_input)
                video_duration = MediaProcessor.get_media_duration(local_input)
                
                Logger.info(f"音频时长: {audio_duration:.2f}秒, 视频时长: {video_duration:.2f}秒")
                Logger.info(f"时长基准: {duration_reference}")
                
                # 处理音频语速调整
                if duration_reference == "video" and adjust_audio_speed:
                    # 以视频时长为准，且需要调整音频语速
                    if audio_duration > 0 and video_duration > 0:
                        # 计算需要的语速调整倍数
                        if audio_speed_factor != 1.0:
                            # 使用手动指定的倍数
                            speed_factor = audio_speed_factor
                            Logger.info(f"使用手动指定的语速调整倍数: {speed_factor}")
                        else:
                            # 自动计算倍数
                            speed_factor = audio_duration / video_duration
                            Logger.info(f"自动计算语速调整倍数: {speed_factor}")
                        
                        # 限制倍数在合理范围内
                        speed_factor = max(0.5, min(2.0, speed_factor))
                        
                        # 调整音频语速
                        adjusted_audio_path = job_dir / f"{out_basename}_adjusted_audio.wav"
                        MediaProcessor.adjust_audio_speed(audio_input, adjusted_audio_path, speed_factor)
                        processed_audio = adjusted_audio_path
                        adjusted_audio_for_transcription = adjusted_audio_path
                        
                        # 更新音频时长
                        adjusted_duration = MediaProcessor.get_media_duration(processed_audio)
                        Logger.info(f"调整后音频时长: {adjusted_duration:.2f}秒")

            # 准备音频文件用于转录
            audio_for_transcription = None
            if generate_subtitle:
                # 优先级：字幕文件 > 音频文件 > 视频文件
                if local_subtitle:
                    # 有字幕文件，直接使用，不进行语音识别
                    Logger.info("使用上传的字幕文件，跳过语音识别")
                    audio_for_transcription = None  # 不需要音频转录
                elif adjusted_audio_for_transcription:
                    audio_for_transcription = adjusted_audio_for_transcription
                    Logger.info("使用调整后的音频进行语音识别，确保字幕时间轴与视频同步")
                elif audio_input:
                    audio_for_transcription = audio_input
                elif local_input and FileUtils.is_video_file(str(local_input)):
                    audio_for_transcription = job_dir / "audio.wav"
                    MediaProcessor.extract_audio(local_input, audio_for_transcription)
                elif local_input:
                    audio_for_transcription = local_input

            # 转录音频
            segments = None
            if generate_subtitle and audio_for_transcription and not local_subtitle:
                segments = await whisper_service.transcribe_advanced(
                    audio_for_transcription,
                    model_name=model_name,
                    device=device,
                    beam_size=beam_size,
                    task="transcribe",
                    word_timestamps=word_timestamps,
                    # 基础参数
                    vad_filter=vad_filter,
                    condition_on_previous_text=condition_on_previous_text,
                    temperature=temperature
                )

            # 生成字幕文件
            srt_path = None
            bilingual_srt_path = None

            if local_subtitle:
                # 使用上传的字幕文件
                srt_path = local_subtitle
                Logger.info(f"使用上传的字幕文件: {srt_path}")
                
                # 如果需要双语字幕，尝试翻译
                if bilingual:
                    # TODO: 实现字幕翻译功能
                    Logger.info("双语字幕功能暂未实现")
            elif segments and generate_subtitle:
                # 从语音识别生成字幕
                # LLM 字幕纠错
                if enable_llm_correction and reference_text and reference_text.strip():
                    try:
                        from utils.llm_corrector import llm_corrector, SubtitleSegment

                        Logger.info("开始 LLM 字幕纠错...")

                        # 将 segments 转换为 SubtitleSegment 对象
                        subtitle_segments = [
                            SubtitleSegment(start=seg.start, end=seg.end, text=seg.text)
                            for seg in segments
                        ]

                        # 调用 LLM 纠错
                        corrected_segments = llm_corrector.correct_subtitle_segments(
                            subtitle_segments,
                            reference_text
                        )

                        # 更新 segments 的文本
                        for i, corrected_seg in enumerate(corrected_segments):
                            if i < len(segments):
                                segments[i].text = corrected_seg.text

                        Logger.info("LLM 字幕纠错完成")

                    except Exception as e:
                        Logger.error(f"LLM 字幕纠错失败: {e}")
                        import traceback
                        Logger.error(traceback.format_exc())

                # 生成字幕文件
                srt_path = job_dir / f"{out_basename}.srt"
                SubtitleGenerator.write_srt(
                    segments, srt_path, bilingual=False,
                    max_chars_per_line=max_chars_per_line,
                    max_lines_per_segment=max_lines_per_segment
                )

                # 生成双语字幕
                if bilingual:
                    translated_segments = await whisper_service.transcribe_advanced(
                        audio_for_transcription,
                        model_name=model_name,
                        device=device,
                        beam_size=beam_size,
                        task="translate",
                        word_timestamps=word_timestamps,
                        # 基础参数
                        vad_filter=vad_filter,
                        condition_on_previous_text=condition_on_previous_text,
                        temperature=temperature
                    )
                    bilingual_srt_path = job_dir / f"{out_basename}_bilingual.srt"
                    SubtitleGenerator.write_srt(
                        segments, bilingual_srt_path,
                        bilingual=True,
                        translated_segments=translated_segments,
                        max_chars_per_line=max_chars_per_line,
                        max_lines_per_segment=max_lines_per_segment
                    )

            # 合并音视频（如果需要）
            if audio_input and local_input:
                merged_video_path = job_dir / f"{out_basename}_merged{local_input.suffix}"
                try:
                    # 重新获取音频和视频时长（可能在音频调整后发生变化）
                    if processed_audio:
                        processed_audio_duration = MediaProcessor.get_media_duration(processed_audio)
                    else:
                        processed_audio_duration = MediaProcessor.get_media_duration(audio_input)
                    
                    video_duration = MediaProcessor.get_media_duration(local_input)
                    
                    # 根据时长基准参数决定处理方式
                    if duration_reference == "audio" and processed_audio_duration > video_duration:
                        # 以音频时长为准，视频时长不足时以最后一帧补充
                        Logger.info("以音频时长为准，视频时长不足，将补充最后一帧")
                        MediaProcessor.merge_audio_video_with_duration(
                            local_input, processed_audio, merged_video_path, 
                            target_duration=processed_audio_duration, extend_video=True, audio_volume=audio_volume, keep_original_audio=keep_original_audio
                        )
                    elif duration_reference == "video":
                        # 以视频时长为准，不使用 -shortest 参数
                        Logger.info("以视频时长为准，保持视频完整长度")
                        MediaProcessor.merge_audio_video(local_input, processed_audio, merged_video_path, use_shortest=False, audio_volume=audio_volume, keep_original_audio=keep_original_audio)
                    else:
                        # 默认合并方式（兼容旧版本）
                        MediaProcessor.merge_audio_video(local_input, processed_audio, merged_video_path, audio_volume=audio_volume, keep_original_audio=keep_original_audio)
                    
                    base_video = merged_video_path
                    Logger.info(f"音视频合并成功: {merged_video_path}")
                except Exception as e:
                    Logger.error(f"音视频合并失败: {e}")
                    # 合并失败，使用原始视频
                    if local_input and FileUtils.is_video_file(str(local_input)):
                        base_video = local_input
                    else:
                        # 如果没有视频文件但有音频文件，创建一个临时视频
                        Logger.warning("没有视频文件，跳过视频处理")
                        base_video = None

            # 烧录字幕
            if burn_subtitles != "none" and srt_path and base_video:
                srt_to_use = bilingual_srt_path if bilingual else srt_path
                hardsub_video = job_dir / f"{out_basename}_hardsub{base_video.suffix}"

                try:
                    Logger.info(f"开始烧录硬字幕: {base_video} + {srt_to_use} -> {hardsub_video}")
                    MediaProcessor.burn_hardsub(base_video, srt_to_use, hardsub_video, subtitle_bottom_margin)
                    video_output = hardsub_video
                    Logger.info(f"硬字幕视频生成成功: {video_output}")
                except Exception as e:
                    Logger.error(f"硬字幕视频生成失败: {e}")
                    import traceback
                    Logger.error(traceback.format_exc())
                    # 烧录失败，使用原始视频
                    video_output = base_video

            # 构建结果
            result = {
                "success": True,
                "out_basename": out_basename,
                "segments_count": len(segments) if segments else 0
            }

            # 只添加实际存在的文件路径
            if srt_path and srt_path.exists():
                result["subtitle_path"] = str(srt_path)
            if bilingual_srt_path and bilingual_srt_path.exists():
                result["bilingual_subtitle_path"] = str(bilingual_srt_path)
            if video_output and video_output.exists():
                result["video_with_subtitle_path"] = str(video_output)
            elif base_video and base_video.exists():
                # 如果video_output不存在但base_video存在，返回base_video
                result["video_with_subtitle_path"] = str(base_video)

            if segments:
                result["transcript_text"] = "\n".join([seg.text for seg in segments])
                result["segments"] = [
                    {"start": seg.start, "end": seg.end, "text": seg.text}
                    for seg in segments
                ]

            Logger.info(f"高级字幕生成完成: {out_basename}")
            return result

        except Exception as e:
            Logger.error(f"高级字幕生成失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }

    async def generate_subtitles(
        self,
        video_path: Path,
        model_name: str = None,
        language: str = "zh",
        word_timestamps: bool = False,
        output_format: str = "srt",
        bilingual: bool = False,
        burn_subtitles: str = "none",
        out_basename: str = None
    ) -> Dict[str, Any]:
        """
        生成视频字幕（简化版）

        Args:
            video_path: 视频文件路径
            model_name: Whisper模型名称
            language: 目标语言
            word_timestamps: 是否包含词级时间戳
            output_format: 输出格式
            bilingual: 是否生成双语字幕
            burn_subtitles: 字幕烧录类型
            out_basename: 输出文件名前缀

        Returns:
            Dict[str, Any]: 字幕生成结果
        """
        return await self.generate_subtitles_advanced(
            input_type="upload",
            video_file=str(video_path),
            model_name=model_name,
            generate_subtitle=True,
            bilingual=bilingual,
            word_timestamps=word_timestamps,
            burn_subtitles=burn_subtitles,
            out_basename=out_basename
        )

    async def translate_subtitles(
        self,
        subtitle_path: Path,
        target_language: str = "en",
        output_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        翻译字幕

        Args:
            subtitle_path: 字幕文件路径
            target_language: 目标语言
            output_path: 输出文件路径

        Returns:
            Dict[str, Any]: 翻译结果
        """
        try:
            # TODO: 实现字幕翻译功能
            Logger.info(f"Subtitle translation: {subtitle_path} -> {target_language}")

            return {
                "success": True,
                "output_path": str(output_path) if output_path else None,
                "target_language": target_language
            }

        except Exception as e:
            Logger.error(f"Subtitle translation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def burn_subtitles(
        self,
        video_path: Path,
        subtitle_path: Path,
        output_path: Optional[Path] = None,
        subtitle_type: str = "hard",
        # 任务目录配置（可选）
        job_dir: Optional[Path] = None  # 可选的任务目录，如果提供则使用该目录
    ) -> Dict[str, Any]:
        """
        烧录字幕到视频

        Args:
            video_path: 视频文件路径
            subtitle_path: 字幕文件路径
            output_path: 输出视频路径
            subtitle_type: 字幕类型 (hard, soft)

        Returns:
            Dict[str, Any]: 烧录结果
        """
        try:
            # 创建任务目录（如果未提供）
            if job_dir is None:
                job_dir = FileUtils.create_job_dir()
            else:
                # 确保 job_dir 存在
                job_dir = Path(job_dir)
                job_dir.mkdir(parents=True, exist_ok=True)

            if output_path is None:
                output_path = job_dir / f"video_with_subs_{FileUtils.generate_job_id()}.mp4"

            if subtitle_type == "hard":
                MediaProcessor.burn_hardsub(video_path, subtitle_path, output_path)
            else:
                MediaProcessor.mux_softsub(video_path, subtitle_path, output_path)

            Logger.info(f"Subtitles burned: {output_path}")

            return {
                "success": True,
                "output_path": str(output_path),
                "subtitle_type": subtitle_type
            }

        except Exception as e:
            Logger.error(f"Subtitle burning failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def add_watermark(
        self,
        video_path: Path,
        watermark_text: Optional[str] = None,
        watermark_image: Optional[str] = None,
        position: str = "bottom_right",
        opacity: float = 0.5,
        output_path: Optional[Path] = None,
        # 任务目录配置（可选）
        job_dir: Optional[Path] = None  # 可选的任务目录，如果提供则使用该目录
    ) -> Dict[str, Any]:
        """
        为视频添加水印

        Args:
            video_path: 视频文件路径
            watermark_text: 水印文字
            watermark_image: 水印图片路径
            position: 水印位置
            opacity: 透明度
            output_path: 输出视频路径

        Returns:
            Dict[str, Any]: 添加水印结果
        """
        try:
            # 创建任务目录（如果未提供）
            if job_dir is None:
                job_dir = FileUtils.create_job_dir()
            else:
                # 确保 job_dir 存在
                job_dir = Path(job_dir)
                job_dir.mkdir(parents=True, exist_ok=True)

            if output_path is None:
                output_path = job_dir / f"video_with_watermark_{FileUtils.generate_job_id()}.mp4"

            # 构建水印配置
            watermark_config = None
            if watermark_text:
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

            # 应用水印效果（使用同一个 job_dir）
            temp_video = job_dir / f"temp_watermark_{FileUtils.generate_job_id()}.mp4"

            VideoEffectsProcessor.apply_video_effects(
                video_path, temp_video,
                flower_config=None,
                image_config=None,
                watermark_config=watermark_config
            )

            # 合并音频
            from utils.system_utils import SystemUtils
            import shutil
            ffmpeg_path = SystemUtils.get_ffmpeg_path()
            import os
            original_cwd = os.getcwd()

            output_dir = output_path.parent
            os.chdir(output_dir)

            video_rel = os.path.relpath(video_path, output_dir).replace('\\', '/')
            temp_rel = temp_video.name
            output_rel = output_path.name

            cmd = [
                ffmpeg_path, "-y",
                "-i", video_rel,
                "-i", temp_rel,
                "-map", "0:a:0",
                "-map", "1:v:0",
                "-c:a", "copy",
                "-c:v", "copy",
                output_rel
            ]

            SystemUtils.run_cmd(cmd)
            os.chdir(original_cwd)

            Logger.info(f"Watermark added: {output_path}")

            return {
                "success": True,
                "output_path": str(output_path),
                "watermark_text": watermark_text
            }

        except Exception as e:
            Logger.error(f"Watermark addition failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# 创建全局服务实例
subtitle_module = SubtitleModule()
