"""
任务编排器

负责执行模板中的任务，管理任务依赖关系和执行顺序。
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from utils.logger import Logger
from utils.file_utils import FileUtils
from modules.template_manager import template_manager
from modules.parameter_resolver import parameter_resolver, ParameterResolver
from modules.task_handlers import task_handlers


class TaskOrchestrator:
    """任务编排器"""
    
    def __init__(self):
        self._task_handlers: Dict[str, Callable] = {}
        self._register_handlers()
    
    def _register_handlers(self):
        """注册所有任务处理器"""
        # 从 task_handlers 获取所有处理器
        available_handlers = task_handlers.get_available_handlers()
        
        for task_type, description in available_handlers.items():
            handler = task_handlers.get_handler(task_type)
            if handler:
                self._task_handlers[task_type] = handler
                Logger.info(f"注册任务处理器: {task_type} ({description})")
    
    def register_handler(self, task_type: str, handler: Callable):
        """
        注册任务处理器
        
        Args:
            task_type: 任务类型
            handler: 处理函数
        """
        self._task_handlers[task_type] = handler
        Logger.info(f"注册任务处理器: {task_type}")
    
    async def execute_template(self, template_name: str, parameters: Dict[str, Any],
                              progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        执行模板
        
        Args:
            template_name: 模板名称
            parameters: 参数值
            progress_callback: 进度回调函数
            
        Returns:
            执行结果
        """
        # 加载模板
        template = template_manager.get_template(template_name)
        if not template:
            raise ValueError(f"模板不存在: {template_name}")
        
        # 验证参数
        parameters = parameter_resolver.validate_parameters(template, parameters)
        
        # 构建任务依赖图
        tasks = template.get("tasks", [])
        task_graph = self._build_task_graph(tasks)
        
        # 创建共享的输出目录
        shared_job_dir = FileUtils.create_job_dir()
        Logger.info(f"创建共享输出目录: {shared_job_dir}")
        
        # 执行任务
        task_outputs = {}
        total_tasks = len(tasks)
        completed_tasks = 0
        
        Logger.info(f"开始执行模板: {template_name}")
        Logger.info(f"总任务数: {total_tasks}")
        
        # 按拓扑顺序执行任务
        execution_order = self._topological_sort(task_graph)
        
        for task_id in execution_order:
            task = next(t for t in tasks if t["id"] == task_id)
            
            try:
                # 解析任务参数
                original_params = task.get("params", {})
                resolved_params = parameter_resolver.resolve(
                    original_params,
                    parameters,
                    task_outputs
                )
                
                # 自动设置预编码特征ID（针对TTS任务）
                if task["type"] == "tts" and "character" in template:
                    character = template["character"]
                    # 如果没有明确设置feat_id，则使用character作为feat_id
                    if "feat_id" not in resolved_params or not resolved_params["feat_id"]:
                        resolved_params["feat_id"] = character
                        Logger.info(f"自动设置TTS预编码特征ID: {character}")
                
                # 解析模板中的资源路径（相对于模板目录）
                if "template_dir" in template:
                    template_dir = Path(template["template_dir"])
                    
                    # 定义路径参数的后缀模式（使用后缀匹配替代白名单）
                    path_suffixes = (
                        '_path', '_file', '_image', '_video', '_audio',
                        '_images', '_videos', '_audios',
                        '_paths', '_files',
                        'input',  # 添加 input 参数，用于 video_editor 等任务
                        'video1',  # 添加 video1 参数，用于 video_transition 任务
                        'video2'   # 添加 video2 参数，用于 video_transition 任务
                    )
                    
                    # 检查参数中的路径是否需要解析
                    for key, value in resolved_params.items():
                        # 检查参数名是否以路径相关的后缀结尾
                        is_path_param = any(key.endswith(suffix) for suffix in path_suffixes)
                        
                        if not is_path_param:
                            Logger.debug(f"跳过非路径参数: {key}")
                            continue
                        
                        # 检查原始值是否是占位符
                        original_value = original_params.get(key)
                        is_placeholder = isinstance(original_value, str) and ParameterResolver.PARAM_PATTERN.search(original_value)
                        
                        # 只有当原始值不是占位符时，才尝试在模板目录下查找
                        if is_placeholder:
                            Logger.debug(f"跳过占位符参数: {key} (原始值: {original_value})")
                            continue
                            
                        if isinstance(value, str) and not Path(value).is_absolute():
                            # 检查是否是包含换行符的多行字符串（如视频合并任务的 videos 参数）
                            if '\n' in value:
                                # 处理多行字符串
                                lines = [line.strip() for line in value.split('\n') if line.strip()]
                                resolved_lines = []
                                for line in lines:
                                    if not Path(line).is_absolute():
                                        # 检查是否是模板目录下的相对路径
                                        template_resource = template_dir / line
                                        if template_resource.exists():
                                            resolved_lines.append(str(template_resource))
                                            Logger.debug(f"解析模板资源路径（多行）: {line} -> {template_resource}")
                                        else:
                                            # 抛出异常，而不是只记录警告
                                            raise FileNotFoundError(f"模板资源文件不存在: {template_resource}")
                                    else:
                                        resolved_lines.append(line)
                                resolved_params[key] = '\n'.join(resolved_lines)
                            else:
                                # 处理单行字符串
                                template_resource = template_dir / value
                                Logger.info(f"检查参数 {key}: value={value}, template_resource={template_resource}, exists={template_resource.exists()}")
                                if template_resource.exists():
                                    resolved_params[key] = str(template_resource)
                                    Logger.info(f"解析模板资源路径: {value} -> {template_resource}")
                                else:
                                    # 抛出异常，而不是只记录警告
                                    raise FileNotFoundError(f"模板资源文件不存在: {template_resource}")
                        elif isinstance(value, list):
                            # 处理数组类型的参数
                            resolved_list = []
                            for item in value:
                                if isinstance(item, str) and not Path(item).is_absolute():
                                    # 检查是否是模板目录下的相对路径
                                    template_resource = template_dir / item
                                    if template_resource.exists():
                                        resolved_list.append(str(template_resource))
                                        Logger.debug(f"解析模板资源路径（数组）: {item} -> {template_resource}")
                                    else:
                                        # 抛出异常，而不是只记录警告
                                        raise FileNotFoundError(f"模板资源文件不存在: {template_resource}")
                                else:
                                    resolved_list.append(item)
                            resolved_params[key] = resolved_list
                
                # 执行任务
                Logger.info(f"执行任务: {task['name']} ({task_id})")
                
                # 将共享的输出目录传递给任务处理器
                resolved_params["job_dir"] = str(shared_job_dir)
                
                # 将任务ID和任务类型传递给任务处理器，用于生成文件名
                resolved_params["task_id"] = task_id
                resolved_params["task_type"] = task["type"]
                
                # 将模板目录传递给任务处理器，用于访问模板资源
                if "template_dir" in template:
                    resolved_params["template_dir"] = template["template_dir"]
                
                result = await self._execute_task(task, resolved_params)
                
                # 保存任务输出
                task_outputs[task_id] = result
                
                completed_tasks += 1
                progress = completed_tasks / total_tasks
                
                # 调用进度回调
                if progress_callback:
                    await progress_callback({
                        "task_id": task_id,
                        "task_name": task["name"],
                        "progress": progress,
                        "completed": completed_tasks,
                        "total": total_tasks,
                        "status": "completed"
                    })
                
                Logger.info(f"任务完成: {task['name']} ({task_id}), 进度: {progress:.1%}")
                
            except Exception as e:
                Logger.error(f"任务失败: {task['name']} ({task_id}), 错误: {e}")
                
                # 调用进度回调
                if progress_callback:
                    await progress_callback({
                        "task_id": task_id,
                        "task_name": task["name"],
                        "progress": completed_tasks / total_tasks,
                        "completed": completed_tasks,
                        "total": total_tasks,
                        "status": "failed",
                        "error": str(e)
                    })
                
                # 继续执行其他任务
                task_outputs[task_id] = {"error": str(e)}
        
        Logger.info(f"模板执行完成: {template_name}")
        
        return {
            "success": True,
            "template_name": template_name,
            "task_outputs": task_outputs,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks
        }
    
    def _build_task_graph(self, tasks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        构建任务依赖图
        
        Args:
            tasks: 任务列表
            
        Returns:
            任务依赖图 {task_id: [依赖的任务ID列表]}
        """
        graph = {}
        
        for task in tasks:
            task_id = task["id"]
            depends_on = task.get("depends_on", [])
            graph[task_id] = depends_on
        
        return graph
    
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """
        拓扑排序
        
        Args:
            graph: 任务依赖图
            
        Returns:
            排序后的任务ID列表
        """
        # 计算入度
        in_degree = {task_id: 0 for task_id in graph}
        for task_id, dependencies in graph.items():
            for dep in dependencies:
                if dep in in_degree:
                    in_degree[task_id] += 1
        
        # 找到入度为0的节点
        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            task_id = queue.pop(0)
            result.append(task_id)
            
            # 减少依赖该任务的任务的入度
            for other_task_id, dependencies in graph.items():
                if task_id in dependencies:
                    in_degree[other_task_id] -= 1
                    if in_degree[other_task_id] == 0:
                        queue.append(other_task_id)
        
        return result
    
    async def _execute_task(self, task: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个任务
        
        Args:
            task: 任务定义
            params: 解析后的参数
            
        Returns:
            任务输出
        """
        task_type = task["type"]
        
        # 获取任务处理器
        handler = self._task_handlers.get(task_type)
        
        if handler is None:
            Logger.warning(f"未找到任务处理器: {task_type}")
            return {"error": f"未找到任务处理器: {task_type}"}
        
        # 执行任务
        return await handler(params)


# 创建全局任务编排器实例
task_orchestrator = TaskOrchestrator()