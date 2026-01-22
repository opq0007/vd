"""
通用HTTP集成UI组件

提供对外部HTTP接口进行集成的界面，参考n8n的HTTP请求节点设计。
"""

import gradio as gr
import json
from typing import Optional, Dict, Any

from modules.http_integration_module import http_integration_module
from utils.logger import Logger


def parse_json_text(text: str) -> Optional[Dict[str, Any]]:
    """
    解析JSON文本

    Args:
        text: JSON文本

    Returns:
        Optional[Dict[str, Any]]: 解析后的字典，失败返回None
    """
    if not text or not text.strip():
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        Logger.error(f"JSON解析失败: {e}")
        return None


def parse_form_data_text(text: str) -> Optional[Dict[str, Any]]:
        """
        解析表单数据文本（支持 key=value 格式）

        Args:
            text: 表单数据文本

        Returns:
            Optional[Dict[str, Any]]: 解析后的字典
        """
        if not text or not text.strip():
            return None

        try:
            # 尝试JSON格式
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试key=value格式
            result = {}
            for line in text.strip().split('\n'):
                line = line.strip()
                if line and '=' in line:
                    key, value = line.split('=', 1)
                    result[key.strip()] = value.strip()
            return result if result else None


def parse_files_text(text: str) -> Optional[Dict[str, str]]:
        """
        解析文件上传配置文本

        Args:
            text: 文件配置文本（格式：field_name=file_path）

        Returns:
            Optional[Dict[str, str]]: 解析后的字典 {field_name: file_path}
        """
        if not text or not text.strip():
            return None

        try:
            # 尝试JSON格式
            data = json.loads(text)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except json.JSONDecodeError:
            pass

        # 尝试field_name=file_path格式
        result = {}
        for line in text.strip().split('\n'):
            line = line.strip()
            if line and '=' in line:
                field_name, file_path = line.split('=', 1)
                result[field_name.strip()] = file_path.strip()
        return result if result else None

def parse_headers_text(text: str) -> Optional[Dict[str, str]]:
    """
    解析请求头文本

    Args:
        text: 请求头文本

    Returns:
        Optional[Dict[str, str]]: 解析后的字典
    """
    if not text or not text.strip():
        return None

    try:
        # 尝试JSON格式
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试key:value格式
        result = {}
        for line in text.strip().split('\n'):
            line = line.strip()
            if line and ':' in line:
                key, value = line.split(':', 1)
                result[key.strip()] = value.strip()
        return result if result else None


def format_result(result: Dict[str, Any]) -> str:
    """
    格式化请求结果

    Args:
        result: 请求结果

    Returns:
        str: 格式化后的结果文本
    """
    if not result:
        return "无结果"

    output = []

    # 状态信息
    status_icon = "✅" if result.get("success", False) else "❌"
    output.append(f"{status_icon} 请求状态: {result.get('status_code', 'N/A')} {result.get('status_text', '')}")
    output.append("")

    # 错误信息
    if not result.get("success", False) and result.get("error"):
        output.append(f"错误信息: {result['error']}")
        output.append("")

    # 响应头
    if result.get("response_headers"):
        output.append("响应头:")
        for key, value in result["response_headers"].items():
            output.append(f"  {key}: {value}")
        output.append("")

    # 响应体
    if result.get("is_binary", False):
        output.append(f"响应内容: {result.get('response_body', 'N/A')}")
        if result.get("saved_file"):
            output.append(f"保存位置: {result['saved_file']}")
            output.append(f"文件大小: {result.get('file_size', 0)} 字节")
            output.append(f"内容类型: {result.get('content_type', 'N/A')}")
    else:
        output.append("响应内容:")
        response_body = result.get("response_body", "")
        if response_body:
            # 尝试格式化JSON
            try:
                json_data = json.loads(response_body)
                output.append(json.dumps(json_data, indent=2, ensure_ascii=False))
            except:
                output.append(response_body)
        else:
            output.append("(空)")

    return "\n".join(output)


