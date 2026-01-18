"""
模板管理模块

负责加载、验证和管理处理模板。
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from utils.logger import Logger


class TemplateManager:
    """模板管理器"""
    
    def __init__(self, template_dir: str = "templates"):
        """
        初始化模板管理器
        
        Args:
            template_dir: 模板目录路径
        """
        self.template_dir = Path(template_dir)
        self.template_dir.mkdir(exist_ok=True)
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._load_templates()
    
    def _load_templates(self):
        """加载所有模板"""
        self._templates = {}
        
        # 遍历模板目录（递归扫描子目录）
        for template_file in self.template_dir.rglob("*.json"):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template = json.load(f)
                
                # 验证模板格式
                if self._validate_template(template):
                    # 从文件路径中提取信息
                    # 例如：templates/atm/atm_birthday.json
                    # -> character = "atm", theme = "birthday"
                    relative_path = template_file.relative_to(self.template_dir)
                    parts = relative_path.parts
                    
                    if len(parts) >= 2:
                        # 文件在子目录中：character/theme.json
                        character = parts[0]  # 子目录名 = 操作模板对象名称
                        theme = template_file.stem  # 文件名（不含扩展名）= character_theme
                        
                        # 提取主题名（去掉character前缀）
                        if theme.startswith(f"{character}_"):
                            theme_name = theme[len(f"{character}_"):]
                        else:
                            theme_name = theme
                        
                        # 添加模板元数据
                        template["character"] = character
                        template["theme"] = theme_name
                        template["template_file"] = str(template_file)
                        template["template_dir"] = str(template_file.parent)
                    
                    template_name = template.get("name", template_file.stem)
                    self._templates[template_name] = template
                    Logger.info(f"加载模板: {template_name} ({template_file.name})")
                else:
                    Logger.warning(f"模板格式无效: {template_file.name}")
            except Exception as e:
                Logger.error(f"加载模板失败: {template_file.name}, 错误: {e}")
    
    def _validate_template(self, template: Dict[str, Any]) -> bool:
        """
        验证模板格式
        
        Args:
            template: 模板数据
            
        Returns:
            是否有效
        """
        # 检查必需字段
        required_fields = ["name", "version", "parameters", "tasks"]
        for field in required_fields:
            if field not in template:
                Logger.error(f"模板缺少必需字段: {field}")
                return False
        
        # 检查参数格式
        parameters = template.get("parameters", {})
        if not isinstance(parameters, dict):
            Logger.error("parameters 必须是字典类型")
            return False
        
        # 检查任务格式
        tasks = template.get("tasks", [])
        if not isinstance(tasks, list):
            Logger.error("tasks 必须是列表类型")
            return False
        
        # 检查每个任务的格式
        for task in tasks:
            if not isinstance(task, dict):
                Logger.error("task 必须是字典类型")
                return False
            
            if "id" not in task or "type" not in task:
                Logger.error("task 缺少必需字段: id 或 type")
                return False
        
        return True
    
    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取模板
        
        Args:
            name: 模板名称
            
        Returns:
            模板数据，如果不存在则返回 None
        """
        return self._templates.get(name)
    
    def get_template_names(self) -> List[str]:
        """
        获取所有模板名称
        
        Returns:
            模板名称列表
        """
        return list(self._templates.keys())
    
    def get_template_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取模板信息（不包括任务详情）
        
        Args:
            name: 模板名称
            
        Returns:
            模板信息，如果不存在则返回 None
        """
        template = self.get_template(name)
        if not template:
            return None
        
        return {
            "name": template.get("name"),
            "description": template.get("description", ""),
            "version": template.get("version"),
            "parameters": template.get("parameters", {}),
            "task_count": len(template.get("tasks", []))
        }
    
    def get_template_parameters(self, name: str) -> Dict[str, Any]:
        """
        获取模板的参数定义
        
        Args:
            name: 模板名称
            
        Returns:
            参数定义字典
        """
        template = self.get_template(name)
        if not template:
            return {}
        
        return template.get("parameters", {})
    
    def reload_templates(self):
        """重新加载所有模板"""
        Logger.info("重新加载模板...")
        self._load_templates()
        Logger.info(f"已加载 {len(self._templates)} 个模板")


# 创建全局模板管理器实例
template_manager = TemplateManager()