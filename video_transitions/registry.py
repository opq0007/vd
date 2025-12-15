"""
转场效果注册表

管理所有可用的转场效果，提供注册和查询功能。
"""

from typing import Dict, Type, List
from .base import BaseTransition


class TransitionRegistry:
    """转场效果注册表"""
    
    _transitions: Dict[str, Type[BaseTransition]] = {}
    _categories: Dict[str, List[str]] = {}
    
    @classmethod
    def register(cls, name: str, transition_class: Type[BaseTransition], category: str = "General") -> None:
        """注册转场效果"""
        cls._transitions[name] = transition_class
        
        if category not in cls._categories:
            cls._categories[category] = []
        cls._categories[category].append(name)
    
    @classmethod
    def get_transition(cls, name: str) -> Type[BaseTransition]:
        """获取转场效果类"""
        if name not in cls._transitions:
            raise ValueError(f"未找到转场效果: {name}")
        return cls._transitions[name]
    
    @classmethod
    def list_transitions(cls) -> List[str]:
        """列出所有转场效果"""
        return list(cls._transitions.keys())
    
    @classmethod
    def list_categories(cls) -> List[str]:
        """列出所有分类"""
        return list(cls._categories.keys())
    
    @classmethod
    def get_transitions_by_category(cls, category: str) -> List[str]:
        """获取指定分类的转场效果"""
        return cls._categories.get(category, [])
    
    @classmethod
    def get_transition_info(cls) -> Dict[str, Dict[str, any]]:
        """获取所有转场效果的详细信息"""
        info = {}
        for name, transition_class in cls._transitions.items():
            # 创建实例获取参数
            instance = transition_class()
            info[name] = {
                'name': name,
                'class': transition_class.__name__,
                'params': instance.get_params(),
                'category': instance.category
            }
        return info


def register_transition(name: str, category: str = "General"):
    """装饰器：注册转场效果"""
    def decorator(cls: Type[BaseTransition]):
        TransitionRegistry.register(name, cls, category)
        return cls
    return decorator