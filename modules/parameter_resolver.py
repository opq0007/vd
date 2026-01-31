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
                       task_outputs: Dict[str, Any]) -> Any:
        """
        解析字符串中的参数
        
        Args:
            text: 字符串
            parameters: 参数值字典
            task_outputs: 任务输出字典
            
        Returns:
            解析后的值（可能是字符串或列表）
        """
        # 检查是否整个字符串就是一个参数占位符
        match = cls.PARAM_PATTERN.fullmatch(text)
        if match:
            param_path = match.group(1)
            value = cls._get_value(param_path, parameters, task_outputs)
            # 如果返回值是列表或字典，直接返回，保持原始类型
            if isinstance(value, (list, dict)):
                Logger.debug(f"参数 {param_path} 返回复杂类型: {type(value)}")
                return value
            # 否则转换为字符串
            return str(value)
        
        # 如果字符串包含多个参数占位符或普通文本，正常替换
        def replace_match(match):
            param_path = match.group(1)
            value = cls._get_value(param_path, parameters, task_outputs)
            # 将任何类型转换为字符串
            if isinstance(value, (list, dict)):
                return str(value)
            return str(value)
        
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

            # 检查是否包含数组索引（如 output[0]）
            if '[' in output_key and output_key.endswith(']'):
                try:
                    # 分离键名和索引
                    # 支持两种格式：
                    # 1. task.output[0] -> parts[1:] = ['output[0]']
                    # 2. task.data.items[0] -> parts[1:] = ['data', 'items[0]']

                    # 提取数组索引信息
                    def extract_array_index(key_part):
                        """从键中提取数组索引，返回 (clean_key, index_str)"""
                        if '[' in key_part and key_part.endswith(']'):
                            bracket_start = key_part.index('[')
                            clean_key = key_part[:bracket_start]
                            index_str = key_part[bracket_start + 1:-1]  # 去掉方括号
                            return clean_key, index_str
                        return None, None

                    # 处理每个路径部分
                    value = task_output
                    index_to_apply = None  # 记录需要应用的索引

                    for i, part in enumerate(parts[1:]):
                        # 检查是否包含数组索引
                        clean_key, index_str = extract_array_index(part)

                        if clean_key is not None:
                            # 这部分包含数组索引
                            if isinstance(value, dict):
                                # 先获取数组
                                array_value = value.get(clean_key, [])
                                value = array_value
                            elif isinstance(value, list) and i > 0:
                                # 如果value已经是列表，可能是在处理数组元素
                                value = value
                            else:
                                Logger.warning(f"任务 {task_id} 的路径 {output_key} 在键 {part} 处无法获取数组")
                                return ""

                            # 保存索引，稍后应用
                            index_to_apply = index_str
                        else:
                            # 普通键，直接访问
                            if isinstance(value, dict):
                                value = value.get(part)
                            else:
                                Logger.warning(f"任务 {task_id} 的路径 {output_key} 在键 {part} 处不是字典类型")
                                return ""

                            if value is None:
                                Logger.warning(f"任务 {task_id} 的路径 {output_key} 在键 {part} 处为空")
                                return ""

                    # 应用数组索引
                    if index_to_apply is not None and isinstance(value, list):
                        try:
                            index = int(index_to_apply)
                            if len(value) == 0:
                                Logger.warning(f"数组为空: {task_id}.{output_key}")
                                return ""
                            else:
                                # 使用取模运算处理索引越界
                                actual_index = index % len(value)
                                value = value[actual_index]
                                if index != actual_index:
                                    Logger.info(f"数组索引 {index} 越界，使用取模后的索引 {actual_index}: {task_id}.{output_key} = {value}")
                                else:
                                    Logger.info(f"获取数组索引值: {task_id}.{output_key} = {value}")
                        except (ValueError, IndexError) as e:
                            Logger.warning(f"解析数组索引失败: {task_id}.{output_key}, 错误: {e}")
                            return ""
                    elif index_to_apply is not None:
                        Logger.warning(f"期望数组类型但得到: {task_id}.{output_key}, 类型: {type(value)}")
                        return ""

                except Exception as e:
                    Logger.warning(f"解析路径失败: {task_id}.{output_key}, 错误: {e}")
                    return ""
            else:
                # 普通嵌套路径访问（如 output.full_text）
                if isinstance(task_output, dict):
                    value = task_output
                    for key in parts[1:]:
                        if isinstance(value, dict):
                            value = value.get(key)
                            if value is None:
                                Logger.warning(f"任务 {task_id} 的路径 {output_key} 不存在，在键 {key} 处中断")
                                return ""
                        else:
                            Logger.warning(f"任务 {task_id} 的路径 {output_key} 在键 {key} 处不是字典类型")
                            return ""

                    if value is None or value == '':
                        Logger.warning(f"任务 {task_id} 的路径 {output_key} 为空，task_output={task_output}")
                else:
                    value = str(task_output)

            # 如果值是列表或字典，保持原始类型
            if isinstance(value, (list, dict)):
                Logger.debug(f"任务输出 {task_id}.{output_key} 返回复杂类型: {type(value)}")
                return value

            return str(value)

        # 否则从参数中获取
        value = parameters.get(path, '')

        # 如果值是列表或字典，直接返回（保持原始类型）
        if isinstance(value, (list, dict)):
            return value

        # 其他类型转换为字符串
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