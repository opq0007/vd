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
        from modules.template_manager import template_manager

        template_name = result.get("template_name", "")
        task_outputs = result.get("task_outputs", {})

        # 获取模板定义
        template = template_manager.get_template(template_name)
        if not template:
            Logger.warning(f"模板不存在: {template_name}")
            return None

        # 获取模板中的任务列表（按定义顺序）
        tasks = template.get("tasks", [])
        if not tasks:
            Logger.warning(f"模板中没有任务: {template_name}")
            return None

        # 获取最后一个任务
        last_task = tasks[-1]
        last_task_id = last_task["id"]
        last_task_output = task_outputs.get(last_task_id, {})

        Logger.info(f"提取最终视频: 使用最后一个任务 {last_task_id} ({last_task['name']}) 的结果")

        # 检查最后一个任务是否执行成功
        if last_task_output.get("success") is False or "error" in last_task_output:
            error_msg = last_task_output.get("error", "未知错误")
            Logger.warning(f"最后一个任务 {last_task_id} 执行失败: {error_msg}，final_video 为空")
            return None

        # 检查最后一个任务是否有输出
        if not last_task_output:
            Logger.warning(f"最后一个任务 {last_task_id} 没有输出，final_video 为空")
            return None

        # 从最后一个任务的输出中提取视频文件
        for key, value in last_task_output.items():
            if isinstance(value, str) and value.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
                Logger.info(f"找到最终视频: {value}")
                return value

        # 如果最后一个任务的输出字段中没有视频文件，检查 output 字段
        output_value = last_task_output.get("output", "")
        if output_value and isinstance(output_value, str) and output_value.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
            Logger.info(f"从 output 字段找到最终视频: {output_value}")
            return output_value

        Logger.warning(f"最后一个任务 {last_task_id} 的输出中没有找到视频文件，final_video 为空")
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
        task_times = result.get("task_times", {})  # 新增：获取任务执行时间
        
        for idx, task in enumerate(tasks, 1):
            task_id = task["id"]
            task_output = task_outputs.get(task_id, {})
            
            # 判断任务状态
            # 1. 优先检查 success 字段（如果明确标记为失败）
            if task_output.get("success") is False:
                status = "failed"
                error_msg = task_output.get("error", "任务执行失败")
            # 2. 如果有错误字段，标记为失败
            elif "error" in task_output:
                status = "failed"
                error_msg = task_output.get("error", "未知错误")
            # 3. 如果没有输出（空字典），标记为跳过
            elif not task_output:
                status = "skipped"
                error_msg = None
            # 4. 如果有输出，检查是否有实际的输出内容
            else:
                # 提取输出文件
                output_files = ResultFormatter.extract_output_files_from_task(task_output)
                if output_files:
                    status = "success"
                    error_msg = None
                else:
                    # 有输出但没有文件，标记为跳过
                    status = "skipped"
                    error_msg = None
            
            # 构建任务结果
            task_result = {
                "index": idx,
                "id": task_id,
                "name": task["name"],
                "type": task["type"],
                "status": status,
                "error": error_msg
            }
            
            # 提取输出文件
            output_files = ResultFormatter.extract_output_files_from_task(task_output)
            task_result["output_files"] = output_files[:3]  # 最多显示3个文件
            
            # 新增：添加执行时间（如果存在）
            if task_id in task_times:
                task_result["execution_time"] = task_times[task_id]
            
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

        # 统计成功/失败/跳过的任务数量
        success_count = sum(1 for task in task_results if task.get("status") == "success")
        failed_count = sum(1 for task in task_results if task.get("status") == "failed")
        skipped_count = sum(1 for task in task_results if task.get("status") == "skipped")

        # 构建格式化结果
        formatted_result = {
            "success": result.get("success", False),
            "template_name": template_name,
            "total_tasks": result.get("total_tasks"),
            "completed_tasks": result.get("completed_tasks"),
            "success_count": success_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "final_video": final_video,
            "task_results": task_results,
            "error": result.get("error") if not result.get("success") else None
        }
        
        # 新增：添加执行时间信息
        if "total_execution_time" in result:
            formatted_result["total_execution_time"] = result["total_execution_time"]
        if "task_times" in result:
            formatted_result["task_times"] = result["task_times"]
        
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
        task_times = result.get("task_times", {})  # 新增：获取任务执行时间
        total_tasks = result.get("total_tasks", 0)
        completed_tasks = result.get("completed_tasks", 0)
        total_execution_time = result.get("total_execution_time", 0)  # 新增：获取总执行时间

        # 重新构建任务结果列表以获取准确的状态统计
        from modules.template_manager import template_manager
        template = template_manager.get_template(result.get("template_name", ""))
        tasks = template.get("tasks", []) if template else []

        # 统计成功和失败的任务数量
        success_count = 0
        failed_count = 0
        skipped_count = 0

        for task in tasks:
            task_id = task["id"]
            task_output = task_outputs.get(task_id, {})

            # 判断任务状态
            if task_output.get("success") is False or "error" in task_output:
                failed_count += 1
            elif not task_output:
                skipped_count += 1
            else:
                # 检查是否有输出文件
                output_files = ResultFormatter.extract_output_files_from_task(task_output)
                if output_files:
                    success_count += 1
                else:
                    skipped_count += 1

        # 计算成功率，避免除零错误
        success_rate = (success_count / total_tasks * 100) if total_tasks > 0 else 0.0
        
        # 新增：计算总执行时间统计
        total_time_str = f"{total_execution_time:.3f}秒" if total_execution_time > 0 else "-"
        
        html = f"""
        <div style="border: 1px solid #ddd; padding: 15px; border-radius: 5px; background-color: #f9f9f9;">
            <h4 style="margin-top: 0; color: #333;">📋 任务执行详情</h4>
            <p style="margin-bottom: 15px;">
                <strong>总任务数:</strong> {total_tasks} |
                <strong style="color: #4CAF50;">✅ 成功:</strong> {success_count} |
                <strong style="color: #f44336;">❌ 失败:</strong> {failed_count} |
                <strong style="color: #FF9800;">⏭️ 跳过:</strong> {skipped_count} |
                <strong>成功率:</strong> {success_rate:.1f}% |
                <strong style="color: #2196F3;">⏱️ 总耗时:</strong> {total_time_str}
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
                        <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">耗时</th>
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
                
                # 新增：获取任务执行时间
                task_time_str = f"{task_times.get(task_id, 0):.3f}秒" if task_id in task_times else "-"
                
                # 判断任务状态（优先检查 success 字段）
                if task_output.get("success") is False:
                    status = "❌ 失败"
                    status_color = "#f44336"
                    error_msg = task_output.get("error", "任务执行失败")
                    output_files = "-"
                    remark = f"错误: {error_msg}"
                elif "error" in task_output:
                    status = "❌ 失败"
                    status_color = "#f44336"
                    error_msg = task_output.get("error", "未知错误")
                    output_files = "-"
                    remark = f"错误: {error_msg}"
                elif not task_output:
                    status = "⏭️ 跳过"
                    status_color = "#FF9800"
                    output_files = "-"
                    remark = "未执行"
                else:
                    # 提取输出文件（格式化为前端展示格式）
                    output_files = ResultFormatter.extract_output_files_from_task(task_output, format_for_display=True)
                    if output_files and output_files != "-":
                        status = "✅ 成功"
                        status_color = "#4CAF50"
                        remark = "执行成功"
                    else:
                        status = "⏭️ 跳过"
                        status_color = "#FF9800"
                        remark = "无输出"
                
                html += f"""
                    <tr style="background-color: {'#f5f5f5' if idx % 2 == 0 else 'white'};">
                        <td style="padding: 8px; border: 1px solid #ddd;">{idx}</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{task_name}</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{task_type}</td>
                        <td style="padding: 8px; border: 1px solid #ddd; color: {status_color}; font-weight: bold;">{status}</td>
                        <td style="padding: 8px; border: 1px solid #ddd; font-size: 12px;">{output_files}</td>
                        <td style="padding: 8px; border: 1px solid #ddd; font-size: 12px;">{remark}</td>
                        <td style="padding: 8px; border: 1px solid #ddd; font-size: 12px;">{task_time_str}</td>
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