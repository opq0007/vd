"""
Gradio UI 模块

包含所有 Gradio 界面组件。
"""

from .base_ui import get_custom_css, create_header
from .tts_ui import create_tts_interface
from .subtitle_ui import create_subtitle_interface
from .transition_ui import create_transition_interface
from .video_editor_ui import create_video_editor_interface
from .video_merge_ui import create_video_merge_interface
from .image_processing_ui import create_image_processing_interface
from .batch_processing_ui import create_batch_processing_interface
from .template_manager_ui import get_template_manager_ui
from .file_persistence_ui import create_file_persistence_interface

__all__ = [
    'get_custom_css',
    'create_header',
    'create_tts_interface',
    'create_subtitle_interface',
    'create_transition_interface',
    'create_video_editor_interface',
    'create_video_merge_interface',
    'create_image_processing_interface',
    'create_batch_processing_interface',
    'get_template_manager_ui',
    'create_file_persistence_interface'
]