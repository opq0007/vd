"""
文件持久化模块

支持将本地文件持久化到多个平台：
- HuggingFace Hub（推荐）
- ModelScope Hub

支持功能：
- 上传单个文件
- 上传文件夹
- 批量上传多个文件
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
from enum import Enum

from utils import Logger


class PlatformType(Enum):
    """支持的平台类型"""
    HUGGINGFACE = "huggingface"
    MODELSCOPE = "modelscope"


@dataclass
class UploadResult:
    """上传结果"""
    success: bool
    platform: str
    repo_id: Optional[str] = None
    file_path: Optional[str] = None
    repo_url: Optional[str] = None
    download_url: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None


class BasePlatformUploader:
    """平台上传器基类"""

    def __init__(self, token: str):
        """
        初始化上传器

        Args:
            token: 平台认证 token
        """
        self.token = token
        self._client = None

    def connect(self) -> bool:
        """连接到平台"""
        raise NotImplementedError("子类必须实现 connect 方法")

    def upload_file(
        self,
        file_path: str,
        repo_id: str,
        path_in_repo: str,
        repo_type: str = "dataset",
        commit_message: str = "Upload file"
    ) -> UploadResult:
        """
        上传单个文件

        Args:
            file_path: 本地文件路径
            repo_id: 仓库 ID (如: username/repo-name)
            path_in_repo: 仓库中的文件路径
            repo_type: 仓库类型 (model/dataset/space)
            commit_message: 提交消息

        Returns:
            UploadResult: 上传结果
        """
        raise NotImplementedError("子类必须实现 upload_file 方法")

    def upload_folder(
        self,
        folder_path: str,
        repo_id: str,
        path_in_repo: str = "",
        repo_type: str = "dataset",
        commit_message: str = "Upload folder"
    ) -> UploadResult:
        """
        上传文件夹

        Args:
            folder_path: 本地文件夹路径
            repo_id: 仓库 ID
            path_in_repo: 仓库中的文件夹路径
            repo_type: 仓库类型
            commit_message: 提交消息

        Returns:
            UploadResult: 上传结果
        """
        raise NotImplementedError("子类必须实现 upload_folder 方法")


class HuggingFaceUploader(BasePlatformUploader):
    """HuggingFace 平台上传器"""

    def __init__(self, token: str):
        super().__init__(token)
        self._huggingface_hub = None

    def connect(self) -> bool:
        """连接到 HuggingFace"""
        try:
            from huggingface_hub import HfApi
            self._client = HfApi(token=self.token)
            Logger.info("成功连接到 HuggingFace Hub")
            return True
        except ImportError:
            Logger.error("未安装 huggingface_hub 库，请运行: pip install huggingface_hub")
            return False
        except Exception as e:
            Logger.error(f"连接 HuggingFace 失败: {str(e)}")
            return False

    def upload_file(
        self,
        file_path: str,
        repo_id: str,
        path_in_repo: str,
        repo_type: str = "dataset",
        commit_message: str = "Upload file"
    ) -> UploadResult:
        """上传单个文件到 HuggingFace"""
        try:
            if not self._client:
                if not self.connect():
                    return UploadResult(
                        success=False,
                        platform=PlatformType.HUGGINGFACE.value,
                        error="无法连接到 HuggingFace"
                    )

            # 检查文件是否存在
            if not os.path.exists(file_path):
                return UploadResult(
                    success=False,
                    platform=PlatformType.HUGGINGFACE.value,
                    error=f"文件不存在: {file_path}"
                )

            Logger.info(f"开始上传文件到 HuggingFace: {file_path} -> {repo_id}/{path_in_repo}")

            # 上传文件
            self._client.upload_file(
                path_or_fileobj=file_path,
                path_in_repo=path_in_repo,
                repo_id=repo_id,
                repo_type=repo_type,
                commit_message=commit_message,
                token=self.token
            )

            repo_url = f"https://huggingface.co/datasets/{repo_id}" if repo_type == "dataset" else f"https://huggingface.co/{repo_id}"
            download_url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{path_in_repo}" if repo_type == "dataset" else f"https://huggingface.co/{repo_id}/resolve/main/{path_in_repo}"

            return UploadResult(
                success=True,
                platform=PlatformType.HUGGINGFACE.value,
                repo_id=repo_id,
                file_path=path_in_repo,
                repo_url=repo_url,
                download_url=download_url,
                message=f"文件上传成功: {file_path}"
            )

        except Exception as e:
            Logger.error(f"HuggingFace 上传失败: {str(e)}")
            return UploadResult(
                success=False,
                platform=PlatformType.HUGGINGFACE.value,
                error=str(e)
            )

    def upload_folder(
        self,
        folder_path: str,
        repo_id: str,
        path_in_repo: str = "",
        repo_type: str = "dataset",
        commit_message: str = "Upload folder"
    ) -> UploadResult:
        """上传文件夹到 HuggingFace"""
        try:
            if not self._client:
                if not self.connect():
                    return UploadResult(
                        success=False,
                        platform=PlatformType.HUGGINGFACE.value,
                        error="无法连接到 HuggingFace"
                    )

            # 检查文件夹是否存在
            if not os.path.exists(folder_path):
                return UploadResult(
                    success=False,
                    platform=PlatformType.HUGGINGFACE.value,
                    error=f"文件夹不存在: {folder_path}"
                )

            Logger.info(f"开始上传文件夹到 HuggingFace: {folder_path} -> {repo_id}/{path_in_repo}")

            # 上传文件夹
            self._client.upload_folder(
                folder_path=folder_path,
                repo_id=repo_id,
                repo_type=repo_type,
                path_in_repo=path_in_repo,
                commit_message=commit_message,
                token=self.token
            )

            repo_url = f"https://huggingface.co/datasets/{repo_id}" if repo_type == "dataset" else f"https://huggingface.co/{repo_id}"
            download_url = f"https://huggingface.co/datasets/{repo_id}/tree/main/{path_in_repo}" if repo_type == "dataset" else f"https://huggingface.co/{repo_id}/tree/main/{path_in_repo}"

            return UploadResult(
                success=True,
                platform=PlatformType.HUGGINGFACE.value,
                repo_id=repo_id,
                file_path=path_in_repo,
                repo_url=repo_url,
                download_url=download_url,
                message=f"文件夹上传成功: {folder_path}"
            )

        except Exception as e:
            Logger.error(f"HuggingFace 文件夹上传失败: {str(e)}")
            return UploadResult(
                success=False,
                platform=PlatformType.HUGGINGFACE.value,
                error=str(e)
            )


class ModelScopeUploader(BasePlatformUploader):
    """ModelScope 平台上传器"""

    def __init__(self, token: str):
        super().__init__(token)
        self._modelscope_hub = None

    def connect(self) -> bool:
        """连接到 ModelScope"""
        try:
            from modelscope.hub.api import HubApi
            self._client = HubApi()
            self._client.login(access_token=self.token)
            Logger.info("成功连接到 ModelScope Hub")
            return True
        except ImportError:
            Logger.error("未安装 modelscope 库，请运行: pip install modelscope")
            return False
        except Exception as e:
            Logger.error(f"连接 ModelScope 失败: {str(e)}")
            return False

    def upload_file(
        self,
        file_path: str,
        repo_id: str,
        path_in_repo: str,
        repo_type: str = "dataset",
        commit_message: str = "Upload file"
    ) -> UploadResult:
        """上传单个文件到 ModelScope"""
        try:
            if not self._client:
                if not self.connect():
                    return UploadResult(
                        success=False,
                        platform=PlatformType.MODELSCOPE.value,
                        error="无法连接到 ModelScope"
                    )

            # 检查文件是否存在
            if not os.path.exists(file_path):
                return UploadResult(
                    success=False,
                    platform=PlatformType.MODELSCOPE.value,
                    error=f"文件不存在: {file_path}"
                )

            Logger.info(f"开始上传文件到 ModelScope: {file_path} -> {repo_id}/{path_in_repo}")

            # 上传文件
            self._client.upload_file(
                path_or_fileobj=file_path,
                path_in_repo=path_in_repo,
                repo_id=repo_id,
                repo_type=repo_type,
                commit_message=commit_message,
                token=self.token
            )

            repo_url = f"https://modelscope.cn/datasets/{repo_id}" if repo_type == "dataset" else f"https://modelscope.cn/models/{repo_id}"
            download_url = f"https://modelscope.cn/datasets/{repo_id}/resolve/master/{path_in_repo}" if repo_type == "dataset" else f"https://modelscope.cn/models/{repo_id}/resolve/master/{path_in_repo}"

            return UploadResult(
                success=True,
                platform=PlatformType.MODELSCOPE.value,
                repo_id=repo_id,
                file_path=path_in_repo,
                repo_url=repo_url,
                download_url=download_url,
                message=f"文件上传成功: {file_path}"
            )

        except Exception as e:
            Logger.error(f"ModelScope 上传失败: {str(e)}")
            return UploadResult(
                success=False,
                platform=PlatformType.MODELSCOPE.value,
                error=str(e)
            )

    def upload_folder(
        self,
        folder_path: str,
        repo_id: str,
        path_in_repo: str = "",
        repo_type: str = "dataset",
        commit_message: str = "Upload folder"
    ) -> UploadResult:
        """上传文件夹到 ModelScope"""
        try:
            if not self._client:
                if not self.connect():
                    return UploadResult(
                        success=False,
                        platform=PlatformType.MODELSCOPE.value,
                        error="无法连接到 ModelScope"
                    )

            # 检查文件夹是否存在
            if not os.path.exists(folder_path):
                return UploadResult(
                    success=False,
                    platform=PlatformType.MODELSCOPE.value,
                    error=f"文件夹不存在: {folder_path}"
                )

            Logger.info(f"开始上传文件夹到 ModelScope: {folder_path} -> {repo_id}/{path_in_repo}")

            # 上传文件夹
            self._client.upload_folder(
                folder_path=folder_path,
                repo_id=repo_id,
                repo_type=repo_type,
                path_in_repo=path_in_repo,
                commit_message=commit_message,
                token=self.token
            )

            repo_url = f"https://modelscope.cn/datasets/{repo_id}" if repo_type == "dataset" else f"https://modelscope.cn/models/{repo_id}"
            download_url = f"https://modelscope.cn/datasets/{repo_id}/tree/master/{path_in_repo}" if repo_type == "dataset" else f"https://modelscope.cn/models/{repo_id}/tree/master/{path_in_repo}"

            return UploadResult(
                success=True,
                platform=PlatformType.MODELSCOPE.value,
                repo_id=repo_id,
                file_path=path_in_repo,
                repo_url=repo_url,
                download_url=download_url,
                message=f"文件夹上传成功: {folder_path}"
            )

        except Exception as e:
            Logger.error(f"ModelScope 文件夹上传失败: {str(e)}")
            return UploadResult(
                success=False,
                platform=PlatformType.MODELSCOPE.value,
                error=str(e)
            )


class FilePersistenceManager:
    """文件持久化管理器"""

    def __init__(self, huggingface_token: Optional[str] = None, modelscope_token: Optional[str] = None):
        """
        初始化文件持久化管理器

        Args:
            huggingface_token: HuggingFace 认证 token
            modelscope_token: ModelScope 认证 token
        """
        self.uploaders: Dict[PlatformType, BasePlatformUploader] = {}

        if huggingface_token:
            self.uploaders[PlatformType.HUGGINGFACE] = HuggingFaceUploader(huggingface_token)

        if modelscope_token:
            self.uploaders[PlatformType.MODELSCOPE] = ModelScopeUploader(modelscope_token)

    def get_available_platforms(self) -> List[str]:
        """获取可用的平台列表"""
        return [platform.value for platform in self.uploaders.keys()]

    def upload_single_file(
        self,
        file_path: str,
        platform: str,
        repo_id: str,
        path_in_repo: Optional[str] = None,
        repo_type: str = "dataset",
        commit_message: str = "Upload file"
    ) -> UploadResult:
        """
        上传单个文件

        Args:
            file_path: 本地文件路径
            platform: 平台类型 (huggingface/modelscope)
            repo_id: 仓库 ID
            path_in_repo: 仓库中的文件路径（如果为 None，则使用 yyyyMM/文件名）
            repo_type: 仓库类型
            commit_message: 提交消息

        Returns:
            UploadResult: 上传结果
        """
        try:
            # 验证平台
            platform_type = PlatformType(platform.lower())
            if platform_type not in self.uploaders:
                return UploadResult(
                    success=False,
                    platform=platform,
                    error=f"平台 {platform} 未配置或不可用"
                )

            # 如果没有指定仓库路径，使用当前月份文件夹 + 文件名
            if path_in_repo is None:
                current_month = datetime.now().strftime("%Y%m")
                filename = os.path.basename(file_path)
                path_in_repo = f"{current_month}/{filename}"

            # 获取上传器并上传
            uploader = self.uploaders[platform_type]
            return uploader.upload_file(
                file_path=file_path,
                repo_id=repo_id,
                path_in_repo=path_in_repo,
                repo_type=repo_type,
                commit_message=commit_message
            )

        except ValueError:
            return UploadResult(
                success=False,
                platform=platform,
                error=f"不支持的平台: {platform}"
            )
        except Exception as e:
            Logger.error(f"上传文件失败: {str(e)}")
            return UploadResult(
                success=False,
                platform=platform,
                error=str(e)
            )

    def upload_folder(
        self,
        folder_path: str,
        platform: str,
        repo_id: str,
        path_in_repo: str = "",
        repo_type: str = "dataset",
        commit_message: str = "Upload folder"
    ) -> UploadResult:
        """
        上传文件夹

        Args:
            folder_path: 本地文件夹路径
            platform: 平台类型
            repo_id: 仓库 ID
            path_in_repo: 仓库中的文件夹路径（如果为空，则使用 yyyyMM）
            repo_type: 仓库类型
            commit_message: 提交消息

        Returns:
            UploadResult: 上传结果
        """
        try:
            # 验证平台
            platform_type = PlatformType(platform.lower())
            if platform_type not in self.uploaders:
                return UploadResult(
                    success=False,
                    platform=platform,
                    error=f"平台 {platform} 未配置或不可用"
                )

            # 如果没有指定仓库路径，使用当前月份文件夹
            if not path_in_repo:
                current_month = datetime.now().strftime("%Y%m")
                path_in_repo = current_month

            # 获取上传器并上传
            uploader = self.uploaders[platform_type]
            return uploader.upload_folder(
                folder_path=folder_path,
                repo_id=repo_id,
                path_in_repo=path_in_repo,
                repo_type=repo_type,
                commit_message=commit_message
            )

        except ValueError:
            return UploadResult(
                success=False,
                platform=platform,
                error=f"不支持的平台: {platform}"
            )
        except Exception as e:
            Logger.error(f"上传文件夹失败: {str(e)}")
            return UploadResult(
                success=False,
                platform=platform,
                error=str(e)
            )

    def batch_upload_files(
        self,
        file_paths: List[str],
        platform: str,
        repo_id: str,
        repo_type: str = "dataset",
        commit_message: str = "Batch upload files"
    ) -> List[UploadResult]:
        """
        批量上传多个文件

        Args:
            file_paths: 本地文件路径列表
            platform: 平台类型
            repo_id: 仓库 ID
            repo_type: 仓库类型
            commit_message: 提交消息

        Returns:
            List[UploadResult]: 上传结果列表
        """
        results = []

        for i, file_path in enumerate(file_paths):
            Logger.info(f"批量上传进度: {i+1}/{len(file_paths)} - {file_path}")

            result = self.upload_single_file(
                file_path=file_path,
                platform=platform,
                repo_id=repo_id,
                path_in_repo=None,  # 使用默认路径：yyyyMM/文件名
                repo_type=repo_type,
                commit_message=f"{commit_message} ({i+1}/{len(file_paths)})"
            )

            results.append(result)

        return results


# 创建全局实例（将在配置后初始化）
_persistence_manager: Optional[FilePersistenceManager] = None


def get_persistence_manager() -> Optional[FilePersistenceManager]:
    """获取文件持久化管理器实例"""
    return _persistence_manager


def init_persistence_manager(huggingface_token: Optional[str] = None, modelscope_token: Optional[str] = None):
    """
    初始化文件持久化管理器

    Args:
        huggingface_token: HuggingFace 认证 token
        modelscope_token: ModelScope 认证 token
    """
    global _persistence_manager
    _persistence_manager = FilePersistenceManager(
        huggingface_token=huggingface_token,
        modelscope_token=modelscope_token
    )
    Logger.info(f"文件持久化管理器已初始化，可用平台: {_persistence_manager.get_available_platforms()}")