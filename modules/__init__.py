"""
功能模块

包含 Whisper 语音识别、语音合成、字幕生成、视频转场、图像处理、文件持久化、ComfyUI 集成、通用HTTP集成、全自动视频生成等功能模块。
"""

from .whisper_service import WhisperService, whisper_service
from .tts_onnx_module import TTSOnnxModule, tts_onnx_module
from .subtitle_module import SubtitleModule, subtitle_module
from .transition_module import TransitionModule, transition_module
from .video_editor_module import VideoEditorModule, video_editor_module
from .video_merge_module import VideoMergeModule, video_merge_module
from .image_processing_module import ImageProcessingModule, image_processing_module
from .template_manager import TemplateManager, template_manager
from .parameter_resolver import ParameterResolver, parameter_resolver
from .task_orchestrator import TaskOrchestrator, task_orchestrator
from .task_handlers import TaskHandlers, task_handlers
from .file_persistence import (
    FilePersistenceManager,
    BasePlatformUploader,
    HuggingFaceUploader,
    ModelScopeUploader,
    UploadResult,
    PlatformType,
    get_persistence_manager,
    init_persistence_manager
)
from .comfyui_module import ComfyUIClient, ComfyUIModule, ComfyUIResult, comfyui_module
from .http_integration_module import HTTPIntegrationModule, http_integration_module
from .auto_video_task_module import AutoVideoTaskModule, auto_video_task_module

__all__ = [
    'WhisperService',
    'TTSOnnxModule',
    'SubtitleModule',
    'TransitionModule',
    'VideoEditorModule',
    'VideoMergeModule',
    'ImageProcessingModule',
    'TemplateManager',
    'ParameterResolver',
    'TaskOrchestrator',
    'TaskHandlers',
    'FilePersistenceManager',
    'BasePlatformUploader',
    'HuggingFaceUploader',
    'ModelScopeUploader',
    'UploadResult',
    'PlatformType',
    'ComfyUIClient',
    'ComfyUIModule',
    'ComfyUIResult',
    'HTTPIntegrationModule',
    'AutoVideoTaskModule',
    'whisper_service',
    'tts_onnx_module',
    'subtitle_module',
    'transition_module',
    'video_editor_module',
    'video_merge_module',
    'image_processing_module',
    'template_manager',
    'parameter_resolver',
    'task_orchestrator',
    'task_handlers',
    'get_persistence_manager',
    'init_persistence_manager',
    'comfyui_module',
    'http_integration_module',
    'auto_video_task_module'
]