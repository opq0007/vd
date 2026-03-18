"""
整合版 Whisper 服务 - 统一 FastAPI + Gradio 界面

重构版本，采用模块化设计，遵循高内聚、低耦合原则。
- FastAPI REST API with Bearer token auth
- Gradio UI with modern interface
- faster-whisper for ASR
- 统一认证和服务层
- 支持基础转录和高级字幕生成
- 模块化架构，便于扩展和维护
"""

import os
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

import gradio as gr
import torch

# 导入配置
from config import config

# 导入工具类
from utils import Logger

# 导入功能模块
from modules import (
    whisper_service,
    tts_onnx_module,
    subtitle_module,
    transition_module,
    image_processing_module
)

# 导入 API 路由
from api import register_routes

# 导入 UI 组件
from ui import (
    get_custom_css,
    create_header,
    create_tts_interface,
    create_subtitle_interface,
    create_transition_interface,
    create_video_editor_interface,
    create_video_merge_interface,
    create_image_processing_interface,
    create_batch_processing_interface,
    get_template_manager_ui,
    create_file_persistence_interface,
    create_comfyui_interface,
    create_http_integration_interface,
    create_email_interface
)

# 初始化日志
Logger.info("Starting Whisper Service...")

# 设置torch精度，避免TensorFloat32警告
try:
    torch.set_float32_matmul_precision('high')
except:
    pass

# ----------------------------
# FastAPI 应用初始化
# ----------------------------
app = FastAPI(
    title="整合版 Whisper 语音转文字服务",
    version="3.0.0",
    description="模块化重构版本，支持语音识别、语音合成、字幕生成和视频转场"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
register_routes(app)

# ----------------------------
# 全局异常处理器 - 统一响应格式
# ----------------------------
from fastapi import Request, status
from fastapi.responses import JSONResponse
from api.response_formatter import response_formatter
from fastapi.exceptions import RequestValidationError


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """处理 HTTPException，返回统一的响应格式"""
    return JSONResponse(
        status_code=exc.status_code,
        content=response_formatter.error(
            message=exc.detail,
            error_code=f"HTTP_{exc.status_code}"
        )
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证异常，返回统一的响应格式"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response_formatter.error(
            message=f"请求参数验证失败: {str(exc)}",
            error_code="VALIDATION_ERROR"
        )
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理所有未捕获的异常，返回统一的响应格式"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_formatter.wrap_exception(exc, "服务器内部错误")
    )

# ----------------------------
# Gradio 界面鉴权相关函数
# ----------------------------
def login_user(username: str, password: str) -> tuple:
    """
    用户登录函数

    Args:
        username: 用户名
        password: 密码

    Returns:
        tuple: (success: bool, message: str, session_id: str)
    """
    from api.auth import AuthService
    
    # 验证用户凭据
    if AuthService.verify_user(username, password):
        # 创建会话
        session_id = AuthService.create_gradio_session(username)
        Logger.info(f"User {username} logged in successfully")
        return True, "登录成功！", session_id
    else:
        Logger.warning(f"Failed login attempt for user: {username}")
        return False, "用户名或密码错误！", ""

def verify_session(session_id: str) -> tuple:
    """
    验证会话函数

    Args:
        session_id: 会话ID

    Returns:
        tuple: (valid: bool, username: str)
    """
    from api.auth import AuthService
    
    username = AuthService.verify_gradio_session(session_id)
    if username:
        return True, username
    return False, ""

def logout_user(session_id: str) -> tuple:
    """
    用户登出函数

    Args:
        session_id: 会话ID

    Returns:
        tuple: (success: bool, message: str)
    """
    from api.auth import AuthService
    
    if AuthService.revoke_gradio_session(session_id):
        return True, "已退出登录"
    return False, "会话无效"

