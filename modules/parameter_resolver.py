"""
参数替换引擎

负责将模板中的参数占位符替换为实际值。
"""

import re
from typing import Any, Dict, List
from utils.logger import Logger


class ParameterResolver:
    """参数解析器"""
    
    # 参数占位符的正则表达式：${parameter_name}
    PARAM_PATTERN = re.compile(r'\$\{([^}]+)\}')
    
    @classmethod
    def resolve(cls, template: Any, parameters: Dict[str, Any], 
                task_outputs: Dict[str, Any] = None) -> Any:
        """
        解析模板中的参数
        
        Args:
            template: 模板数据（可以是字符串、字典、列表等）
            parameters: 参数值字典
            task_outputs: 任务输出字典（用于引用其他任务的输出）
            
        Returns:
            解析后的数据
        """
        if task_outputs is None:
            task_outputs = {}
        
        if isinstance(template, str):
            return cls._resolve_string(template, parameters, task_outputs)
        elif isinstance(template, dict):
            return cls._resolve_dict(template, parameters, task_outputs)
        elif isinstance(template, list):
            return cls._resolve_list(template, parameters, task_outputs)
        else:
            return template
    
    @classmethod
    def _resolve_string(cls, text: str, parameters: Dict[str, Any],
                       task_outputs: Dict[str, Any]) -> str:
        """
        解析字符串中的参数
        
        Args:
            text: 字符串
            parameters: 参数值字典
            task_outputs: 任务输出字典
            
        Returns:
            解析后的字符串
        """
        def replace_match(match):
            param_path = match.group(1)
            return cls._get_value(param_path, parameters, task_outputs)
        
        return cls.PARAM_PATTERN.sub(replace_match, text)
    
    @classmethod
    def _resolve_dict(cls, data: Dict[str, Any], parameters: Dict[str, Any],
                     task_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析字典中的参数
        
        Args:
            data: 字典数据
            parameters: 参数值字典
            task_outputs: 任务输出字典
            
        Returns:
            解析后的字典
        """
        result = {}
        for key, value in data.items():
            # 解析键
            resolved_key = cls._resolve_string(key, parameters, task_outputs) if isinstance(key, str) else key
            # 解析值
            resolved_value = cls.resolve(value, parameters, task_outputs)
            result[resolved_key] = resolved_value
        return result
    
    @classmethod
    def _resolve_list(cls, data: List[Any], parameters: Dict[str, Any],
                     task_outputs: Dict[str, Any]) -> List[Any]:
        """
        解析列表中的参数
        
        Args:
            data: 列表数据
            parameters: 参数值字典
            task_outputs: 任务输出字典
            
        Returns:
            解析后的列表
        """
        return [cls.resolve(item, parameters, task_outputs) for item in data]
    
    @classmethod
    def _get_value(cls, path: str, parameters: Dict[str, Any],
                  task_outputs: Dict[str, Any]) -> str:
        """
        根据路径获取值
        
        Args:
            path: 参数路径（如：username 或 task.output 或 task.output[0]）
            parameters: 参数值字典
            task_outputs: 任务输出字典
            
        Returns:
            值字符串
        """
        # 分割路径
        parts = path.split('.')
        
        # 检查是否是任务输出引用
        if len(parts) >= 2 and parts[0] in task_outputs:
            task_id = parts[0]
            output_key = '.'.join(parts[1:])
            
            task_output = task_outputs[task_id]
            
            # 检查任务是否失败
            if isinstance(task_output, dict) and "error" in task_output:
                Logger.error(f"任务 {task_id} 失败，无法获取输出: {task_output['error']}")
                return ""  # 返回空字符串，避免后续任务崩溃
            
            if isinstance(task_output, dict):
                value = task_output.get(output_key, '')
                if not value and output_key == "output":
                    Logger.warning(f"任务 {task_id} 的 output 字段为空，task_output={task_output}")
            else:
                value = str(task_output)
            
            # 处理数组索引（如 output[0]）
            if '[' in output_key and output_key.endswith(']'):
                try:
                    # 提取数组索引
                    key_without_index = output_key.split('[')[0]
                    index_str = output_key.split('[')[1].rstrip(']')
                    index = int(index_str)
                    
                    # 获取数组值
                    if isinstance(task_output, dict):
                        array_value = task_output.get(key_without_index, [])
                    else:
                        array_value = task_output
                    
                    if isinstance(array_value, list) and 0 <= index < len(array_value):
                        value = str(array_value[index])
                        Logger.info(f"获取数组索引值: {task_id}.{output_key} = {value}")
                    else:
                        Logger.warning(f"数组索引超出范围或不是数组: {task_id}.{output_key}")
                        value = ""
                except (ValueError, IndexError) as e:
                    Logger.warning(f"解析数组索引失败: {task_id}.{output_key}, 错误: {e}")
                    value = ""
            
            return str(value)
        
        # 否则从参数中获取
        value = parameters.get(path, '')
        
        # 如果值是列表或字典，转换为字符串
        if isinstance(value, (list, dict)):
            return str(value)
        
        return str(value)
    
    @classmethod
    def validate_parameters(cls, template: Dict[str, Any], 
                          parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证参数并应用默认值
        
        Args:
            template: 模板数据
            parameters: 用户提供的参数
            
        Returns:
            验证后的完整参数字典
        """
        template_params = template.get("parameters", {})
        result = {}
        
        # 复制用户提供的参数
        result.update(parameters)
        
        # 应用默认值
        for param_name, param_def in template_params.items():
            if param_name not in result:
                default_value = param_def.get("default", "")
                result[param_name] = default_value
                Logger.debug(f"使用默认值: {param_name} = {default_value}")
        
        return result


# 创建全局参数解析器实例
parameter_resolver = ParameterResolver()