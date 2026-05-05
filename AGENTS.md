# AGENTS.md - 项目架构与模块说明

## 项目概述

VD (Video Processing Service) 是一个基于 FastAPI + React + Remotion 的现代化视频处理服务。项目采用模块化设计，遵循高内聚、低耦合原则，提供完整的视频处理、AI 生成、自动化工作流等功能。

### 核心特性

- **现代化前端**: React + TypeScript + Vite + Remotion
- **后端服务**: FastAPI REST API with Bearer token 认证
- **AI 能力**: Whisper ASR、TTS 合成、ComfyUI 图像生成
- **视频处理**: 视频编辑、转场、合并、批量处理
- **自动化**: HTTP 集成、邮件发送、文件持久化
- **部署**: Docker 多阶段构建，支持 HuggingFace Spaces

---

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                        前端层 (React)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Pages   │  │Components│  │ Services │  │  Store   │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────┘
                            │ HTTP/REST
                            ▼
┌─────────────────────────────────────────────────────────┐
│                      API 层 (FastAPI)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Routes  │  │  Auth    │  │Response  │  │Middleware│  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    业务逻辑层 (Modules)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Whisper  │  │   TTS    │  │ Subtitle │  │  Video   │  │
│  │ Service  │  │  ONNX    │  │  Module  │  │  Editor  │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Image   │  │  ComfyUI │  │  Email   │  │   HTTP   │  │
│  │  Proc    │  │  Module  │  │  Module  │  │  Integ   │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    工具层 (Utils)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Logger  │  │  Media   │  │  File    │  │  Config  │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 技术栈

**前端:**
- React 18 + TypeScript
- Vite (构建工具)
- React Router (路由)
- Zustand (状态管理)
- Remotion (视频生成)
- Tailwind CSS (样式)

**后端:**
- FastAPI (Web 框架)
- Pydantic (数据验证)
- faster-whisper (ASR)
- ONNX Runtime (TTS)
- FFmpeg (视频处理)
- ComfyUI (图像生成)

**部署:**
- Docker (容器化)
- Nginx (反向代理)
- HuggingFace Spaces (托管)

---

## 前端结构

### 目录结构

```
frontend/
├── src/
│   ├── components/          # 可复用组件
│   │   ├── Layout.tsx      # 布局组件
│   │   ├── FileUpload.tsx  # 文件上传组件
│   │   └── PageContainer.tsx # 页面容器
│   ├── pages/              # 页面组件
│   │   ├── Login.tsx       # 登录页面
│   │   ├── Dashboard.tsx   # 仪表板
│   │   ├── TTSSynthesis.tsx # TTS 合成
│   │   ├── SubtitleGeneration.tsx # 字幕生成
│   │   ├── ImageProcessing.tsx # 图像处理
│   │   ├── VideoEditor.tsx # 视频编辑
│   │   ├── VideoTransition.tsx # 视频转场
│   │   ├── VideoMerge.tsx  # 视频合并
│   │   ├── BatchProcessing.tsx # 批量处理
│   │   ├── TemplateManager.tsx # 模板管理
│   │   ├── EmailSender.tsx  # 邮件发送
│   │   ├── FilePersistence.tsx # 文件持久化
│   │   ├── ComfyUIIntegration.tsx # ComfyUI 集成
│   │   ├── HTTPIntegration.tsx # HTTP 集成
│   │   └── RemotionStudio.tsx # Remotion 工作室
│   ├── remotion/           # Remotion 组件
│   │   └── MyVideo.tsx     # 视频组件
│   ├── services/           # API 服务
│   │   └── api.ts          # API 客户端
│   ├── store/              # 状态管理
│   │   └── authStore.ts    # 认证状态
│   ├── types/              # 类型定义
│   │   └── index.ts        # 类型声明
│   ├── styles/             # 样式文件
│   │   └── index.css       # 全局样式
│   ├── App.tsx             # 应用入口
│   └── main.tsx            # 主入口
├── public/                 # 静态资源
├── package.json            # 依赖配置
├── vite.config.ts          # Vite 配置
├── tsconfig.json           # TypeScript 配置
└── index.html              # HTML 模板
```

### 页面路由

| 路径 | 组件 | 功能 |
|------|------|------|
| `/login` | Login | 用户登录 |
| `/dashboard` | Dashboard | 仪表板 |
| `/tts` | TTSSynthesis | TTS 语音合成 |
| `/subtitle` | SubtitleGeneration | 字幕生成 |
| `/image` | ImageProcessing | 图像处理 |
| `/video-editor` | VideoEditor | 视频编辑 |
| `/video-transition` | VideoTransition | 视频转场 |
| `/video-merge` | VideoMerge | 视频合并 |
| `/batch` | BatchProcessing | 批量处理 |
| `/templates` | TemplateManager | 模板管理 |
| `/email` | EmailSender | 邮件发送 |
| `/files` | FilePersistence | 文件持久化 |
| `/comfyui` | ComfyUIIntegration | ComfyUI 集成 |
| `/http` | HTTPIntegration | HTTP 集成 |
| `/remotion` | RemotionStudio | Remotion 工作室 |