def create_login_interface():
    """创建登录界面"""
    login_css = """
    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .login-box {
        background: white;
        padding: 40px;
        border-radius: 15px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        max-width: 400px;
        width: 100%;
    }
    .login-title {
        text-align: center;
        margin-bottom: 30px;
        color: #333;
        font-size: 24px;
        font-weight: bold;
    }
    """

    with gr.Blocks(css=login_css) as login_demo:
        gr.HTML("""
        <div class="login-container">
            <div class="login-box">
                <div class="login-title">🔐 登录</div>
            </div>
        </div>
        """)
        
        with gr.Row():
            with gr.Column():
                username_input = gr.Textbox(
                    label="用户名",
                    placeholder="请输入用户名",
                    type="text"
                )
                password_input = gr.Textbox(
                    label="密码",
                    placeholder="请输入密码",
                    type="password"
                )
                login_btn = gr.Button("登录", variant="primary", size="lg")
                login_message = gr.Textbox(label="", visible=False)
                session_id_state = gr.State(value="")

                # 登录按钮点击事件
                login_btn.click(
                    fn=login_user,
                    inputs=[username_input, password_input],
                    outputs=[login_message, gr.Textbox(visible=False), session_id_state]
                )
                
                # 显示登录结果
                login_message.change(
                    fn=lambda msg: gr.update(visible=True, value=msg),
                    inputs=[login_message],
                    outputs=[login_message]
                )
        
        gr.HTML("""
        <div style="margin-top: 20px; text-align: center; color: #666; font-size: 14px;">
            <p>默认账号：<br/>admin / admin123<br/>user / user123</p>
        </div>
        """)

    return login_demo