async def send_http_request(
        method: str,
        url: str,
        headers_text: str,
        params_text: str,
        body_format: str,
        body_data_text: str,
        body_json_text: str,
        form_data_text: str,
        files_text: str,
        auth_type: str,
        auth_token: str,
        auth_username: str,
        auth_password: str,
        auth_key_name: str,
        auth_key_value: str,
        auth_custom_header: str,
        timeout: float,
        save_binary: bool,
        save_filename: str,
        progress=gr.Progress()
) -> str:
        """
        发送HTTP请求

        Args:
            method: HTTP方法
            url: 请求URL
            headers_text: 请求头文本
            params_text: 查询参数文本
            body_format: 请求体格式 (none/data/json/form/files)
            body_data_text: 原始数据文本
            body_json_text: JSON数据文本
            form_data_text: 表单数据文本
            files_text: 文件上传配置文本
            auth_type: 认证类型
            auth_token: Bearer Token
            auth_username: Basic认证用户名
            auth_password: Basic认证密码
            auth_key_name: API Key名称
            auth_key_value: API Key值
            auth_custom_header: 自定义认证头
            timeout: 超时时间
            save_binary: 是否保存二进制流
            save_filename: 保存文件名
            progress: 进度条

        Returns:
            str: 格式化的结果
        """
        try:
            progress(0.1, desc="准备请求...")

            # 解析请求头
            headers = parse_headers_text(headers_text)

            # 解析查询参数
            params = parse_json_text(params_text)

            # 准备请求体
            body_data = None
            body_json = None
            form_data = None
            files = None

            if body_format == "data":
                body_data = body_data_text if body_data_text.strip() else None
            elif body_format == "json":
                body_json = parse_json_text(body_json_text)
            elif body_format == "form":
                form_data = parse_form_data_text(form_data_text)
            elif body_format == "files":
                form_data = parse_form_data_text(form_data_text)
                files = parse_files_text(files_text)

            # 准备认证配置
            auth_config = None
            if auth_type and auth_type != "none":
                auth_config = {"type": auth_type}
                if auth_type == "bearer":
                    auth_config["token"] = auth_token
                elif auth_type == "basic":
                    auth_config["username"] = auth_username
                    auth_config["password"] = auth_password
                elif auth_type == "api_key":
                    auth_config["key_name"] = auth_key_name or "X-API-Key"
                    auth_config["key_value"] = auth_key_value
                elif auth_type == "custom":
                    auth_config["header"] = auth_custom_header

            progress(0.3, desc="发送请求...")

            # 发送请求
            if save_binary:
                result = await http_integration_module.send_request_and_save(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    body_data=body_data,
                    body_json=body_json,
                    form_data=form_data,
                    auth_config=auth_config,
                    timeout=timeout,
                    save_filename=save_filename if save_filename.strip() else None,
                    files=files
                )
            else:
                result = await http_integration_module.send_request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    body_data=body_data,
                    body_json=body_json,
                    form_data=form_data,
                    auth_config=auth_config,
                    timeout=timeout,
                    files=files
                )

            progress(1.0, desc="完成！")

            # 格式化结果
            return format_result(result)

        except Exception as e:
            Logger.error(f"发送HTTP请求失败: {str(e)}")
            return f"❌ 请求失败: {str(e)}"


