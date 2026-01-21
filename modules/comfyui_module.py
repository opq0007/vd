"""
ComfyUI 集成模块

提供与 ComfyUI 服务的集成能力，支持：
- 连接 ComfyUI 服务器
- 执行工作流（workflow）
- 上传/下载工作流文件
- 获取执行结果
"""

import json
import uuid
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path
import aiohttp
from dataclasses import dataclass

from utils.logger import Logger

# workflows 目录路径
WORKFLOWS_DIR = Path(__file__).parent.parent / "workflows"


@dataclass
class ComfyUIResult:
    """ComfyUI 执行结果"""
    success: bool
    prompt_id: Optional[str] = None
    output_images: Optional[List[Dict[str, Any]]] = None
    output_audio: Optional[List[Dict[str, Any]]] = None
    output_videos: Optional[List[Dict[str, Any]]] = None
    output_files: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    message: Optional[str] = None


class ComfyUIClient:
    """ComfyUI 客户端"""

    def __init__(
        self,
        server_url: str,
        client_id: Optional[str] = None,
        auth_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        初始化 ComfyUI 客户端

        Args:
            server_url: ComfyUI 服务器地址，例如 http://127.0.0.1:8188
            client_id: 客户端 ID，如果不提供则自动生成
            auth_token: 认证 Token（优先级高于 username/password）
            username: 用户名（用于基本认证）
            password: 密码（用于基本认证）
        """
        self.server_url = server_url.rstrip('/')
        self.client_id = client_id or str(uuid.uuid4())
        self.auth_token = auth_token
        self.username = username
        self.password = password
        self.session: Optional[aiohttp.ClientSession] = None

    def _get_auth_headers(self) -> Dict[str, str]:
        """
        获取认证头

        Returns:
            Dict[str, str]: 认证头字典
        """
        headers = {}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        return headers

    def _get_auth(self) -> Optional[aiohttp.BasicAuth]:
        """
        获取基本认证对象

        Returns:
            Optional[aiohttp.BasicAuth]: 认证对象
        """
        if self.username and self.password and not self.auth_token:
            return aiohttp.BasicAuth(self.username, self.password)
        return None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    async def connect(self) -> bool:
        """
        连接到 ComfyUI 服务器

        Returns:
            bool: 连接是否成功
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            headers = self._get_auth_headers()
            auth = self._get_auth()

            async with self.session.get(
                f"{self.server_url}/system_stats",
                headers=headers,
                auth=auth
            ) as response:
                if response.status == 200:
                    Logger.info(f"成功连接到 ComfyUI 服务器: {self.server_url}")
                    return True
                elif response.status == 401:
                    Logger.error(f"ComfyUI 服务器认证失败: {response.status}")
                    return False
                else:
                    Logger.error(f"ComfyUI 服务器响应异常: {response.status}")
                    return False
        except Exception as e:
            Logger.error(f"连接 ComfyUI 服务器失败: {str(e)}")
            return False

    async def get_object_info(self) -> Dict[str, Any]:
        """
        获取 ComfyUI 对象信息（节点列表）

        Returns:
            Dict[str, Any]: 对象信息
        """
        try:
            if not self.session:
                await self.connect()

            headers = self._get_auth_headers()
            auth = self._get_auth()

            async with self.session.get(
                f"{self.server_url}/object_info",
                headers=headers,
                auth=auth
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    Logger.error(f"获取对象信息失败: {response.status}")
                    return {}
        except Exception as e:
            Logger.error(f"获取对象信息异常: {str(e)}")
            return {}

    async def get_history(self, prompt_id: str) -> Dict[str, Any]:
        """
        获取执行历史

        Args:
            prompt_id: 提示 ID

        Returns:
            Dict[str, Any]: 执行历史
        """
        try:
            if not self.session:
                await self.connect()

            headers = self._get_auth_headers()
            auth = self._get_auth()

            async with self.session.get(
                f"{self.server_url}/history/{prompt_id}",
                headers=headers,
                auth=auth
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get(prompt_id, {})
                else:
                    Logger.error(f"获取历史失败: {response.status}")
                    return {}
        except Exception as e:
            Logger.error(f"获取历史异常: {str(e)}")
            return {}

    async def execute_workflow(
        self,
        workflow: Dict[str, Any],
        upload_files: Optional[Dict[str, str]] = None,
        timeout: int = 300
    ) -> ComfyUIResult:
        """
        执行工作流

        Args:
            workflow: 工作流定义（JSON 格式）
            upload_files: 要上传的文件 {filename: filepath}，支持图片、音频、视频等
            timeout: 超时时间（秒），默认 300 秒

        Returns:
            ComfyUIResult: 执行结果
        """
        try:
            if not self.session:
                await self.connect()

            # 上传文件
            if upload_files:
                for filename, filepath in upload_files.items():
                    await self.upload_file(filename, filepath)

            # 提交工作流
            prompt = {
                "prompt": workflow,
                "client_id": self.client_id
            }

            headers = self._get_auth_headers()
            auth = self._get_auth()

            async with self.session.post(
                f"{self.server_url}/prompt",
                json=prompt,
                headers=headers,
                auth=auth
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return ComfyUIResult(
                        success=False,
                        error=f"提交工作流失败: {response.status}, 错误: {error_text}"
                    )
                
                # 从 ComfyUI 响应中获取真实的 prompt_id
                response_data = await response.json()
                prompt_id = response_data.get("prompt_id")
                
                if not prompt_id:
                    return ComfyUIResult(
                        success=False,
                        error="ComfyUI 响应中未找到 prompt_id"
                    )
                
                Logger.info(f"工作流已提交，prompt_id: {prompt_id}")

            # 使用 ComfyUI 返回的真实 prompt_id 等待执行完成
            result = await self._wait_for_completion(prompt_id, timeout)
            return result

        except Exception as e:
            Logger.error(f"执行工作流异常: {str(e)}")
            return ComfyUIResult(
                success=False,
                error=str(e)
            )

    async def upload_file(
        self,
        filename: str,
        filepath: str,
        overwrite: bool = True,
        file_type: str = "input"
    ) -> bool:
        """
        上传文件到 ComfyUI（支持图片、音频、视频等多种格式）

        注意：ComfyUI 只有一个 /upload/image 端点，所有文件都上传到这个端点，
        但需要根据文件类型设置正确的 MIME 类型。

        Args:
            filename: 文件名
            filepath: 本地文件路径
            overwrite: 是否覆盖已存在的文件
            file_type: 文件类型（input/output）

        Returns:
            bool: 上传是否成功
        """
        try:
            if not self.session:
                await self.connect()

            # 获取文件扩展名
            file_ext = Path(filename).suffix.lower()
            
            # 定义 MIME 类型映射
            mime_types = {
                # 图片
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.bmp': 'image/bmp',
                '.webp': 'image/webp',
                # 音频
                '.mp3': 'audio/mpeg',
                '.wav': 'audio/wav',
                '.ogg': 'audio/ogg',
                '.flac': 'audio/flac',
                '.m4a': 'audio/mp4',
                '.aac': 'audio/aac',
                # 视频
                '.mp4': 'video/mp4',
                '.avi': 'video/x-msvideo',
                '.mov': 'video/quicktime',
                '.mkv': 'video/x-matroska',
                '.webm': 'video/webm'
            }
            
            # 获取 MIME 类型，默认为 application/octet-stream
            mime_type = mime_types.get(file_ext, 'application/octet-stream')

            with open(filepath, 'rb') as f:
                data = aiohttp.FormData()
                # 所有文件都上传到 /upload/image 端点，使用 'image' 字段名
                # 但设置正确的 MIME 类型
                data.add_field('image', f, filename=filename, content_type=mime_type)
                data.add_field('overwrite', str(overwrite).lower())
                data.add_field('type', file_type)

                headers = self._get_auth_headers()
                auth = self._get_auth()

                # 所有文件都使用 /upload/image 端点
                async with self.session.post(
                    f"{self.server_url}/upload/image",
                    data=data,
                    headers=headers,
                    auth=auth
                ) as response:
                    if response.status == 200:
                        Logger.info(f"文件上传成功: {filename} (类型: {file_ext}, MIME: {mime_type})")
                        return True
                    else:
                        error_text = await response.text()
                        Logger.error(f"文件上传失败: {response.status}, 错误: {error_text}")
                        return False
        except Exception as e:
            Logger.error(f"上传文件异常: {str(e)}")
            return False

    async def _wait_for_completion(
        self,
        prompt_id: str,
        timeout: int = 300
    ) -> ComfyUIResult:
        """
        等待工作流执行完成

        Args:
            prompt_id: 提示 ID（必须是 ComfyUI 返回的真实 prompt_id）
            timeout: 超时时间（秒）

        Returns:
            ComfyUIResult: 执行结果
        """
        import time
        start_time = time.time()

        Logger.info(f"开始等待工作流执行完成，prompt_id: {prompt_id}, 超时时间: {timeout}秒")

        while True:
            # 检查超时
            if time.time() - start_time > timeout:
                Logger.error(f"工作流执行超时，prompt_id: {prompt_id}")
                return ComfyUIResult(
                    success=False,
                    prompt_id=prompt_id,
                    error=f"执行超时（{timeout}秒）"
                )

            # 获取执行状态
            history = await self.get_history(prompt_id)
            if not history:
                # 如果没有历史记录，说明工作流还在执行中
                await asyncio.sleep(0.5)
                continue

            # 检查是否完成
            if 'outputs' in history:
                Logger.info(f"工作流执行完成，prompt_id: {prompt_id}")
                output_images = []
                output_audio = []
                output_videos = []
                output_files = []

                # 提取输出内容
                for node_id, node_output in history['outputs'].items():
                    # 处理图片输出
                    if 'images' in node_output:
                        for image_info in node_output['images']:
                            image_url = f"{self.server_url}/view?filename={image_info['filename']}&subfolder={image_info.get('subfolder', '')}&type={image_info.get('type', 'output')}"
                            output_images.append({
                                'url': image_url,
                                'filename': image_info['filename'],
                                'subfolder': image_info.get('subfolder', ''),
                                'type': image_info.get('type', 'output')
                            })

                    # 处理音频输出
                    if 'audio' in node_output:
                        for audio_info in node_output['audio']:
                            audio_url = f"{self.server_url}/view?filename={audio_info['filename']}&subfolder={audio_info.get('subfolder', '')}&type={audio_info.get('type', 'output')}"
                            output_audio.append({
                                'url': audio_url,
                                'filename': audio_info['filename'],
                                'subfolder': audio_info.get('subfolder', ''),
                                'type': audio_info.get('type', 'output')
                            })

                    # 处理视频输出
                    if 'videos' in node_output:
                        for video_info in node_output['videos']:
                            video_url = f"{self.server_url}/view?filename={video_info['filename']}&subfolder={video_info.get('subfolder', '')}&type={video_info.get('type', 'output')}"
                            output_videos.append({
                                'url': video_url,
                                'filename': video_info['filename'],
                                'subfolder': video_info.get('subfolder', ''),
                                'type': video_info.get('type', 'output')
                            })

                    # 处理通用文件输出
                    if 'files' in node_output:
                        for file_info in node_output['files']:
                            file_url = f"{self.server_url}/view?filename={file_info['filename']}&subfolder={file_info.get('subfolder', '')}&type={file_info.get('type', 'output')}"
                            output_files.append({
                                'url': file_url,
                                'filename': file_info['filename'],
                                'subfolder': file_info.get('subfolder', ''),
                                'type': file_info.get('type', 'output')
                            })

                return ComfyUIResult(
                    success=True,
                    prompt_id=prompt_id,
                    output_images=output_images,
                    output_audio=output_audio,
                    output_videos=output_videos,
                    output_files=output_files,
                    message="工作流执行成功"
                )

            # 等待后继续检查
            await asyncio.sleep(0.5)

    async def download_file(self, filename: str, output_path: str, file_type: str = "output") -> bool:
        """
        从 ComfyUI 下载文件

        Args:
            filename: 文件名
            output_path: 输出路径
            file_type: 文件类型（input/output）

        Returns:
            bool: 下载是否成功
        """
        try:
            if not self.session:
                await self.connect()

            headers = self._get_auth_headers()
            auth = self._get_auth()

            async with self.session.get(
                f"{self.server_url}/view",
                params={"filename": filename, "type": file_type},
                headers=headers,
                auth=auth
            ) as response:
                if response.status == 200:
                    with open(output_path, 'wb') as f:
                        f.write(await response.read())
                    Logger.info(f"文件下载成功: {output_path}")
                    return True
                else:
                    Logger.error(f"文件下载失败: {response.status}")
                    return False
        except Exception as e:
            Logger.error(f"下载文件异常: {str(e)}")
            return False

    async def get_server_info(self) -> Dict[str, Any]:
        """
        获取服务器信息

        Returns:
            Dict[str, Any]: 服务器信息
        """
        try:
            if not self.session:
                await self.connect()

            headers = self._get_auth_headers()
            auth = self._get_auth()

            async with self.session.get(
                f"{self.server_url}/system_stats",
                headers=headers,
                auth=auth
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {}
        except Exception as e:
            Logger.error(f"获取服务器信息异常: {str(e)}")
            return {}


class ComfyUIModule:
    """ComfyUI 模块"""

    def __init__(self, server_url: Optional[str] = None):
        """
        初始化 ComfyUI 模块

        Args:
            server_url: ComfyUI 服务器地址（默认值，实际使用时以入参为准）
        """
        from config import config
        self.default_server_url = server_url or getattr(config, 'COMFYUI_SERVER_URL', 'http://127.0.0.1:8188')
        self._client: Optional[ComfyUIClient] = None

    async def get_client(
        self,
        server_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> ComfyUIClient:
        """
        获取 ComfyUI 客户端实例

        Args:
            server_url: ComfyUI 服务器地址
            auth_token: 认证 Token
            username: 用户名
            password: 密码

        Returns:
            ComfyUIClient: 客户端实例
        """
        url = server_url or self.default_server_url

        # 如果客户端已存在且配置相同，则复用
        if self._client is not None:
            if (self._client.server_url == url and
                self._client.auth_token == auth_token and
                self._client.username == username and
                self._client.password == password):
                return self._client

        self._client = ComfyUIClient(
            server_url=url,
            auth_token=auth_token,
            username=username,
            password=password
        )
        return self._client

    async def test_connection(
        self,
        server_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        测试连接

        Args:
            server_url: ComfyUI 服务器地址
            auth_token: 认证 Token
            username: 用户名
            password: 密码

        Returns:
            Dict[str, Any]: 测试结果
        """
        try:
            url = server_url or self.default_server_url
            client = await self.get_client(url, auth_token, username, password)
            connected = await client.connect()

            if connected:
                server_info = await client.get_server_info()
                return {
                    "success": True,
                    "server_url": url,
                    "server_info": server_info,
                    "message": "连接成功"
                }
            else:
                return {
                    "success": False,
                    "server_url": url,
                    "error": "无法连接到 ComfyUI 服务器"
                }
        except Exception as e:
            return {
                "success": False,
                "server_url": server_url or self.default_server_url,
                "error": str(e)
            }

    async def get_available_nodes(
        self,
        server_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取可用节点列表

        Args:
            server_url: ComfyUI 服务器地址
            auth_token: 认证 Token
            username: 用户名
            password: 密码

        Returns:
            Dict[str, Any]: 节点信息
        """
        try:
            url = server_url or self.default_server_url
            client = await self.get_client(url, auth_token, username, password)
            object_info = await client.get_object_info()
            return {
                "success": True,
                "nodes": object_info,
                "count": len(object_info)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def execute_workflow_from_json(
        self,
        workflow_json: str,
        server_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        upload_files: Optional[Dict[str, str]] = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        从 JSON 字符串执行工作流

        Args:
            workflow_json: 工作流 JSON 字符串
            server_url: ComfyUI 服务器地址
            auth_token: 认证 Token
            username: 用户名
            password: 密码
            upload_files: 要上传的文件 {filename: filepath}，支持多种格式
            timeout: 超时时间（秒），默认 300 秒

        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            workflow = json.loads(workflow_json)
            url = server_url or self.default_server_url
            client = await self.get_client(url, auth_token, username, password)
            result = await client.execute_workflow(workflow, upload_files, timeout)

            return {
                "success": result.success,
                "prompt_id": result.prompt_id,
                "output_images": result.output_images,
                "output_audio": result.output_audio,
                "output_videos": result.output_videos,
                "output_files": result.output_files,
                "error": result.error,
                "message": result.message
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"工作流 JSON 解析失败: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def execute_workflow_from_file(
        self,
        workflow_path: str,
        server_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        upload_files: Optional[Dict[str, str]] = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        从文件执行工作流

        Args:
            workflow_path: 工作流文件路径
            server_url: ComfyUI 服务器地址
            auth_token: 认证 Token
            username: 用户名
            password: 密码
            upload_files: 要上传的文件 {filename: filepath}，支持多种格式
            timeout: 超时时间（秒），默认 300 秒

        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow_json = f.read()

            return await self.execute_workflow_from_json(
                workflow_json,
                server_url,
                auth_token,
                username,
                password,
                upload_files,
                timeout
            )
        except FileNotFoundError:
            return {
                "success": False,
                "error": f"工作流文件不存在: {workflow_path}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模块信息

        Returns:
            Dict[str, Any]: 模块信息
        """
        return {
            "name": "ComfyUI Module",
            "version": "1.0.0",
            "default_server_url": self.default_server_url,
            "description": "ComfyUI 集成模块，支持工作流执行和多种媒体文件生成"
        }

    def list_workflows(self) -> Dict[str, Any]:
        """
        列出 workflows 目录中的所有工作流文件

        Returns:
            Dict[str, Any]: 工作流文件列表
        """
        try:
            if not WORKFLOWS_DIR.exists():
                return {
                    "success": False,
                    "error": f"workflows 目录不存在: {WORKFLOWS_DIR}"
                }

            workflow_files = []
            for file_path in WORKFLOWS_DIR.glob("*.json"):
                workflow_files.append({
                    "filename": file_path.name,
                    "path": str(file_path),
                    "size": file_path.stat().st_size
                })

            return {
                "success": True,
                "workflows": workflow_files,
                "count": len(workflow_files),
                "workflows_dir": str(WORKFLOWS_DIR)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def load_workflow_file(self, workflow_name: str) -> Dict[str, Any]:
        """
        从 workflows 目录加载工作流文件

        Args:
            workflow_name: 工作流文件名（如 "example_text_to_image.json"）

        Returns:
            Dict[str, Any]: 工作流内容
        """
        try:
            workflow_path = WORKFLOWS_DIR / workflow_name

            if not workflow_path.exists():
                return {
                    "success": False,
                    "error": f"工作流文件不存在: {workflow_name}"
                }

            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow = json.load(f)

            return {
                "success": True,
                "workflow": workflow,
                "workflow_name": workflow_name,
                "workflow_path": str(workflow_path)
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"工作流 JSON 解析失败: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _replace_parameters(
        self,
        workflow: Dict[str, Any],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        替换工作流中的参数占位符

        支持的占位符格式：
        - {{param_name}}: 字符串、数字、布尔值
        - {{nested.param}}: 嵌套参数

        Args:
            workflow: 工作流字典
            params: 参数字典

        Returns:
            Dict[str, Any]: 替换后的工作流
        """
        import re

        def replace_in_value(value):
            """递归替换值中的参数"""
            if isinstance(value, str):
                # 匹配 {{param}} 格式的占位符
                pattern = r'\{\{(\w+(?:\.\w+)*)\}\}'
                
                def replace_match(match):
                    param_path = match.group(1)
                    # 支持点号表示法，如 "model.name"
                    keys = param_path.split('.')
                    param_value = params
                    
                    try:
                        for key in keys:
                            param_value = param_value[key]
                        # 将替换值转换为字符串
                        return str(param_value)
                    except (KeyError, TypeError):
                        # 如果参数不存在，保留原始占位符
                        return match.group(0)
                
                return re.sub(pattern, replace_match, value)
            elif isinstance(value, dict):
                return {k: replace_in_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [replace_in_value(item) for item in value]
            else:
                return value

        # 深拷贝工作流以避免修改原始数据
        import copy
        workflow_copy = copy.deepcopy(workflow)
        
        # 递归替换所有值中的参数
        return replace_in_value(workflow_copy)

    async def execute_workflow_from_template(
        self,
        workflow_name: str,
        server_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        upload_files: Optional[Dict[str, str]] = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        从 workflows 目录中的模板执行工作流，支持参数替换

        Args:
            workflow_name: 工作流文件名（如 "example_text_to_image.json"）
            server_url: ComfyUI 服务器地址
            auth_token: 认证 Token
            username: 用户名
            password: 密码
            params: 参数字典，用于替换工作流中的占位符
            upload_files: 要上传的文件 {filename: filepath}，支持多种格式
            timeout: 超时时间（秒），默认 300 秒

        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            # 加载工作流文件
            load_result = self.load_workflow_file(workflow_name)
            if not load_result["success"]:
                return {
                    "success": False,
                    "error": load_result["error"]
                }

            workflow = load_result["workflow"]

            # 如果提供了参数，进行参数替换
            if params:
                workflow = self._replace_parameters(workflow, params)
                Logger.info(f"已替换工作流 {workflow_name} 中的参数: {list(params.keys())}")

            # 将工作流转换为 JSON 字符串
            workflow_json = json.dumps(workflow, ensure_ascii=False)

            # 执行工作流
            return await self.execute_workflow_from_json(
                workflow_json,
                server_url,
                auth_token,
                username,
                password,
                upload_files,
                timeout
            )
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def upload_file(
        self,
        filename: str,
        filepath: str,
        server_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        overwrite: bool = True
    ) -> Dict[str, Any]:
        """
        上传文件到 ComfyUI 服务器

        Args:
            filename: 文件名
            filepath: 本地文件路径
            server_url: ComfyUI 服务器地址
            auth_token: 认证 Token
            username: 用户名
            password: 密码
            overwrite: 是否覆盖已存在的文件

        Returns:
            Dict[str, Any]: 上传结果
        """
        try:
            url = server_url or self.default_server_url
            client = await self.get_client(url, auth_token, username, password)
            success = await client.upload_file(filename, filepath, overwrite)

            if success:
                return {
                    "success": True,
                    "filename": filename,
                    "filepath": filepath,
                    "message": f"文件上传成功: {filename}"
                }
            else:
                return {
                    "success": False,
                    "filename": filename,
                    "error": "文件上传失败"
                }
        except Exception as e:
            return {
                "success": False,
                "filename": filename,
                "error": str(e)
            }


# 创建全局实例
comfyui_module = ComfyUIModule()