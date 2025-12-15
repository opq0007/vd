"""
转场效果工厂

提供统一的转场效果创建接口。
"""

from typing import Dict, Any
from .base import BaseTransition
from .registry import TransitionRegistry


class TransitionFactory:
    """转场效果工厂类"""
    
    @staticmethod
    def create_transition(transition_name: str, **kwargs) -> BaseTransition:
        """
        创建转场效果实例
        
        Args:
            transition_name: 转场效果名称
            **kwargs: 初始化参数
            
        Returns:
            转场效果实例
        """
        transition_class = TransitionRegistry.get_transition(transition_name)
        return transition_class(**kwargs)
    
    @staticmethod
    def get_available_transitions() -> Dict[str, Dict[str, Any]]:
        """获取所有可用的转场效果信息"""
        return TransitionRegistry.get_transition_info()
    
    @staticmethod
    def get_transition_params(transition_name: str) -> Dict[str, Any]:
        """获取指定转场效果的参数配置"""
        transition_class = TransitionRegistry.get_transition(transition_name)
        instance = transition_class()
        return instance.get_params()
    
    @staticmethod
    def get_transitions_by_category(category: str) -> list:
        """获取指定分类的转场效果"""
        return TransitionRegistry.get_transitions_by_category(category)