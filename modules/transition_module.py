"""
视频转场模块 (Transition Module)

提供视频转场特效功能，集成 video_transitions 包。
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

from config import config
from utils.logger import Logger
from utils.file_utils import FileUtils


class TransitionModule:
    """视频转场模块"""

    def __init__(self):
        self.config = config
        self._processor = None

    @property
    def processor(self):
        """获取转场处理器"""
        if self._processor is None:
            from video_transitions.processor import TransitionProcessor
            self._processor = TransitionProcessor()
        return self._processor

    async def apply_transition(
        self,
        video1_path: str,
        video2_path: str,
        transition_name: str = "crossfade",
        total_frames: int = 30,
        fps: int = 30,
        width: int = 640,
        height: int = 640,
        # 任务目录配置（可选）
        job_dir: Optional[Path] = None,  # 可选的任务目录，如果提供则使用该目录
        # 输出配置（可选）
        output_dir: Optional[str] = None,  # 可选的输出目录（优先级高于 job_dir）
        output_basename: Optional[str] = None,  # 可选的输出文件名前缀
        **kwargs
    ) -> Dict[str, Any]:
        """
        应用转场效果

        Args:
            video1_path: 第一个视频/图片路径
            video2_path: 第二个视频/图片路径
            transition_name: 转场效果名称
            total_frames: 转场帧数
            fps: 帧率
            width: 输出宽度
            height: 输出高度
            job_dir: 可选的任务目录（如果提供则使用该目录）
            output_dir: 可选的输出目录（优先级高于 job_dir）
            output_basename: 可选的输出文件名前缀
            **kwargs: 其他转场参数

        Returns:
            Dict[str, Any]: 转场结果
        """
        try:
            # 创建任务目录（如果未提供）
            if job_dir is None:
                job_dir = FileUtils.create_job_dir()
            else:
                # 确保 job_dir 存在
                job_dir = Path(job_dir)
                job_dir.mkdir(parents=True, exist_ok=True)
            
            # 记录输入参数
            Logger.info(f"转场参数: video1_path={video1_path}, video2_path={video2_path}, template_dir={kwargs.get('template_dir')}")
            Logger.info(f"任务目录: {job_dir}")

            if FileUtils.is_url(video1_path):
                video1_local = FileUtils.process_path_input(video1_path, job_dir)
            else:
                video1_local = Path(video1_path).resolve()
                Logger.info(f"video1 原始路径: {video1_path}, 解析后: {video1_local}, 存在: {video1_local.exists()}")
                
                # 如果文件不存在，尝试从模板目录查找
                if not video1_local.exists():
                    # 从 kwargs 中获取 template_dir
                    template_dir_path = kwargs.get("template_dir")
                    if template_dir_path:
                        template_dir = Path(template_dir_path)
                        template_file = template_dir / video1_path
                        Logger.info(f"尝试从模板目录查找: {template_dir} / {video1_path} = {template_file}, 存在: {template_file.exists()}")
                        if template_file.exists():
                            video1_local = template_file.resolve()
                            Logger.info(f"从模板目录找到文件: {video1_local}")
                        else:
                            Logger.warning(f"模板目录中未找到文件: {video1_path}")
                    
                    # 如果模板目录中也没有，尝试直接复制到任务目录
                    if not video1_local.exists():
                        try:
                            video1_local = FileUtils.process_path_input(video1_path, job_dir)
                            if video1_local and video1_local.exists():
                                Logger.info(f"文件已复制到任务目录: {video1_local}")
                            else:
                                Logger.error(f"无法找到文件: {video1_path}")
                        except Exception as e:
                            Logger.warning(f"无法处理文件路径: {video1_path}, 错误: {e}")
                
                # 最终检查文件是否存在
                if not video1_local.exists():
                    raise ValueError(f"无法找到视频/图片文件: {video1_path}")

            if FileUtils.is_url(video2_path):
                video2_local = FileUtils.process_path_input(video2_path, job_dir)
            else:
                video2_local = Path(video2_path).resolve()
                Logger.info(f"video2 原始路径: {video2_path}, 解析后: {video2_local}, 存在: {video2_local.exists()}")
                
                # 如果文件不存在，尝试从模板目录查找
                if not video2_local.exists():
                    # 从 kwargs 中获取 template_dir
                    template_dir_path = kwargs.get("template_dir")
                    if template_dir_path:
                        template_dir = Path(template_dir_path)
                        template_file = template_dir / video2_path
                        Logger.info(f"尝试从模板目录查找: {template_dir} / {video2_path} = {template_file}, 存在: {template_file.exists()}")
                        if template_file.exists():
                            video2_local = template_file.resolve()
                            Logger.info(f"从模板目录找到文件: {video2_local}")
                        else:
                            Logger.warning(f"模板目录中未找到文件: {video2_path}")
                    
                    # 如果模板目录中也没有，尝试直接复制到任务目录
                    if not video2_local.exists():
                        try:
                            video2_local = FileUtils.process_path_input(video2_path, job_dir)
                            if video2_local and video2_local.exists():
                                Logger.info(f"文件已复制到任务目录: {video2_local}")
                            else:
                                Logger.error(f"无法找到文件: {video2_path}")
                        except Exception as e:
                            Logger.warning(f"无法处理文件路径: {video2_path}, 错误: {e}")
                
                # 最终检查文件是否存在
                if not video2_local.exists():
                    raise ValueError(f"无法找到视频/图片文件: {video2_path}")

            # 应用转场效果
            # 过滤掉 template_dir 参数，避免传递给 processor
            processor_kwargs = {k: v for k, v in kwargs.items() if k != 'template_dir'}
            
            # 确定输出目录和文件名前缀
            final_output_dir = output_dir if output_dir else str(job_dir)
            final_output_basename = output_basename if output_basename else f"{transition_name}_transition"
            
            Logger.info(f"输出配置: output_dir={final_output_dir}, output_basename={final_output_basename}")
            
            output_path, status = await self.processor.process_transition(
                str(video1_local),
                str(video2_local),
                transition_name,
                total_frames=total_frames,
                fps=fps,
                width=width,
                height=height,
                output_dir=final_output_dir,
                output_basename=final_output_basename,
                **processor_kwargs
            )

            if output_path:
                Logger.info(f"Transition applied successfully: {output_path}")
                return {
                    "success": True,
                    "output_path": output_path,
                    "transition_name": transition_name,
                    "status": status
                }
            else:
                Logger.error(f"Transition failed: {status}")
                return {
                    "success": False,
                    "error": status
                }

        except Exception as e:
            Logger.error(f"Transition application failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_available_transitions(self) -> Dict[str, Dict[str, Any]]:
        """
        获取可用的转场效果

        Returns:
            Dict[str, Dict[str, Any]]: 转场效果信息字典
        """
        try:
            return self.processor.get_available_transitions()
        except Exception as e:
            Logger.error(f"Failed to get available transitions: {e}")
            return {}

    def get_transition_params(self, transition_name: str) -> Dict[str, Any]:
        """
        获取转场效果的参数配置

        Args:
            transition_name: 转场效果名称

        Returns:
            Dict[str, Any]: 参数配置字典
        """
        try:
            return self.processor.get_transition_params(transition_name)
        except Exception as e:
            Logger.error(f"Failed to get transition params: {e}")
            return {}

    def get_transitions_by_category(self, category: str) -> list:
        """
        获取指定分类的转场效果

        Args:
            category: 分类名称

        Returns:
            list: 转场效果列表
        """
        try:
            return self.processor.get_transitions_by_category(category)
        except Exception as e:
            Logger.error(f"Failed to get transitions by category: {e}")
            return []

    async def batch_apply_transitions(
        self,
        video_paths: list,
        transition_sequence: list,
        total_frames: int = 30,
        fps: int = 30,
        width: int = 640,
        height: int = 640,
        # 任务目录配置（可选）
        job_dir: Optional[Path] = None  # 可选的任务目录，如果提供则使用该目录
    ) -> Dict[str, Any]:
        """
        批量应用转场效果

        Args:
            video_paths: 视频路径列表
            transition_sequence: 转场效果序列
            total_frames: 转场帧数
            fps: 帧率
            width: 输出宽度
            height: 输出高度

        Returns:
            Dict[str, Any]: 批量转场结果
        """
        try:
            if len(video_paths) < 2:
                return {
                    "success": False,
                    "error": "至少需要2个视频文件"
                }

            if len(transition_sequence) != len(video_paths) - 1:
                return {
                    "success": False,
                    "error": "转场效果数量必须比视频数量少1"
                }

            output_paths = []
            # 创建任务目录（如果未提供）
            if job_dir is None:
                job_dir = FileUtils.create_job_dir()
            else:
                # 确保 job_dir 存在
                job_dir = Path(job_dir)
                job_dir.mkdir(parents=True, exist_ok=True)

            # 依次应用转场效果
            current_video = video_paths[0]

            for i, (next_video, transition_name) in enumerate(zip(video_paths[1:], transition_sequence)):
                result = await self.apply_transition(
                    current_video,
                    next_video,
                    transition_name,
                    total_frames,
                    fps,
                    width,
                    height,
                    job_dir=job_dir  # 传递同一个 job_dir
                )

                if result["success"]:
                    output_paths.append(result["output_path"])
                    current_video = result["output_path"]
                else:
                    return {
                        "success": False,
                        "error": f"转场 {i+1} 失败: {result.get('error')}"
                    }

            Logger.info(f"Batch transitions applied successfully: {len(output_paths)} transitions")

            return {
                "success": True,
                "output_paths": output_paths,
                "final_output": output_paths[-1] if output_paths else None
            }

        except Exception as e:
            Logger.error(f"Batch transition application failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# 创建全局服务实例
transition_module = TransitionModule()