### 组件说明

**Layout.tsx**
- 主布局组件
- 侧边栏导航
- 认证保护
- 响应式设计

**FileUpload.tsx**
- 文件上传组件
- 支持拖拽上传
- 进度显示
- 错误处理

**PageContainer.tsx**
- 页面容器组件
- 统一页面样式
- 加载状态管理

---

## 后端结构

### 目录结构

```
├── api/                    # API 层
│   ├── __init__.py
│   ├── auth.py             # 认证服务
│   ├── response_formatter.py # 响应格式化
│   └── routes.py           # 路由定义
├── modules/                # 业务模块
│   ├── __init__.py
│   ├── whisper_service.py  # Whisper ASR 服务
│   ├── tts_onnx_module.py  # TTS ONNX 模块
│   ├── subtitle_module.py  # 字幕生成模块
│   ├── transition_module.py # 视频转场模块
│   ├── image_processing_module.py # 图像处理模块
│   ├── video_editor_module.py # 视频编辑模块
│   ├── video_merge_module.py # 视频合并模块
│   ├── email_module.py     # 邮件模块
│   ├── comfyui_module.py   # ComfyUI 模块
│   ├── http_integration_module.py # HTTP 集成模块
│   ├── file_persistence.py # 文件持久化
│   ├── template_manager.py # 模板管理
│   ├── task_orchestrator.py # 任务编排
│   ├── task_handlers.py    # 任务处理器
│   ├── parameter_resolver.py # 参数解析
│   └── auto_video_task_module.py # 自动视频任务
├── utils/                  # 工具层
│   ├── __init__.py
│   ├── logger.py           # 日志工具
│   ├── media_processor.py  # 媒体处理
│   └── tts_onnx/           # TTS ONNX 工具
│       └── __init__.py
├── config.py               # 配置管理
├── app.py                  # 应用入口
└── requirements.txt        # Python 依赖
```

### 模块说明

#### 核心模块

**whisper_service.py**
- Whisper ASR 服务
- 音频转文字
- 支持多语言
- 模型管理

**tts_onnx_module.py**
- TTS 语音合成
- ONNX 模型推理
- 多语言支持
- 音频导出

**subtitle_module.py**
- 字幕生成
- 时间轴管理
- 格式转换
- 样式定制

#### 视频处理模块

**video_editor_module.py**
- 视频编辑
- 剪裁、裁剪
- 滤镜应用
- 音频处理

**video_merge_module.py**
- 视频合并
- 多视频拼接
- 转场效果
- 音频混合

**transition_module.py**
- 视频转场
- 转场效果库
- 参数配置
- 预览生成

#### AI 生成模块

**image_processing_module.py**
- 图像处理
- 滤镜、调整
- 格式转换
- 批量处理

**comfyui_module.py**
- ComfyUI 集成
- 图像生成
- 工作流管理
- 参数配置

#### 集成模块

**email_module.py**
- 邮件发送
- SMTP 配置
- 附件支持
- 模板渲染

**http_integration_module.py**
- HTTP 集成
- Webhook 调用
- API 代理
- 数据同步

**file_persistence.py**
- 文件持久化
- 存储管理
- 访问控制
- 版本管理

#### 任务管理模块

**task_orchestrator.py**
- 任务编排
- 工作流管理
- 依赖处理
- 状态跟踪

**task_handlers.py**
- 任务处理器
- 异步执行
- 错误处理
- 结果收集

**parameter_resolver.py**
- 参数解析
- 变量替换
- 表达式求值
- 类型转换

**auto_video_task_module.py**
- 自动视频任务
- 智能生成
- 模板应用
- 批量处理

**template_manager.py**
- 模板管理
- 模板存储
- 版本控制
- 参数化

---

## API 接口

### 认证接口

#### POST /api/login
用户登录

**请求:**
```json
{
  "username": "admin",
  "password": "password"
}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 1,
      "username": "admin"
    }
  }
}
```

### TTS 接口

#### POST /api/tts/synthesize
TTS 语音合成

**请求:**
```json
{
  "text": "Hello, world!",
  "voice": "en-US",
  "speed": 1.0
}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "audio_url": "/output/audio_123456.wav",
    "duration": 2.5
  }
}
```

### 字幕接口

#### POST /api/subtitle/generate
字幕生成

**请求:**
```json
{
  "video_path": "/uploads/video.mp4",
  "language": "zh",
  "format": "srt"
}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "subtitle_path": "/output/subtitle.srt",
    "segments": [
      {
        "start": 0.0,
        "end": 2.5,
        "text": "Hello, world!"
      }
    ]
  }
}
```

