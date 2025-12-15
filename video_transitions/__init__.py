"""
视频转场特效模块

提供多种视频转场效果，支持纯Python、Chromium和WebGL三种实现方式。
"""

from .base import BaseTransition
from .registry import TransitionRegistry
from .factory import TransitionFactory

# 导入所有转场效果
from .crossfade import CrossfadeTransition

from .blink import BlinkTransition

from .blinds import BlindsTransition
from .checkerboard import CheckerboardTransition
from .explosion import ExplosionTransition
from .shake import ShakeTransition
from .warp import WarpTransition
from .page_turn import PageTurnTransition
from .flip3d import Flip3DTransition
from .processor import TransitionProcessor, transition_processor

__all__ = [
    'BaseTransition',
    'TransitionRegistry', 
    'TransitionFactory',
    'TransitionProcessor',
    'transition_processor',
    'CrossfadeTransition',
    'BlinkTransition',
    
    'BlindsTransition',
    'CheckerboardTransition',
    'ExplosionTransition',
    'ShakeTransition',
    'WarpTransition',
    'PageTurnTransition',
    'Flip3DTransition'
]