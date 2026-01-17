"""
功能模块

包含 Whisper 语音识别、语音合成、字幕生成、视频转场、图像处理等功能模块。
"""

from .whisper_service import WhisperService, whisper_service
from .tts_onnx_module import TTSOnnxModule, tts_onnx_module
from .subtitle_module import SubtitleModule, subtitle_module
from .transition_module import TransitionModule, transition_module
from .video_editor_module import VideoEditorModule, video_editor_module
from .video_merge_module import VideoMergeModule, video_merge_module
from .image_processing_module import ImageProcessingModule, image_processing_module

__all__ = [
    'WhisperService',
    'TTSOnnxModule',
    'SubtitleModule',
    'TransitionModule',
    'VideoEditorModule',
    'VideoMergeModule',
    'ImageProcessingModule',
    'whisper_service',
    'tts_onnx_module',
    'subtitle_module',
    'transition_module',
    'video_editor_module',
    'video_merge_module',
    'image_processing_module'
]