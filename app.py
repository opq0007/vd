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

from fastapi import FastAPI
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
    transition_module
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
    create_video_editor_interface
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
# Gradio 界面
# ----------------------------
def create_gradio_interface():
    """创建整合版 Gradio 界面"""

    custom_css = get_custom_css()

    with gr.Blocks(
        css=custom_css,
        title="整合版 Whisper 语音转文字服务",
        theme=gr.themes.Soft(),
        analytics_enabled=False,
        delete_cache=(1800, 1800)  # 30分钟清理缓存
    ) as demo:
        # 页面头部
        create_header()

        # 定义状态变量
        job_completed = gr.State(value=False)

        with gr.Tabs():
            # 语音合成标签页
            with gr.TabItem("🎤 语音合成"):
                create_tts_interface()

            # 高级字幕生成标签页
            with gr.TabItem("高级字幕生成"):
                create_subtitle_interface()

            # 自动剪辑标签页
            with gr.TabItem("✂️ 自动剪辑"):
                create_video_editor_interface()

            # 视频转场特效标签页
            with gr.TabItem("视频转场特效"):
                create_transition_interface()

            # API文档标签页
            with gr.TabItem("API文档"):
                gr.Markdown("## API 文档")
                gr.Markdown("### Swagger UI")
                gr.Markdown(f"[点击访问 Swagger UI]({config.DOCS_URL})")
                gr.Markdown("### ReDoc")
                gr.Markdown(f"[点击访问 ReDoc]({config.BASE_URL}/redoc)")
                gr.Markdown("### 主要 API 端点")
                gr.Markdown("""
#### 认证相关
- `POST /api/login` - 用户登录

#### 模型信息
- `GET /api/model/info` - 获取 Whisper 模型信息
- `GET /api/health` - 健康检查

#### 语音识别 (Whisper)
- `POST /api/transcribe/basic` - 基础语音转文字
- `POST /api/transcribe/advanced` - 高级语音转文字（支持词级时间戳）

#### 语音合成 (VoxCPM-1.5 ONNX)
- `POST /api/tts/synthesize` - 语音合成（支持参考音频和预编码特征）
- `POST /api/tts/save_ref` - 保存参考音频特征
- `GET /api/tts/info` - 获取 TTS 模型信息
- `GET /api/tts/ref_features` - 获取所有已保存的参考音频特征

#### 文件操作
- `GET /api/file/download?file_path=xxx` - 下载文件（返回二进制流）

#### 字幕生成
- `POST /api/subtitle/generate` - 生成视频字幕

#### 视频转场
- `POST /api/transition/apply` - 应用转场效果
- `GET /api/transition/list` - 获取转场效果列表
- `GET /api/transition/params/{transition_name}` - 获取转场参数
                """)

    return demo


# 创建 Gradio 应用
gradio_app = create_gradio_interface()

# 挂载 Gradio 应用到 FastAPI
app = gr.mount_gradio_app(app, gradio_app, path="/")

# ----------------------------
# 根路由
# ----------------------------
@app.get("/")
async def root():
    """根路由，返回欢迎信息"""
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
                    <li>🎬 视频转场 - 多种专业视频转场效果</li>
                    <li>🔊 语音识别 - 基于 faster-whisper 的高性能语音识别</li>
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
    Logger.info(f"Web 界面: {config.GRADIO_URL}")
    Logger.info(f"API 文档: {config.DOCS_URL}")
    Logger.info(f"Whisper 模型: {config.DEFAULT_MODEL}")
    Logger.info(f"设备: {config.DEFAULT_DEVICE}")
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