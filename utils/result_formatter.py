"""
结果格式化工具模块

提供统一的结果格式化功能，用于API和UI层。
"""

from typing import Dict, Any, Optional, List, Union
from utils.logger import Logger


class ResultFormatter:
    """结果格式化工具类"""

    @staticmethod
    def extract_final_video(result: Dict[str, Any]) -> Optional[str]:
        """
        从执行结果中提取最终视频文件
        
        Args:
            result: 模板执行结果
            
        Returns:
            视频文件路径，如果没有则返回None
        """
        task_outputs = result.get("task_outputs", {})
        
        # 查找视频合并任务的输出
        for task_id, task_output in task_outputs.items():
            if "error" not in task_output:
                for key, value in task_output.items():
                    if isinstance(value, str) and value.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
                        return value
                        break
                # 如果找到了视频文件，跳出外层循环
                if any(isinstance(v, str) and v.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')) 
                       for v in task_output.values()):
                    break
        
        return None

    @staticmethod
    def extract_output_files_from_task(task_output: Dict[str, Any], format_for_display: bool = False) -> Union[List[str], str]:
        """
        从任务输出中提取文件路径
        
        Args:
            task_output: 任务输出
            format_for_display: 是否格式化为前端展示所需的字符串格式（默认False，返回列表）
            
        Returns:
            如果 format_for_display=False，返回文件路径列表
            如果 format_for_display=True，返回格式化的HTML字符串（用于前端展示）
        """
        files = []
        
        # 检查常见的输出字段
        for key in ["output", "output_path", "audio_path", "video_path", "image_path", "output_file"]:
            if key in task_output:
                value = task_output[key]
                if isinstance(value, str):
                    files.append(value)
                elif isinstance(value, list):
                    files.extend([str(v) for v in value if v])
        
        # 如果没有找到，检查整个字典
        if not files:
            for key, value in task_output.items():
                if isinstance(value, str) and ("output" in key.lower() or "path" in key.lower()):
                    files.append(value)
        
        # 根据参数决定返回格式
        if format_for_display:
            # 格式化为前端展示所需的字符串格式
            if len(files) > 3:
                return f"{files[0]} ... (+{len(files)-1} more)"
            elif files:
                return "<br>".join(files[:3])
            else:
                return "-"
        else:
            # 返回列表格式
            return files

    @staticmethod
    def build_task_results(result: Dict[str, Any], template_name: str) -> List[Dict[str, Any]]:
        """
        构建任务执行结果详情
        
        Args:
            result: 模板执行结果
            template_name: 模板名称
            
        Returns:
            任务结果列表
        """
        from modules.template_manager import template_manager
        
        task_results = []
        
        if not result.get("success"):
            return task_results
        
        template = template_manager.get_template(template_name)
        if not template:
            return task_results
        
        tasks = template.get("tasks", [])
        task_outputs = result.get("task_outputs", {})
        
        for idx, task in enumerate(tasks, 1):
            task_id = task["id"]
            task_output = task_outputs.get(task_id, {})
            
            # 构建任务结果
            task_result = {
                "index": idx,
                "id": task_id,
                "name": task["name"],
                "type": task["type"],
                "status": "success" if "error" not in task_output else "failed",
                "error": task_output.get("error") if "error" in task_output else None
            }
            
            # 提取输出文件
            output_files = ResultFormatter.extract_output_files_from_task(task_output)
            task_result["output_files"] = output_files[:3]  # 最多显示3个文件
            
            task_results.append(task_result)
        
        return task_results

    @staticmethod
    def format_template_result(result: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化模板执行结果，添加最终视频和任务详情
        
        Args:
            result: 原始执行结果
            
        Returns:
            格式化后的结果
        """
        template_name = result.get("template_name", "")
        
        # 提取最终视频文件
        final_video = ResultFormatter.extract_final_video(result)
        
        # 构建任务执行结果详情
        task_results = ResultFormatter.build_task_results(result, template_name)
        
        # 构建格式化结果
        formatted_result = {
            "success": result.get("success", False),
            "template_name": template_name,
            "total_tasks": result.get("total_tasks"),
            "completed_tasks": result.get("completed_tasks"),
            "final_video": final_video,
            "task_results": task_results,
            "error": result.get("error") if not result.get("success") else None
        }
        
        # 保留原始结果中的其他字段
        for key, value in result.items():
            if key not in formatted_result:
                formatted_result[key] = value
        
        return formatted_result

    @staticmethod
    def generate_task_results_html(result: Dict[str, Any]) -> str:
        """
        生成任务执行结果的HTML详情
        
        Args:
            result: 模板执行结果
            
        Returns:
            HTML字符串
        """
        from modules.template_manager import template_manager
        
        if not result.get("success"):
            error_msg = result.get("error", "未知错误")
            return f"<div style='color: red;'>处理失败: {error_msg}</div>"
        
        task_outputs = result.get("task_outputs", {})
        total_tasks = result.get("total_tasks", 0)
        completed_tasks = result.get("completed_tasks", 0)
        
        # 计算成功率，避免除零错误
        success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0
        
        html = f"""
        <div style="border: 1px solid #ddd; padding: 15px; border-radius: 5px; background-color: #f9f9f9;">
            <h4 style="margin-top: 0; color: #333;">📋 任务执行详情</h4>
            <p style="margin-bottom: 15px;">
                <strong>总任务数:</strong> {total_tasks} | 
                <strong>完成任务:</strong> {completed_tasks} | 
                <strong>成功率:</strong> {success_rate:.1f}%
            </p>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <thead>
                    <tr style="background-color: #4CAF50; color: white;">
                        <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">序号</th>
                        <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">任务名称</th>
                        <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">任务类型</th>
                        <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">状态</th>
                        <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">输出文件</th>
                        <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">备注</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # 获取模板任务列表（按执行顺序）
        template = template_manager.get_template(result.get("template_name", ""))
        
        if template:
            tasks = template.get("tasks", [])
            for idx, task in enumerate(tasks, 1):
                task_id = task["id"]
                task_name = task["name"]
                task_type = task["type"]
                
                # 获取任务执行结果
                task_output = task_outputs.get(task_id, {})
                
                # 判断任务状态
                if "error" in task_output:
                    status = "❌ 失败"
                    status_color = "#f44336"
                    error_msg = task_output.get("error", "未知错误")
                    output_files = "-"
                    remark = f"错误: {error_msg}"
                elif task_output:
                    status = "✅ 成功"
                    status_color = "#4CAF50"
                    # 提取输出文件（格式化为前端展示格式）
                    output_files = ResultFormatter.extract_output_files_from_task(task_output, format_for_display=True)
                    remark = "执行成功"
                else:
                    status = "⏭️ 跳过"
                    status_color = "#FF9800"
                    output_files = "-"
                    remark = "未执行"
                
                html += f"""
                    <tr style="background-color: {'#f5f5f5' if idx % 2 == 0 else 'white'};">
                        <td style="padding: 8px; border: 1px solid #ddd;">{idx}</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{task_name}</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{task_type}</td>
                        <td style="padding: 8px; border: 1px solid #ddd; color: {status_color}; font-weight: bold;">{status}</td>
                        <td style="padding: 8px; border: 1px solid #ddd; font-size: 12px;">{output_files}</td>
                        <td style="padding: 8px; border: 1px solid #ddd; font-size: 12px;">{remark}</td>
                    </tr>
                """
        
        html += """
                </tbody>
            </table>
        </div>
        """
        
        return html


# 创建全局实例
result_formatter = ResultFormatter()