# ----------------------------
# Gradio 界面
# ----------------------------
def create_gradio_interface():
    """创建整合版 Gradio 界面"""

    # 扩展 CSS：添加登录界面和用户栏样式
    extended_css = get_custom_css() + """
    /* 登录界面样式 - 紧凑布局 */
    .login-header {
        text-align: center;
        padding: 15px 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px 12px 0 0;
        margin: -10px -10px 15px -10px;
    }
    .login-title-text {
        color: white;
        font-size: 20px;
        font-weight: 600;
        margin: 0;
    }
    .login-info {
        margin-top: 15px;
        padding: 12px;
        background: #f8f9fa;
        border-radius: 8px;
        color: #666;
        font-size: 12px;
    }
    .login-info p {
        margin: 4px 0;
    }
    
    /* 用户栏样式 */
    .user-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 16px;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 8px;
        margin-bottom: 12px;
        color: white;
    }
    .user-info {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
    }
    .user-avatar {
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: rgba(255,255,255,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
    }
    """

    # 使用 kwargs 来避免 Gradio 6.0+ 的警告
    blocks_kwargs = {
        "title": "整合版 Whisper 语音转文字服务",
        "analytics_enabled": False,
        "delete_cache": (1800, 1800),  # 30分钟清理缓存
    }

    with gr.Blocks(**blocks_kwargs) as demo:
        # 添加自定义 CSS 样式
        gr.HTML(f"<style>{extended_css}</style>")
        
        # ==================== 状态管理 ====================
        session_state = gr.State(value="")
        is_logged_in = gr.State(value=False)
        current_username = gr.State(value="")
        
        # ==================== 登录界面（仅鉴权启用时显示）====================
        with gr.Column(visible=config.ENABLE_TOKEN_AUTH) as login_column:
            with gr.Group():
                # 紧凑的登录标题
                gr.HTML("""
                <div class="login-header">
                    <h2 class="login-title-text">🔐 用户登录</h2>
                </div>
                """)
                
                username_input = gr.Textbox(
                    label="用户名",
                    placeholder="请输入用户名",
                    type="text"
                )
                password_input = gr.Textbox(
                    label="密码",
                    placeholder="请输入密码",
                    type="password"
                )
                
                with gr.Row():
                    login_btn = gr.Button("登录", variant="primary", scale=3)
                    clear_btn = gr.Button("清空", variant="secondary", scale=1)
                
                login_message = gr.Textbox(
                    label="",
                    visible=False,
                    interactive=False
                )
                
                # 登录说明（简化）
                gr.HTML("""
                <div class="login-info">
                    <p>用户名：<code>admin</code> | 密码：<code>API_TOKEN</code> 配置值</p>
                </div>
                """)
                
                # 登录处理临时状态
                login_success_temp = gr.State(value=False)
                login_msg_temp = gr.State(value="")
                login_sid_temp = gr.State(value="")
        
        # ==================== 主界面 ====================
        with gr.Column(visible=not config.ENABLE_TOKEN_AUTH) as main_column:
            # 用户信息栏（仅鉴权启用时显示）
            logout_btn = None
            if config.ENABLE_TOKEN_AUTH:
                with gr.Group() as user_bar:
                    with gr.Row():
                        with gr.Column(scale=4):
                            gr.HTML("""
                            <div class="user-bar">
                                <div class="user-info">
                                    <div class="user-avatar">👤</div>
                                    <span>当前用户：<strong>admin</strong></span>
                                </div>
                            </div>
                            """)
                        with gr.Column(scale=1, min_width=100):
                            logout_btn = gr.Button("退出登录", variant="secondary", size="sm")
            
            # 页面头部
            create_header()

            # 定义状态变量
            job_completed = gr.State(value=False)

            with gr.Tabs():
                # 语音合成标签页
                with gr.TabItem("🎤 语音合成"):
                    create_tts_interface()

                # 高级字幕生成标签页
                with gr.TabItem("📝 字幕生成"):
                    create_subtitle_interface()

                # 图像处理标签页
                with gr.TabItem("🖼️ 图像处理"):
                    create_image_processing_interface()

                # 自动剪辑标签页
                with gr.TabItem("✂️ 自动剪辑"):
                    create_video_editor_interface()

                # 视频转场特效标签页
                with gr.TabItem("🎬 视频转场"):
                    create_transition_interface()

                # 视频合并标签页
                with gr.TabItem("🔗 视频合并"):
                    create_video_merge_interface()

                # 综合处理标签页
                with gr.TabItem("🚀 综合处理"):
                    create_batch_processing_interface()

                # 模板管理标签页
                with gr.TabItem("📁 模板管理"):
                    get_template_manager_ui()

                # 文件持久化标签页
                with gr.TabItem("☁️ 文件持久化"):
                    create_file_persistence_interface()

                # ComfyUI 集成标签页
                with gr.TabItem("🎨 ComfyUI"):
                    create_comfyui_interface()

                # 通用HTTP集成标签页
                with gr.TabItem("🌐 HTTP集成"):
                    create_http_integration_interface()

                # 邮件发送标签页
                with gr.TabItem("📧 邮件发送"):
                    create_email_interface()
        
        # ==================== 事件绑定（必须在所有组件定义之后）====================
        if config.ENABLE_TOKEN_AUTH:
            def handle_login(success, message, session_id):
                """处理登录结果，切换界面"""
                if success:
                    return (
                        gr.update(visible=False),    # login_column 隐藏
                        gr.update(visible=True),     # main_column 显示
                        session_id,                   # session_state
                        True,                         # is_logged_in
                        "admin",                      # current_username
                        gr.update(visible=False),    # login_message
                    )
                else:
                    return (
                        gr.update(visible=True),     # login_column 保持显示
                        gr.update(visible=False),    # main_column 保持隐藏
                        "",                           # session_state
                        False,                        # is_logged_in
                        "",                           # current_username
                        gr.update(visible=True, value="❌ " + message),  # 显示错误
                    )
            
            def handle_logout():
                """处理登出"""
                return (
                    gr.update(visible=True),   # login_column 显示
                    gr.update(visible=False),  # main_column 隐藏
                    "",                         # session_state
                    False,                      # is_logged_in
                    "",                         # current_username
                    gr.update(visible=False),  # login_message
                )
            
            # 登录按钮事件
            login_btn.click(
                fn=login_user,
                inputs=[username_input, password_input],
                outputs=[login_success_temp, login_msg_temp, login_sid_temp]
            ).then(
                fn=handle_login,
                inputs=[login_success_temp, login_msg_temp, login_sid_temp],
                outputs=[login_column, main_column, session_state, is_logged_in, current_username, login_message]
            )
            
            # 清空按钮事件
            clear_btn.click(
                fn=lambda: ("", "", gr.update(visible=False)),
                outputs=[username_input, password_input, login_message]
            )
            
            # 登出按钮事件
            logout_btn.click(
                fn=handle_logout,
                outputs=[login_column, main_column, session_state, is_logged_in, current_username, login_message]
            )

    return demo


# 初始化文件持久化管理器（在 Gradio 界面创建之前）
try:
    from modules.file_persistence import init_persistence_manager
    init_persistence_manager(
        huggingface_token=config.HUGGINGFACE_TOKEN,
        modelscope_token=config.MODELSCOPE_TOKEN
    )
    Logger.info("文件持久化管理器初始化成功")
