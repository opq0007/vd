"""
功能模块

包含 Whisper 语音识别、语音合成、字幕生成、视频转场等功能模块。
"""

from .whisper_service import WhisperService
from .tts_module import TTSModule
from .subtitle_module import SubtitleModule
from .transition_module import TransitionModule

__all__ = [
    'WhisperService',
    'TTSModule',
    'SubtitleModule',
    'TransitionModule'
]