### 视频处理接口

#### POST /api/video/edit
视频编辑

**请求:**
```json
{
  "video_path": "/uploads/video.mp4",
  "operations": [
    {
      "type": "trim",
      "start": 0,
      "end": 10
    }
  ]
}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "output_path": "/output/video_edited.mp4"
  }
}
```

#### POST /api/video/merge
视频合并

**请求:**
```json
{
  "videos": [
    "/uploads/video1.mp4",
    "/uploads/video2.mp4"
  ],
  "transition": "fade"
}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "output_path": "/output/video_merged.mp4"
  }
}
```

### 图像处理接口

#### POST /api/image/process
图像处理

**请求:**
```json
{
  "image_path": "/uploads/image.jpg",
  "operations": [
    {
      "type": "resize",
      "width": 1920,
      "height": 1080
    }
  ]
}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "output_path": "/output/image_processed.jpg"
  }
}
```

### ComfyUI 接口

#### POST /api/comfyui/generate
ComfyUI 图像生成

**请求:**
```json
{
  "prompt": "A beautiful landscape",
  "negative_prompt": "blurry, low quality",
  "width": 1024,
  "height": 1024,
  "steps": 20
}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "image_path": "/output/image_123456.png"
  }
}
```

### 邮件接口

#### POST /api/email/send
发送邮件

**请求:**
```json
{
  "to": "user@example.com",
  "subject": "Test Email",
  "body": "Hello, world!",
  "attachments": ["/uploads/file.pdf"]
}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "message_id": "abc123"
  }
}
```

### HTTP 集成接口

#### POST /api/http/webhook
Webhook 调用

**请求:**
```json
{
  "url": "https://example.com/webhook",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "key": "value"
  }
}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "status_code": 200,
    "response": {}
  }
}
```

### 文件管理接口

#### POST /api/files/upload
文件上传

**请求:** multipart/form-data
- file: 文件

**响应:**
```json
{
  "success": true,
  "data": {
    "file_path": "/uploads/file.jpg",
    "file_size": 123456
  }
}
```

#### GET /api/files/list
文件列表

**响应:**
```json
{
  "success": true,
  "data": {
    "files": [
      {
        "name": "file.jpg",
        "path": "/uploads/file.jpg",
        "size": 123456,
        "created_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

### 批量处理接口

#### POST /api/batch/process
批量处理

**请求:**
```json
{
  "tasks": [
    {
      "type": "tts",
      "params": {
        "text": "Hello"
      }
    },
    {
      "type": "subtitle",
      "params": {
        "video_path": "/uploads/video.mp4"
      }
    }
  ]
}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "job_id": "job_20240101-120000",
    "status": "running"
  }
}
```

---

## 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `API_TOKEN` | `opq#key` | API 认证令牌 |
| `SECRET_KEY` | `your-secret-key-change-in-production` | JWT 密钥 |
| `HOST` | `0.0.0.0` | 服务监听地址 |
| `PORT` | `7860` | 服务监听端口 |
| `FW_MODEL` | `small` | Whisper 模型 |
| `FW_DEVICE` | `cpu` | Whisper 设备 |
| `FW_COMPUTE` | `int8` | Whisper 计算精度 |
| `FW_MODELS_DIR` | `models` | 模型目录 |
| `FW_USE_LOCAL_MODELS` | `true` | 使用本地模型 |
| `UPLOAD_FOLDER` | `uploads` | 上传目录 |
| `OUTPUT_FOLDER` | `output` | 输出目录 |
| `DEBUG_FOLDER` | `debug` | 调试目录 |
| `JOB_TIMEOUT` | `3600` | 任务超时时间(秒) |
| `POLLING_INTERVAL` | `2.0` | 轮询间隔(秒) |

### 配置文件

**config.py**
```python
class Config:
    # 服务配置
    API_TOKEN = os.environ.get("API_TOKEN", "opq#key")
    SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production")
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", 7860))

    # Whisper 配置
    DEFAULT_MODEL = os.environ.get("FW_MODEL", "small")
    DEFAULT_DEVICE = os.environ.get("FW_DEVICE", "cpu")
    DEFAULT_COMPUTE = os.environ.get("FW_COMPUTE", "int8")

    # 文件配置
    UPLOAD_FOLDER = 'uploads'
    OUTPUT_FOLDER = 'output'
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

    # 任务配置
    JOB_TIMEOUT = 3600
    POLLING_INTERVAL = 2.0
```

---

## 部署说明

### Docker 部署

#### 构建镜像

```bash
# 使用 Dockerfile.react
docker build -f Dockerfile.react -t vd-service:latest .
```

#### 运行容器

```bash
docker run -d \
  -p 7860:7860 \
  -e API_TOKEN=your-token \
  -e SECRET_KEY=your-secret \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/output:/app/output \
  vd-service:latest
```