except Exception as e:
    Logger.warning(f"文件持久化管理器初始化失败: {str(e)}")

# 根据配置决定是否启用 Gradio UI
if config.ENABLE_GRADIO_UI:
    # 创建 Gradio 应用
    gradio_app = create_gradio_interface()
    # 挂载 Gradio 应用到 FastAPI
    app = gr.mount_gradio_app(app, gradio_app, path="/")
    Logger.info("Gradio UI 已启用")
else:
    gradio_app = None
    Logger.info("Gradio UI 已禁用，仅提供 API 服务")

# ----------------------------
# 根路由
# ----------------------------
@app.get("/")
async def root():
    """根路由，返回欢迎信息"""
    if config.ENABLE_GRADIO_UI:
        # 启用 Gradio UI 时的欢迎页面
        return HTMLResponse(content=f"""
        <html>
            <head>
                <title>整合版 Whisper 语音转文字服务</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
                        max-width: 800px;
                        margin: 50px auto;
                        padding: 20px;
                        background-color: #f8f9fa;
                    }}
                    h1 {{
                        color: #333;
                    }}
                    .container {{
                        background-color: white;
                        padding: 30px;
                        border-radius: 10px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }}
                    .link {{
                        display: inline-block;
                        margin: 10px 10px 10px 0;
                        padding: 10px 20px;
                        background-color: #007bff;
                        color: white;
                        text-decoration: none;
                        border-radius: 5px;
                    }}
                    .link:hover {{
                        background-color: #0056b3;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🎙️ 整合版 Whisper 语音转文字服务</h1>
                    <p>欢迎使用整合版 Whisper 语音转文字服务！</p>
                    <p>版本: 3.0.0 (模块化重构版本)</p>
                    <h2>快速开始</h2>
                    <a href="{config.GRADIO_URL}" class="link">访问 Web 界面</a>
                    <a href="{config.DOCS_URL}" class="link">API 文档 (Swagger)</a>
                    <a href="{config.BASE_URL}/redoc" class="link">API 文档 (ReDoc)</a>
                    <h2>功能特性</h2>
                    <ul>
                        <li>🎤 语音合成 - 基于 VoxCPM 的高质量语音合成</li>
                        <li>📝 字幕生成 - 自动生成视频字幕，支持翻译和烧录</li>
                        <li>🖼️ 图像处理 - 图片去背景、图片混合等图像处理功能</li>
                        <li>🎬 视频转场 - 多种专业视频转场效果</li>
                        <li>🔗 视频合并 - 合并多个视频文件为一个视频</li>
                        <li>🔊 语音识别 - 基于 faster-whisper 的高性能语音识别</li>
                        <li>☁️ 文件持久化 - 将文件上传到 HuggingFace/ModelScope 等云平台</li>
                        <li>🌐 通用HTTP集成 - 对外部HTTP接口进行集成，支持多种认证方式和请求格式</li>
                    </ul>
                    <h2>技术架构</h2>
                    <p>本服务采用模块化架构设计，遵循高内聚、低耦合原则：</p>
                    <ul>
                        <li><strong>config.py</strong> - 统一配置管理</li>
                        <li><strong>utils/</strong> - 工具类模块（文件操作、系统工具、媒体处理等）</li>
                        <li><strong>modules/</strong> - 功能模块（Whisper服务、语音合成、字幕生成、视频转场）</li>
                        <li><strong>api/</strong> - API 路由和认证</li>
                        <li><strong>ui/</strong> - Gradio UI 界面组件</li>
                    </ul>
                </div>
            </body>
        </html>
        """)
    else:
        # 禁用 Gradio UI 时的 API 专用欢迎页面
        return HTMLResponse(content=f"""
        <html>
            <head>
                <title>整合版 Whisper 语音转文字服务 - API Mode</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
                        max-width: 800px;
                        margin: 50px auto;
                        padding: 20px;
                        background-color: #f8f9fa;
                    }}
                    h1 {{
                        color: #333;
                    }}
                    .container {{
                        background-color: white;
                        padding: 30px;
                        border-radius: 10px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }}
                    .link {{
                        display: inline-block;
                        margin: 10px 10px 10px 0;
                        padding: 10px 20px;
                        background-color: #007bff;
                        color: white;
                        text-decoration: none;
                        border-radius: 5px;
                    }}
                    .link:hover {{
                        background-color: #0056b3;
                    }}
                    .badge {{
                        display: inline-block;
                        padding: 5px 10px;
                        background-color: #28a745;
                        color: white;
                        border-radius: 5px;
                        font-size: 12px;
                        margin-left: 10px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🎙️ 整合版 Whisper 语音转文字服务 <span class="badge">API Mode</span></h1>
                    <p>欢迎使用整合版 Whisper 语音转文字服务 API 模式！</p>
                    <p>版本: 3.0.0 (模块化重构版本)</p>
                    <h2>快速开始</h2>
                    <a href="{config.DOCS_URL}" class="link">API 文档 (Swagger)</a>
                    <a href="{config.BASE_URL}/redoc" class="link">API 文档 (ReDoc)</a>
                    <h2>功能特性</h2>
                    <ul>
                        <li>🎤 语音合成 - 基于 VoxCPM 的高质量语音合成</li>
                        <li>📝 字幕生成 - 自动生成视频字幕，支持翻译和烧录</li>
                        <li>🖼️ 图像处理 - 图片去背景、图片混合等图像处理功能</li>
                        <li>🎬 视频转场 - 多种专业视频转场效果</li>
                        <li>🔗 视频合并 - 合并多个视频文件为一个视频</li>
                        <li>🔊 语音识别 - 基于 faster-whisper 的高性能语音识别</li>
                        <li>📁 模板管理 - 管理综合处理模板文件</li>
                        <li>🚀 综合处理 - 基于模板的自动化视频处理</li>
                        <li>☁️ 文件持久化 - 将文件上传到 HuggingFace/ModelScope 等云平台</li>
                        <li>🌐 通用HTTP集成 - 对外部HTTP接口进行集成，支持多种认证方式和请求格式</li>
                    </ul>
                    <h2>认证方式</h2>
                    <p>所有 API 端点都需要通过 Bearer Token 认证。</p>
                    <p>请使用环境变量或配置文件中设置的 Token 进行认证。</p>
                    <h2>技术架构</h2>
                    <p>本服务采用模块化架构设计，遵循高内聚、低耦合原则：</p>
                    <ul>
                        <li><strong>config.py</strong> - 统一配置管理</li>
                        <li><strong>utils/</strong> - 工具类模块（文件操作、系统工具、媒体处理等）</li>
                        <li><strong>modules/</strong> - 功能模块（Whisper服务、语音合成、字幕生成、视频转场）</li>
                        <li><strong>api/</strong> - API 路由和认证</li>
                    </ul>
                    <h2>配置说明</h2>
                    <p>当前运行模式：API 专用模式（Gradio UI 已禁用）</p>
                    <p>如需启用 Web 界面，请设置环境变量：<code>ENABLE_GRADIO_UI=true</code></p>
                </div>
            </body>
        </html>
        """)


# ----------------------------
# 启动信息
# ----------------------------
@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    Logger.info("=" * 50)
    Logger.info("整合版 Whisper 语音转文字服务启动中...")
    Logger.info("=" * 50)
    Logger.info(f"版本: 3.0.0 (模块化重构版本)")
    Logger.info(f"服务地址: {config.BASE_URL}")
    Logger.info(f"API 文档: {config.DOCS_URL}")
    Logger.info(f"Whisper 模型: {config.DEFAULT_MODEL}")
    Logger.info(f"设备: {config.DEFAULT_DEVICE}")
    Logger.info(f"Gradio UI: {'已启用' if config.ENABLE_GRADIO_UI else '已禁用 (API 模式)'}")
    if config.ENABLE_GRADIO_UI:
        Logger.info(f"Web 界面: {config.GRADIO_URL}")

    Logger.info("=" * 50)


# ----------------------------
# 主程序入口
# ----------------------------
if __name__ == "__main__":
    import uvicorn

    Logger.info(f"Starting server on {config.HOST}:{config.PORT}")

    uvicorn.run(
        "app:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,  # 生产环境关闭热重载
        log_level="info"
    )