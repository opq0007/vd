"""
通用HTTP集成模块

提供对外部HTTP接口的集成功能，支持多种认证方式和请求格式。
"""

import httpx
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import mimetypes

from utils.logger import Logger
from utils.file_utils import FileUtils


class HTTPIntegrationModule:
    """通用HTTP集成模块"""

    def __init__(self):
        """初始化HTTP集成模块"""
        self.timeout = 300.0  # 默认超时时间（秒）

    async def send_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        body_data: Optional[str] = None,
        body_json: Optional[Dict[str, Any]] = None,
        form_data: Optional[Dict[str, Any]] = None,
        auth_config: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        files: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        发送HTTP请求

        Args:
            method: HTTP方法 (GET, POST, PUT, DELETE, PATCH)
            url: 请求URL
            headers: 自定义请求头
            params: URL查询参数
            body_data: 请求体（原始字符串）
            body_json: 请求体（JSON格式）
            form_data: 请求体（表单格式）
            auth_config: 认证配置
            timeout: 超时时间（秒）
            files: 文件上传（multipart/form-data），格式：{"field_name": "file_path"}

        Returns:
            Dict[str, Any]: 请求结果
        """
        try:
            # 准备请求头
            request_headers = {}
            if headers:
                request_headers.update(headers)

            # 处理认证配置
            if auth_config:
                auth_type = auth_config.get("type", "none")
                if auth_type == "bearer":
                    token = auth_config.get("token", "")
                    request_headers["Authorization"] = f"Bearer {token}"
                elif auth_type == "basic":
                    username = auth_config.get("username", "")
                    password = auth_config.get("password", "")
                    request_headers["Authorization"] = f"Basic {username}:{password}"
                elif auth_type == "api_key":
                    key_name = auth_config.get("key_name", "X-API-Key")
                    key_value = auth_config.get("key_value", "")
                    request_headers[key_name] = key_value
                elif auth_type == "custom":
                    custom_header = auth_config.get("header", "")
                    request_headers["Authorization"] = custom_header

            # 准备请求内容
            content = None
            json_data = None
            data = None
            files_data = None

            # 处理文件上传
            if files:
                files_data = {}
                for field_name, file_path in files.items():
                    if not file_path:
                        continue
                    
                    file_path_obj = Path(file_path)
                    if not file_path_obj.exists():
                        Logger.warning(f"文件不存在: {file_path}")
                        continue
                    
                    # 使用文件名作为文件名
                    filename = file_path_obj.name
                    # 根据 MIME 类型猜测
                    mime_type, _ = mimetypes.guess_type(file_path)
                    if mime_type is None:
                        mime_type = "application/octet-stream"
                    
                    files_data[field_name] = (filename, open(file_path, "rb"), mime_type)
                    Logger.info(f"准备上传文件: {field_name} -> {file_path} ({mime_type})")
            
            if body_json:
                request_headers["Content-Type"] = "application/json"
                json_data = body_json
            elif form_data and not files_data:
                data = form_data
            elif body_data and not files_data:
                content = body_data

            # 发送请求（禁用自动重定向，手动处理）
            async with httpx.AsyncClient(
                timeout=timeout or self.timeout,
                follow_redirects=False  # 禁用自动重定向
            ) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    params=params,
                    content=content,
                    json=json_data,
                    data=data,
                    files=files_data
                )

                # 关闭打开的文件
                if files_data:
                    for field_name, file_tuple in files_data.items():
                        if len(file_tuple) >= 2:
                            file_obj = file_tuple[1]
                            if hasattr(file_obj, 'close'):
                                file_obj.close()

                # 检查是否是重定向响应（301, 302, 303, 307, 308）
                redirect_codes = [301, 302, 303, 307, 308]
                if response.status_code in redirect_codes:
                    # 获取重定向URL
                    redirect_url = response.headers.get("location")
                    if redirect_url:
                        Logger.info(f"检测到重定向 {response.status_code}，跟随到: {redirect_url}")

                        # 处理相对URL
                        if redirect_url.startswith("/"):
                            from urllib.parse import urlparse
                            parsed_url = urlparse(url)
                            redirect_url = f"{parsed_url.scheme}://{parsed_url.netloc}{redirect_url}"

                        # 使用GET方法访问重定向URL（大多数重定向都使用GET）
                        # 保留认证头
                        redirect_response = await client.get(
                            redirect_url,
                            headers=request_headers,
                            follow_redirects=False
                        )

                        # 如果重定向URL再次返回重定向，继续跟随（最多5次）
                        max_redirects = 5
                        redirect_count = 0
                        while redirect_response.status_code in redirect_codes and redirect_count < max_redirects:
                            redirect_count += 1
                            next_redirect_url = redirect_response.headers.get("location")
                            if not next_redirect_url:
                                break

                            # 处理相对URL
                            if next_redirect_url.startswith("/"):
                                from urllib.parse import urlparse
                                parsed_url = urlparse(redirect_url)
                                next_redirect_url = f"{parsed_url.scheme}://{parsed_url.netloc}{next_redirect_url}"

                            Logger.info(f"第{redirect_count + 1}次重定向，跟随到: {next_redirect_url}")
                            redirect_response = await client.get(
                                next_redirect_url,
                                headers=request_headers,
                                follow_redirects=False
                            )
                            redirect_url = next_redirect_url

                        # 使用最终的响应
                        response = redirect_response
                        Logger.info(f"重定向完成，最终状态码: {response.status_code}")

                # 处理响应
                result = {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "status_text": response.reason_phrase,
                    "headers": dict(response.headers),
                    "response_body": None,
                    "response_headers": dict(response.headers),
                    "is_binary": False,
                    "saved_file": None
                }

                # 判断响应内容类型
                content_type = response.headers.get("content-type", "").lower()

                # 检查是否为二进制流
                if "application/json" not in content_type and "text/" not in content_type:
                    # 二进制流
                    result["is_binary"] = True
                    result["response_body"] = f"<二进制流，大小: {len(response.content)} 字节>"
                else:
                    # 文本响应
                    try:
                        result["response_body"] = response.text
                    except:
                        result["response_body"] = str(response.content)

                return result

        except httpx.TimeoutException:
            Logger.error(f"HTTP请求超时: {url}")
            return {
                "success": False,
                "error": "请求超时",
                "status_code": None,
                "status_text": "Timeout",
                "response_body": None
            }
        except httpx.HTTPError as e:
            Logger.error(f"HTTP请求失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "status_code": None,
                "status_text": "HTTP Error",
                "response_body": None
            }
        except Exception as e:
            Logger.error(f"HTTP请求异常: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "status_code": None,
                "status_text": "Error",
                "response_body": None
            }

    async def send_request_and_save(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        body_data: Optional[str] = None,
        body_json: Optional[Dict[str, Any]] = None,
        form_data: Optional[Dict[str, Any]] = None,
        auth_config: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        save_filename: Optional[str] = None,
        output_dir: Optional[Path] = None,
        files: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        发送HTTP请求并保存二进制响应到本地

        Args:
            method: HTTP方法
            url: 请求URL
            headers: 自定义请求头
            params: URL查询参数
            body_data: 请求体（原始字符串）
            body_json: 请求体（JSON格式）
            form_data: 请求体（表单格式）
            auth_config: 认证配置
            timeout: 超时时间（秒）
            save_filename: 保存文件名（不含扩展名）
            output_dir: 输出目录
            files: 文件上传（multipart/form-data），格式：{"field_name": "file_path"}

        Returns:
            Dict[str, Any]: 请求结果
        """
        try:
            # 准备请求头
            request_headers = {}
            if headers:
                request_headers.update(headers)

            # 处理认证配置
            if auth_config:
                auth_type = auth_config.get("type", "none")
                if auth_type == "bearer":
                    token = auth_config.get("token", "")
                    request_headers["Authorization"] = f"Bearer {token}"
                elif auth_type == "basic":
                    username = auth_config.get("username", "")
                    password = auth_config.get("password", "")
                    request_headers["Authorization"] = f"Basic {username}:{password}"
                elif auth_type == "api_key":
                    key_name = auth_config.get("key_name", "X-API-Key")
                    key_value = auth_config.get("key_value", "")
                    request_headers[key_name] = key_value
                elif auth_type == "custom":
                    custom_header = auth_config.get("header", "")
                    request_headers["Authorization"] = custom_header

            # 准备请求内容
            content = None
            json_data = None
            data = None
            files_data = None

            # 处理文件上传
            if files:
                files_data = {}
                for field_name, file_path in files.items():
                    if not file_path:
                        continue
                    
                    file_path_obj = Path(file_path)
                    if not file_path_obj.exists():
                        Logger.warning(f"文件不存在: {file_path}")
                        continue
                    
                    # 使用文件名作为文件名
                    filename = file_path_obj.name
                    # 根据 MIME 类型猜测
                    mime_type, _ = mimetypes.guess_type(file_path)
                    if mime_type is None:
                        mime_type = "application/octet-stream"
                    
                    files_data[field_name] = (filename, open(file_path, "rb"), mime_type)
                    Logger.info(f"准备上传文件: {field_name} -> {file_path} ({mime_type})")
            
            if body_json:
                request_headers["Content-Type"] = "application/json"
                json_data = body_json
            elif form_data and not files_data:
                data = form_data
            elif body_data and not files_data:
                content = body_data

            # 发送请求（禁用自动重定向，手动处理）
            async with httpx.AsyncClient(
                timeout=timeout or self.timeout,
                follow_redirects=False  # 禁用自动重定向
            ) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    params=params,
                    content=content,
                    json=json_data,
                    data=data,
                    files=files_data
                )

                # 关闭打开的文件
                if files_data:
                    for field_name, file_tuple in files_data.items():
                        if len(file_tuple) >= 2:
                            file_obj = file_tuple[1]
                            if hasattr(file_obj, 'close'):
                                file_obj.close()

                # 检查是否是重定向响应（301, 302, 303, 307, 308）
                redirect_codes = [301, 302, 303, 307, 308]
                if response.status_code in redirect_codes:
                    # 获取重定向URL
                    redirect_url = response.headers.get("location")
                    if redirect_url:
                        Logger.info(f"检测到重定向 {response.status_code}，跟随到: {redirect_url}")

                        # 处理相对URL
                        if redirect_url.startswith("/"):
                            from urllib.parse import urlparse
                            parsed_url = urlparse(url)
                            redirect_url = f"{parsed_url.scheme}://{parsed_url.netloc}{redirect_url}"

                        # 使用GET方法访问重定向URL（大多数重定向都使用GET）
                        # 保留认证头
                        redirect_response = await client.get(
                            redirect_url,
                            headers=request_headers,
                            follow_redirects=False
                        )

                        # 如果重定向URL再次返回重定向，继续跟随（最多5次）
                        max_redirects = 5
                        redirect_count = 0
                        while redirect_response.status_code in redirect_codes and redirect_count < max_redirects:
                            redirect_count += 1
                            next_redirect_url = redirect_response.headers.get("location")
                            if not next_redirect_url:
                                break

                            # 处理相对URL
                            if next_redirect_url.startswith("/"):
                                from urllib.parse import urlparse
                                parsed_url = urlparse(redirect_url)
                                next_redirect_url = f"{parsed_url.scheme}://{parsed_url.netloc}{next_redirect_url}"

                            Logger.info(f"第{redirect_count + 1}次重定向，跟随到: {next_redirect_url}")
                            redirect_response = await client.get(
                                next_redirect_url,
                                headers=request_headers,
                                follow_redirects=False
                            )
                            redirect_url = next_redirect_url

                        # 使用最终的响应
                        response = redirect_response
                        Logger.info(f"重定向完成，最终状态码: {response.status_code}")

                # 获取输出目录
                if output_dir is None:
                    output_dir = FileUtils.get_output_dir()

                # 确定文件扩展名
                content_type = response.headers.get("content-type", "").lower()
                file_extension = self._get_file_extension_from_content_type(content_type, url)

                # 确定文件名
                if not save_filename:
                    save_filename = f"http_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                # 处理文件名：支持带/分隔的路径，兼容带后缀的场景
                save_path = self._resolve_save_path(output_dir, save_filename, file_extension, url, params)

                # 保存文件
                with open(save_path, "wb") as f:
                    f.write(response.content)

                Logger.info(f"HTTP响应已保存到: {save_path} (大小: {len(response.content)} 字节)")

                # 判断响应内容类型
                is_binary = "application/json" not in content_type and "text/" not in content_type

                result = {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "status_text": response.reason_phrase,
                    "headers": dict(response.headers),
                    "response_headers": dict(response.headers),
                    "is_binary": is_binary,
                    "saved_file": str(save_path),
                    "file_size": len(response.content),
                    "content_type": content_type
                }

                # 如果不是二进制流，也返回文本内容
                if not is_binary:
                    try:
                        result["response_body"] = response.text
                    except:
                        result["response_body"] = str(response.content)
                else:
                    result["response_body"] = f"<二进制流已保存，大小: {len(response.content)} 字节>"

                return result

        except httpx.TimeoutException:
            Logger.error(f"HTTP请求超时: {url}")
            return {
                "success": False,
                "error": "请求超时",
                "status_code": None,
                "status_text": "Timeout",
                "response_body": None,
                "saved_file": None
            }
        except httpx.HTTPError as e:
            Logger.error(f"HTTP请求失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "status_code": None,
                "status_text": "HTTP Error",
                "response_body": None,
                "saved_file": None
            }
        except Exception as e:
            Logger.error(f"HTTP请求异常: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "status_code": None,
                "status_text": "Error",
                "response_body": None,
                "saved_file": None
            }

    def _get_file_extension_from_content_type(self, content_type: str, url: str) -> str:
        """
        根据Content-Type或URL推断文件扩展名

        Args:
            content_type: Content-Type头
            url: 请求URL

        Returns:
            str: 文件扩展名（包含点）
        """
        # 常见Content-Type映射
        content_type_map = {
            "application/json": ".json",
            "text/json": ".json",
            "text/plain": ".txt",
            "text/html": ".html",
            "text/xml": ".xml",
            "application/xml": ".xml",
            "application/pdf": ".pdf",
            "application/zip": ".zip",
            "application/x-zip-compressed": ".zip",
            "application/x-rar-compressed": ".rar",
            "application/x-7z-compressed": ".7z",
            "application/x-tar": ".tar",
            "application/x-gtar": ".tar.gz",
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/svg+xml": ".svg",
            "image/bmp": ".bmp",
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "video/x-msvideo": ".avi",
            "video/x-ms-wmv": ".wmv",
            "video/x-flv": ".flv",
            "video/webm": ".webm",
            "audio/mpeg": ".mp3",
            "audio/wav": ".wav",
            "audio/ogg": ".ogg",
            "audio/flac": ".flac",
            "audio/aac": ".aac",
            "audio/m4a": ".m4a",
            "application/octet-stream": ".bin",
        }

        # 尝试从Content-Type推断
        for ct, ext in content_type_map.items():
            if ct in content_type:
                return ext

        # 尝试从URL推断
        if url:
            parsed_url = Path(url.split("?")[0])
            if parsed_url.suffix:
                return parsed_url.suffix

        # 默认返回.bin
        return ".bin"

    def _resolve_save_path(
        self,
        output_dir: Path,
        save_filename: str,
        default_extension: str,
        url: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        解析保存路径，支持子目录和后缀处理

        Args:
            output_dir: 输出根目录
            save_filename: 保存文件名（可能包含路径和后缀）
            default_extension: 默认文件扩展名
            url: 请求URL（用于兜底判断后缀）
            params: 请求参数（可能包含filename参数）

        Returns:
            Path: 完整的保存路径
        """
        # 将/转换为路径分隔符（兼容Windows和Unix）
        save_path = output_dir / save_filename.replace("/", "\\")

        # 检查文件名是否包含后缀
        if save_path.suffix:
            # 文件名已指定后缀，直接使用
            pass
        else:
            # 文件名未指定后缀，使用默认后缀
            save_path = save_path.with_suffix(default_extension)

        # 兜底处理：如果默认后缀是.bin，尝试从其他来源获取更准确的后缀
        if save_path.suffix == ".bin":
            # 1. 尝试从请求参数中的filename获取
            if params and "filename" in params:
                filename = str(params["filename"])
                if "." in filename:
                    save_path = save_path.with_suffix(Path(filename).suffix)
                    Logger.info(f"从请求参数filename获取后缀: {save_path.suffix}")
            # 2. 尝试从URL路径获取
            else:
                url_filename = url.split("/")[-1].split("?")[0]
                if "." in url_filename:
                    save_path = save_path.with_suffix(Path(url_filename).suffix)
                    Logger.info(f"从URL路径获取后缀: {save_path.suffix}")

        # 如果路径包含子目录，确保父目录存在
        if save_path.parent != output_dir:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            Logger.info(f"创建子目录: {save_path.parent}")

        return save_path


# 创建全局实例
http_integration_module = HTTPIntegrationModule()