#### Docker Compose

```bash
docker-compose up -d
```

### HuggingFace Spaces 部署

#### 准备工作

1. 创建 HuggingFace Space
2. 选择 Docker 运行时
3. 上传代码

#### 配置

在 Space 设置中配置环境变量:
- `API_TOKEN`: 你的 API 令牌
- `SECRET_KEY`: 你的密钥

#### 部署

```bash
# 使用部署脚本
./deploy.sh
```

### 本地开发

#### 后端开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python app.py
```

#### 前端开发

```bash
# 安装依赖
cd frontend
npm install

# 启动开发服务器
npm run dev
```

#### 构建前端

```bash
cd frontend
npm run build
```

---

## 开发指南

### 添加新页面

1. 在 `frontend/src/pages/` 创建新组件
2. 在 `frontend/src/App.tsx` 添加路由
3. 在 `frontend/src/components/Layout.tsx` 添加菜单项
4. 在 `frontend/src/services/api.ts` 添加 API 调用

### 添加新模块

1. 在 `modules/` 创建新模块
2. 在 `api/routes.py` 添加路由
3. 在 `modules/__init__.py` 导出模块
4. 在 `app.py` 导入模块

### 添加新 API

1. 在 `api/routes.py` 定义路由
2. 在 `modules/` 实现业务逻辑
3. 在 `frontend/src/services/api.ts` 添加客户端
4. 在 `frontend/src/types/index.ts` 添加类型定义

### 测试

```bash
# 后端测试
pytest

# 前端测试
npm test

# 集成测试
npm run test:e2e
```

---

## 故障排查

### 常见问题

**1. 前端无法连接后端**
- 检查 CORS 配置
- 确认后端服务运行
- 检查 API 地址配置

**2. Whisper 模型加载失败**
- 检查模型路径配置
- 确认模型文件存在
- 检查磁盘空间

**3. TTS 合成失败**
- 检查 ONNX 模型
- 确认 ONNX Runtime 安装
- 检查音频编码器

**4. 视频处理失败**
- 检查 FFmpeg 安装
- 确认视频格式支持
- 检查磁盘空间

**5. Docker 构建失败**
- 检查 Docker 版本
- 确认网络连接
- 检查依赖版本

### 日志查看

```bash
# 查看应用日志
docker logs <container_id>

# 查看实时日志
docker logs -f <container_id>

# 查看特定模块日志
grep "whisper_service" logs/app.log
```

---

## 性能优化

### 前端优化

- 使用 React.memo 避免不必要的重渲染
- 使用 useMemo/useCallback 优化计算
- 代码分割和懒加载
- 图片压缩和 CDN 加速

### 后端优化

- 使用异步 I/O
- 缓存常用数据
- 批量处理请求
- 使用连接池

### 视频处理优化

- 使用硬件加速
- 调整 FFmpeg 参数
- 并行处理任务
- 使用临时文件

---

## 安全建议

1. **生产环境必须修改默认密钥**
   - 修改 `SECRET_KEY`
   - 修改 `API_TOKEN`

2. **启用 HTTPS**
   - 使用 SSL 证书
   - 配置 Nginx 反向代理

3. **限制文件上传**
   - 设置文件大小限制
   - 验证文件类型
   - 扫描恶意文件

4. **访问控制**
   - 使用认证中间件
   - 限制 API 调用频率
   - 记录访问日志

5. **数据备份**
   - 定期备份重要数据
   - 使用版本控制
   - 监控系统状态

---

## 贡献指南

### 代码规范

- Python: PEP 8
- TypeScript: ESLint + Prettier
- Git: Conventional Commits

### 提交规范

```
feat: 添加新功能
fix: 修复 bug
docs: 更新文档
style: 代码格式调整
refactor: 代码重构
test: 添加测试
chore: 构建/工具变动
```

### Pull Request 流程

1. Fork 项目
2. 创建分支
3. 提交代码
4. 创建 PR
5. 等待 review
6. 合并代码

---

## 许可证

MIT License

---

## 联系方式

- 项目地址: https://github.com/yourusername/vd
- 问题反馈: https://github.com/yourusername/vd/issues
- 邮箱: your.email@example.com

---

## 更新日志

### v4.0.0 (2024-01-01)

- 完全重构前端为 React
- 移除所有 Gradio 依赖
- 添加 Remotion 集成
- 优化模块化架构
- 改进部署流程

### v3.0.0 (2023-12-01)

- 添加 ComfyUI 集成
- 优化视频处理性能
- 添加批量处理功能

### v2.0.0 (2023-11-01)

- 添加 TTS 功能
- 添加字幕生成
- 优化 API 接口

### v1.0.0 (2023-10-01)

- 初始版本
- 基础视频处理功能
- Gradio UI