def create_http_integration_interface() -> gr.Blocks:
    """
    创建通用HTTP集成界面

    Returns:
        gr.Blocks: Gradio界面块
    """
    with gr.Blocks() as http_integration_interface:
        gr.Markdown("## 🌐 通用HTTP集成")
        gr.Markdown("对外部HTTP接口进行集成，支持多种认证方式和请求格式")

        with gr.Row():
            # 左侧：请求配置
            with gr.Column(scale=1):
                gr.Markdown("### 📝 请求配置")

                # HTTP方法
                method_dropdown = gr.Dropdown(
                    choices=["GET", "POST", "PUT", "DELETE", "PATCH"],
                    value="GET",
                    label="HTTP方法",
                    info="选择HTTP请求方法"
                )

                # 请求URL
                url_input = gr.Textbox(
                    label="请求URL",
                    placeholder="https://api.example.com/endpoint",
                    info="完整的请求URL"
                )

                # 超时时间
                timeout_slider = gr.Slider(
                    minimum=5,
                    maximum=600,
                    value=30,
                    step=5,
                    label="超时时间（秒）",
                    info="请求超时时间"
                )

            # 右侧：认证配置
            with gr.Column(scale=1):
                gr.Markdown("### 🔐 认证配置")

                # 认证类型
                auth_type_dropdown = gr.Dropdown(
                    choices=["none", "bearer", "basic", "api_key", "custom"],
                    value="none",
                    label="认证类型",
                    info="选择认证方式"
                )

                # Bearer Token
                auth_token_input = gr.Textbox(
                    label="Bearer Token",
                    placeholder="your-bearer-token",
                    visible=False,
                    type="password"
                )

                # Basic认证
                with gr.Row(visible=False) as auth_basic_box:
                    auth_username_input = gr.Textbox(
                        label="用户名",
                        placeholder="username"
                    )
                    auth_password_input = gr.Textbox(
                        label="密码",
                        placeholder="password",
                        type="password"
                    )

                # API Key
                with gr.Row(visible=False) as auth_api_key_box:
                    auth_key_name_input = gr.Textbox(
                        label="Key名称",
                        placeholder="X-API-Key",
                        value="X-API-Key"
                    )
                    auth_key_value_input = gr.Textbox(
                        label="Key值",
                        placeholder="your-api-key"
                    )

                # 自定义认证头
                auth_custom_header_input = gr.Textbox(
                    label="自定义认证头",
                    placeholder="Authorization: Custom value",
                    visible=False
                )

        # 请求头和查询参数
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📋 请求头")

                headers_textarea = gr.Textbox(
                    label="请求头 (JSON 或 key: value 格式)",
                    placeholder='{\n  "Content-Type": "application/json",\n  "Accept": "application/json"\n}',
                    lines=5,
                    info='支持JSON格式或 key: value 格式（每行一个）'
                )

            with gr.Column(scale=1):
                gr.Markdown("### 🔍 查询参数")

                params_textarea = gr.Textbox(
                    label="查询参数 (JSON 格式)",
                    placeholder='{\n  "param1": "value1",\n  "param2": "value2"\n}',
                    lines=5,
                    info="URL查询参数，JSON格式"
                )

        # 请求体配置
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📦 请求体")

                # 请求体格式
                body_format_dropdown = gr.Dropdown(
                    choices=["none", "data", "json", "form", "files"],
                    value="none",
                    label="请求体格式",
                    info="选择请求体的格式"
                )

                # 原始数据
                body_data_textarea = gr.Textbox(
                    label="原始数据",
                    placeholder="输入原始数据字符串",
                    lines=5,
                    visible=False
                )

                # JSON数据
                body_json_textarea = gr.Textbox(
                    label="JSON数据",
                    placeholder='{\n  "key1": "value1",\n  "key2": "value2"\n}',
                    lines=5,
                    visible=False
                )

                # 表单数据
                form_data_textarea = gr.Textbox(
                    label="表单数据 (JSON 或 key=value 格式)",
                    placeholder='key1=value1\nkey2=value2',
                    lines=5,
                    visible=False,
                    info='支持JSON格式或 key=value 格式（每行一个）'
                )

                # 文件上传配置
                files_textarea = gr.Textbox(
                    label="文件上传配置 (field_name=file_path)",
                    placeholder='file=output/video.mp4\ndata=uploads/data.json\nimage=output/image.png',
                    lines=5,
                    visible=False,
                    info='格式：field_name=file_path（每行一个），支持JSON格式或 field_name=file_path 格式。文件路径为服务器上的绝对或相对路径。'
                )

        # 二进制流保存配置
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 💾 二进制流保存")

                save_binary_checkbox = gr.Checkbox(
                    label="保存二进制流到本地",
                    value=False,
                    info="如果响应是二进制流，自动保存到output目录"
                )

                save_filename_input = gr.Textbox(
                    label="保存文件名（不含扩展名）",
                    placeholder="http_response",
                    info="留空则自动生成文件名"
                )

        # 发送按钮
        send_btn = gr.Button(
            "🚀 发送请求",
            variant="primary",
            size="lg"
        )

        # 结果显示
        gr.Markdown("### 📊 请求结果")

        result_output = gr.Textbox(
            label="响应结果",
            lines=20,
            interactive=False,
            placeholder="请求结果将显示在这里..."
        )

        # 事件绑定：认证类型切换
        def update_auth_visibility(auth_type):
            """根据认证类型更新可见性"""
            return {
                auth_token_input: gr.update(visible=(auth_type == "bearer")),
                auth_basic_box: gr.update(visible=(auth_type == "basic")),
                auth_api_key_box: gr.update(visible=(auth_type == "api_key")),
                auth_custom_header_input: gr.update(visible=(auth_type == "custom"))
            }

        auth_type_dropdown.change(
            fn=update_auth_visibility,
            inputs=[auth_type_dropdown],
            outputs=[
                auth_token_input,
                auth_basic_box,
                auth_api_key_box,
                auth_custom_header_input
            ]
        )

        # 事件绑定：请求体格式切换
        def update_body_format_visibility(body_format):
            """根据请求体格式更新可见性"""
            return {
                body_data_textarea: gr.update(visible=(body_format == "data")),
                body_json_textarea: gr.update(visible=(body_format == "json")),
                form_data_textarea: gr.update(visible=(body_format in ["form", "files"])),
                files_textarea: gr.update(visible=(body_format == "files"))
            }

        body_format_dropdown.change(
            fn=update_body_format_visibility,
            inputs=[body_format_dropdown],
            outputs=[
                body_data_textarea,
                body_json_textarea,
                form_data_textarea,
                files_textarea
            ]
        )

        # 事件绑定：发送请求
        send_btn.click(
            fn=send_http_request,
            inputs=[
                method_dropdown,
                url_input,
                headers_textarea,
                params_textarea,
                body_format_dropdown,
                body_data_textarea,
                body_json_textarea,
                form_data_textarea,
                files_textarea,
                auth_type_dropdown,
                auth_token_input,
                auth_username_input,
                auth_password_input,
                auth_key_name_input,
                auth_key_value_input,
                auth_custom_header_input,
                timeout_slider,
                save_binary_checkbox,
                save_filename_input
            ],
            outputs=result_output
        )

        # 使用说明
        gr.Markdown("---")
        gr.Markdown("### 📖 使用说明")
        gr.Markdown("""
#### 1. 基本配置
- **HTTP方法**：选择请求方法（GET、POST、PUT、DELETE、PATCH）
- **请求URL**：输入完整的API端点URL
- **超时时间**：设置请求超时时间（秒）

#### 2. 认证配置
支持多种认证方式：
- **无认证**：不使用任何认证
- **Bearer Token**：使用Bearer Token认证
  - 输入Token值（例如：`your-bearer-token`）
- **Basic认证**：使用用户名和密码认证
  - 输入用户名和密码
- **API Key**：使用API Key认证
  - 设置Key名称（默认：`X-API-Key`）
  - 输入Key值
- **自定义认证头**：使用自定义的认证头
  - 输入完整的认证头（例如：`Authorization: Custom value`）

#### 3. 请求头配置
支持两种格式：
- **JSON格式**：
  ```json
  {
    "Content-Type": "application/json",
    "Accept": "application/json"
  }
  ```
- **key: value格式**（每行一个）：
  ```
  Content-Type: application/json
  Accept: application/json
  ```

#### 4. 查询参数配置
使用JSON格式配置URL查询参数：
```json
{
  "param1": "value1",
  "param2": "value2"
}
```

#### 5. 请求体配置
支持多种请求体格式：
- **无请求体**：不发送请求体（适用于GET、DELETE等）
- **原始数据**：发送原始字符串数据
- **JSON数据**：发送JSON格式数据
  ```json
  {
    "key1": "value1",
    "key2": "value2"
  }
  ```
- **表单数据**：发送表单格式数据
  - 支持JSON格式
  - 支持`key=value`格式（每行一个）

#### 6. 二进制流保存
如果响应是二进制流（如图片、视频、音频、PDF等），可以自动保存到本地：
- 勾选"保存二进制流到本地"
- 输入保存文件名（不含扩展名）
- 系统会自动根据Content-Type或URL推断文件扩展名
- 文件保存在`output/`目录下

#### 7. 常见示例

**示例1：GET请求（带查询参数）**
```
方法: GET
URL: https://api.example.com/users
查询参数:
{
  "page": 1,
  "limit": 10
}
```

**示例2：POST请求（JSON数据）**
```
方法: POST
URL: https://api.example.com/users
请求体格式: JSON
JSON数据:
{
  "name": "张三",
  "email": "zhangsan@example.com"
}
```

**示例3：POST请求（表单数据）**
```
方法: POST
URL: https://api.example.com/upload
请求体格式: 表单数据
表单数据:
file=example.jpg
title=测试图片
```

**示例4：POST请求（文件上传）**
```
方法: POST
URL: https://api.example.com/upload
请求体格式: 文件上传
文件上传配置:
file=output/video.mp4
data=uploads/data.json
```

**示例5：带Bearer Token的请求**
```
认证类型: Bearer Token
Bearer Token: your-api-token-here
```

**示例5：下载图片**
```
方法: GET
URL: https://example.com/image.png
保存二进制流到本地: ✓
保存文件名: downloaded_image
```

**示例6：上传多个文件**
```
方法: POST
URL: https://api.example.com/batch-upload
请求体格式: 文件上传
文件上传配置:
file1=output/video1.mp4
file2=output/video2.mp4
metadata=uploads/metadata.json
```

#### 注意事项
- 确保URL格式正确，必须包含协议（http://或https://）
- JSON格式必须符合标准，注意引号和逗号的使用
- 认证信息会被安全处理，不会在日志中明文显示
- 下载大文件时请适当增加超时时间
- 二进制流文件会自动根据Content-Type或URL推断扩展名
- **文件上传功能**：
  - 文件路径必须是服务器上存在的文件路径（绝对路径或相对于项目根目录的路径）
  - 支持同时上传多个文件
  - 支持同时上传文件和表单数据
  - 文件上传使用 multipart/form-data 格式
  - 文件会自动根据文件扩展名推断 MIME 类型
        """)

    return http_integration_interface