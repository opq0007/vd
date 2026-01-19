# 项目概述

这是一个综合性的视频处理服务项目，采用模块化架构设计，遵循高内聚、低耦合原则。主要包含以下核心功能模块：

1. **Whisper 语音转文字服务** - 基于 faster-whisper 和 FastAPI 的高性能语音转文字 API 服务
2. **语音合成模块 (TTS)** - 基于 VoxCPM 的高质量语音合成，支持参考音频克隆声音
3. **高级字幕生成模块** - 自动生成视频字幕，支持翻译、烧录和水印功能
4. **视频转场特效模块** - 提供多种专业视频转场效果的 Python 实现

## 技术栈

### 核心框架
- **FastAPI** - 高性能 Web 框架，提供 RESTful API
- **Gradio** - 现代化 Web 界面框架
- **faster-whisper** - 高性能语音识别模型
- **VoxCPM** - 高质量语音合成模型
- **PyTorch** - 深度学习框架，用于视频转场处理
- **OpenCV (cv2)** - 视频和图像处理
- **Pillow (PIL)** - 图像处理

### 主要依赖
- `uvicorn` - ASGI 服务器
- `PyJWT` - JWT 身份验证
- `playwright` - 浏览器自动化
- `numpy` - 数值计算
- `torch` - 深度学习框架

## 项目结构

```
vd/
├── app.py                          # 主应用入口（模块化重构版本 v3.0.0）
├── config.py                       # 配置模块 - 统一管理所有配置参数
├── requirements.txt                # Python 依赖包列表
├── start_windows.bat               # Windows 启动脚本
├── start_linux.sh                  # Linux/macOS 启动脚本
├── README.md                       # 项目说明文档
├── IFLOW.md                        # iFlow 上下文文档
├── ui.png                          # UI 截图
├── app_old_backup.py               # 原版本备份（重构前）
│
├── modules/                        # 功能模块目录
│   ├── __init__.py                # 模块初始化
│   ├── whisper_service.py         # Whisper 语音识别服务
│   ├── tts_module.py              # 语音合成模块（VoxCPM）
│   ├── subtitle_module.py         # 高级字幕生成模块
│   └── transition_module.py       # 视频转场特效模块
│
├── utils/                          # 工具类目录
│   ├── __init__.py                # 工具类初始化
│   ├── file_utils.py              # 文件操作工具
│   ├── system_utils.py            # 系统工具（FFmpeg等）
│   ├── media_processor.py         # 媒体处理工具
│   ├── subtitle_generator.py      # 字幕生成工具
│   ├── video_effects.py           # 视频效果处理
│   └── logger.py                  # 日志工具
│
├── api/                            # API 路由目录
│   ├── __init__.py                # API 模块初始化
│   ├── auth.py                    # 认证相关（JWT、用户验证）
│   └── routes.py                  # API 路由定义
│
├── ui/                             # Gradio UI 界面目录
│   ├── __init__.py                # UI 模块初始化
│   ├── base_ui.py                 # 基础 UI 组件
│   ├── tts_ui.py                  # 语音合成界面
│   ├── subtitle_ui.py             # 字幕生成界面
│   └── transition_ui.py           # 转场特效界面
│
├── video_transitions/              # 视频转场特效模块（保持不变）
│   ├── __init__.py                # 模块初始化
│   ├── base.py                    # 转场效果基类
│   ├── factory.py                 # 转场效果工厂类
│   ├── registry.py                # 转场效果注册表
│   ├── processor.py               # 转场处理器
│   ├── ui.py                      # Gradio 界面实现
│   ├── crossfade.py               # 交叉淡入淡出转场
│   ├── blink.py                   # 闪烁转场
│   ├── blinds.py                  # 百叶窗转场
│   ├── checkerboard.py            # 棋盘格转场
│   ├── explosion.py               # 爆炸转场
│   ├── shake.py                   # 震动转场
│   ├── warp.py                    # 扭曲转场
│   ├── page_turn.py               # 翻页转场
│   └── flip3d.py                  # 3D 翻转转场
│
├── uploads/                       # 上传文件目录（自动创建）
├── output/                        # 输出文件目录（自动创建）
├── debug/                         # 调试文件目录（自动创建）
└── logs/                          # 日志文件目录（自动创建）
```

## 构建和运行

### 环境要求
- Python 3.8+
- 至少 4GB RAM（推荐 8GB+）
- FFmpeg（用于音视频处理）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

**方式一：使用一键启动脚本**

Windows:
```bash
start_windows.bat
```

Linux/macOS:
```bash
chmod +x start_linux.sh
./start_linux.sh
```

**方式二：手动启动**

```bash
python app.py
```

服务默认运行在 `http://127.0.0.1:7860`

### 服务地址

- **Web 界面**: http://127.0.0.1:7860
- **API 文档**: http://127.0.0.1:7860/docs (Swagger UI)
- **ReDoc 文档**: http://127.0.0.1:7860/redoc

## 开发约定

### 模块化架构设计原则

本项目采用模块化架构，遵循以下设计原则：

1. **高内聚** - 每个模块专注于单一功能领域
2. **低耦合** - 模块之间通过明确的接口通信，减少依赖
3. **单一职责** - 每个类和函数只负责一个明确的功能
4. **开闭原则** - 对扩展开放，对修改关闭

### 代码组织

#### 配置模块（config.py）

- **Config 类** - 统一管理所有配置参数
- 支持环境变量覆盖默认值
- 集中管理服务、模型、文件、认证等配置
- 提供配置验证和初始化方法

#### 工具类模块（utils/）

- **FileUtils** - 文件操作工具（路径处理、文件类型判断、文件复制）
- **SystemUtils** - 系统工具（FFmpeg 检测、命令执行、系统信息）
- **MediaProcessor** - 媒体处理（音频提取、视频合并、字幕烧录）
- **SubtitleGenerator** - 字幕生成（SRT 格式、时间戳格式化）
- **VideoEffectsProcessor** - 视频效果处理（水印、滤镜、文字图像）
- **Logger** - 日志工具（统一的日志记录接口）

#### 功能模块（modules/）

- **WhisperService** - Whisper 语音识别服务
  - 单例模式，支持模型缓存
  - 基础和高级转录功能
  - 模型信息查询

- **TTSModule** - 语音合成模块（VoxCPM）
  - 支持参考音频克隆声音
  - 多种下载源（ModelScope、HF 镜像、HF 原始）
  - 文本标准化和音频降噪

- **SubtitleModule** - 高级字幕生成模块
  - 自动生成视频字幕
  - 字幕翻译功能
  - 硬字幕和软字幕烧录
  - 视频水印添加

- **TransitionModule** - 视频转场模块
  - 集成 video_transitions 包
  - 支持单个和批量转场
  - 转场效果参数查询

#### API 路由模块（api/）

- **AuthService** - 认证服务
  - JWT token 生成和验证
  - 固定 token 验证
  - 用户凭据验证

- **routes.py** - API 路由定义
  - 认证相关路由
  - 语音转文字路由
  - 语音合成路由
  - 字幕生成路由
  - 视频转场路由

#### UI 界面模块（ui/）

- **base_ui.py** - 基础 UI 组件
  - 自定义 CSS 样式
  - 通用组件（文件上传、结果显示、进度条）

- **tts_ui.py** - 语音合成界面
  - 文本输入和参考音频选择
  - 参数配置（CFG、推理步数等）
  - 音频输出显示

- **subtitle_ui.py** - 字幕生成界面
  - 视频上传和参数配置
  - 字幕类型选择（生成/硬字幕/软字幕）
  - 水印配置

- **transition_ui.py** - 转场特效界面
  - 视频输入和转场效果选择
  - 参数配置（帧数、帧率、尺寸）
  - 视频输出显示

#### 主应用入口（app.py）

- FastAPI 应用初始化
- CORS 配置
- API 路由注册
- Gradio 界面挂载
- 启动事件处理

### 转场效果开发规范

新增转场效果需要：

1. 继承 `BaseTransition` 基类
2. 实现 `get_params()` 方法，返回参数配置
3. 实现 `apply_transition()` 异步方法，执行转场逻辑
4. 使用 `@register_transition` 装饰器注册效果
5. 在 `video_transitions/__init__.py` 中导出新效果

参数配置格式：
```python
{
    'param_name': {
        'type': 'choice|int|float|boolean|string',
        'default': default_value,
        'description': '参数描述',
        'options': [],  # choice 类型必需
        'min': 0,       # int/float 类型可选
        'max': 100,     # int/float 类型可选
        'step': 0.1     # float 类型可选
    }
}
```

### 命名约定

- 类名使用 PascalCase（如 `BaseTransition`）
- 函数和方法名使用 snake_case（如 `apply_transition`）
- 常量使用 UPPER_SNAKE_CASE（如 `API_TOKEN`）
- 私有方法使用前缀下划线（如 `_load_media`）

### 错误处理

- 使用 `try-except` 捕获异常
- 记录详细的错误日志
- 返回用户友好的错误消息
- 对于媒体处理失败，提供具体的失败原因

### 日志规范

- 使用 Python 标准的 `logging` 模块
- 日志级别：DEBUG（调试）、INFO（信息）、WARNING（警告）、ERROR（错误）
- 关键操作记录 INFO 级别日志
- 错误记录 ERROR 级别日志并包含堆栈信息

## API 端点

### 认证

支持两种认证方式：

1. **JWT Token** - 通过登录获取
2. **固定 API Token** - 用于自动化调用

默认账号：
- 管理员: `admin` / `admin123`
- 普通用户: `user` / `user123`

固定 token：
- `whisper-api-key-2024` - 自动化调用
- `test-token` - 测试用途

### 主要 API

#### 认证相关
- `POST /api/login` - 用户登录，获取 JWT token

#### 模型信息
- `GET /api/model/info` - 获取模型信息
- `GET /api/health` - 健康检查

#### 语音转文字
- `POST /api/transcribe/basic` - 基础语音转文字
- `POST /api/transcribe/advanced` - 高级语音转文字（支持词级时间戳）

#### 语音合成
- `POST /api/tts/synthesize` - 语音合成

#### 字幕生成
- `POST /api/subtitle/generate` - 生成视频字幕

#### 视频转场
- `POST /api/transition/apply` - 应用转场效果
- `GET /api/transition/list` - 获取转场效果列表
- `GET /api/transition/params/{transition_name}` - 获取转场参数

#### 综合处理（基于模板）
- `GET /api/batch/templates` - 获取所有可用的模板列表
- `GET /api/batch/template/{template_name}` - 获取指定模板的详细信息
- `POST /api/batch/execute` - 执行模板（表单格式）
- `POST /api/batch/execute_json` - 执行模板（JSON格式，适合程序化调用）

#### 文件下载
- `GET /api/file/download` - 下载文件（返回二进制流）

## 配置管理

所有配置通过 `Config` 类集中管理，支持环境变量覆盖：

```python
# 服务配置
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 7860))

# Whisper 模型配置
DEFAULT_MODEL = os.environ.get("FW_MODEL", "small")
DEFAULT_DEVICE = os.environ.get("FW_DEVICE", "cpu")
DEFAULT_COMPUTE = os.environ.get("FW_COMPUTE", "int8")

# VoxCPM 语音合成配置
VOXCPM_MODEL_DIR = os.environ.get("VOXCPM_MODEL_DIR", "models/OpenBMB__VoxCPM-0.5B")
VOXCPM_REPO_ID = os.environ.get("VOXCPM_REPO_ID", "OpenBMB/VoxCPM-0.5B")

# 认证配置
API_TOKEN = os.environ.get("API_TOKEN", "whisper-api-key-2024")
SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production")

# 文件和目录配置
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
DEBUG_FOLDER = 'debug'
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
```

## 文件处理

### 支持的格式

**视频格式**: .mp4, .avi, .mov, .mkv, .wmv, .flv, .webm
**音频格式**: .mp3, .wav, .m4a, .aac, .ogg, .flac
**图片格式**: .png, .jpg, .jpeg

### 文件大小限制

- 最大文件大小: 50MB
- 上传的文件会在处理完成后自动删除

### 输出目录

- `uploads/` - 上传的临时文件
- `output/` - 处理结果文件
- `debug/` - 调试信息文件
- `logs/` - 日志文件

## 模块化架构优势

### 高内聚

每个模块专注于单一功能领域，内部组件紧密协作：
- `modules/` 中的每个模块独立管理自己的业务逻辑
- `utils/` 中的工具类按功能分类，职责明确
- `api/` 和 `ui/` 分别处理接口和界面逻辑

### 低耦合

模块之间通过明确的接口通信，减少相互依赖：
- 模块之间通过导入和函数调用交互，不直接访问内部状态
- 配置通过 `config.py` 统一管理，避免硬编码
- 工具类提供通用功能，可被多个模块复用

### 易于扩展

新增功能时，只需添加新模块或扩展现有模块：
- 新增转场效果：在 `video_transitions/` 中添加新类
- 新增 UI 组件：在 `ui/` 中添加新文件
- 新增 API 端点：在 `api/routes.py` 中添加路由

### 易于维护

清晰的模块划分使代码定位和修改更加容易：
- 修改语音合成功能：只需编辑 `modules/tts_module.py` 和 `ui/tts_ui.py`
- 修改认证逻辑：只需编辑 `api/auth.py`
- 修改配置：只需编辑 `config.py`

### 独立测试

每个模块可以独立进行单元测试：
- 测试工具类：直接测试 `utils/` 中的函数
- 测试功能模块：mock 依赖项后测试业务逻辑
- 测试 API：使用 FastAPI 测试客户端测试端点

## 模块开发指南

### 新增功能模块

1. 在 `modules/` 中创建新模块文件
2. 定义模块类，实现核心功能
3. 在 `modules/__init__.py` 中导出
4. 在 `api/routes.py` 中添加 API 路由（如需要）
5. 在 `ui/` 中创建 UI 组件（如需要）

### 新增工具类

1. 在 `utils/` 中创建新工具类文件
2. 定义工具类，实现通用功能
3. 在 `utils/__init__.py` 中导出
4. 在需要的地方导入使用

### 新增 UI 组件

1. 在 `ui/` 中创建新 UI 组件文件
2. 定义界面函数，返回 Gradio 组件
3. 在 `ui/__init__.py` 中导出
4. 在 `app.py` 的 `create_gradio_interface()` 中调用

### 新增 API 路由

1. 在 `api/routes.py` 中添加路由函数
2. 使用 `@api_router` 装饰器定义端点
3. 实现请求处理逻辑
4. 返回标准化响应

## 测试

目前项目未包含自动化测试。建议为以下内容添加测试：

1. Whisper 服务的 API 端点
2. 转场效果的参数验证
3. 媒体文件处理功能
4. 认证机制
5. 各个工具类的功能

## 性能优化

- **异步处理** - FastAPI 异步特性提高并发性能
- **模型复用** - 单例模式避免重复加载 Whisper 模型
- **批量处理** - 支持批量音视频处理
- **缓存机制** - 模型和配置缓存
- **模块化设计** - 减少不必要的依赖和加载

## 安全注意事项

1. **生产环境**必须修改 `SECRET_KEY`
2. 使用更安全的认证方式（如 OAuth2）
3. 限制文件上传大小和类型
4. 定期清理临时文件
5. 使用 HTTPS 部署
6. 添加请求速率限制

## 综合处理API使用指南

### 概述

综合处理API提供基于模板的自动化视频处理功能，支持通过API接口调用预定义的模板，一键完成复杂的视频处理任务。

### API端点

#### 1. 获取模板列表
```
GET /api/batch/templates
```

**功能**：获取所有可用的模板列表

**请求头**：
```
Authorization: Bearer {token}
```

**响应示例**：
```json
{
  "success": true,
  "count": 2,
  "templates": [
    {
      "name": "奥特曼生日祝福",
      "description": "奥特曼主题的生日祝福视频模板",
      "version": "1.0",
      "character": "atm",
      "theme": "birthday",
      "task_count": 9,
      "parameters": ["username", "age", "theme_text", "tts_text", "user_images"]
    }
  ]
}
```

#### 2. 获取模板详细信息
```
GET /api/batch/template/{template_name}
```

**功能**：获取指定模板的详细信息，包括参数定义

**请求头**：
```
Authorization: Bearer {token}
```

**响应示例**：
```json
{
  "success": true,
  "template": {
    "name": "奥特曼生日祝福",
    "description": "奥特曼主题的生日祝福视频模板",
    "version": "1.0",
    "parameters": {
      "username": {
        "type": "string",
        "description": "用户名",
        "default": "小明"
      },
      "age": {
        "type": "number",
        "description": "年龄",
        "default": 6
      },
      "theme_text": {
        "type": "string",
        "description": "主题文字",
        "default": "生日快乐"
      },
      "tts_text": {
        "type": "string",
        "description": "TTS文本内容",
        "default": ""
      },
      "user_images": {
        "type": "array",
        "description": "用户图片（0-5张）",
        "default": []
      }
    },
    "task_count": 9
  }
}
```

#### 3. 执行模板（表单格式）
```
POST /api/batch/execute
```

**功能**：执行模板，使用表单格式提交参数

**请求头**：
```
Authorization: Bearer {token}
Content-Type: multipart/form-data
```

**请求参数**：
- `template_name`: 模板名称（必填）
- `username`: 用户名
- `age`: 年龄
- `theme`: 主题文字
- `character`: 操作模板对象
- `sub_character`: 二级对象
- `tts_text`: TTS文本内容
- `user_images`: 上传的用户图片文件（最多6张）
- `user_images_paths`: 用户图片路径（多行文本，每行一个路径）

**响应示例**：
```json
{
  "success": true,
  "template_name": "奥特曼生日祝福",
  "total_tasks": 9,
  "completed_tasks": 9,
  "final_video": "output/job_20260119-120000/final_video.mp4",
  "task_results": [
    {
      "index": 1,
      "id": "task1",
      "name": "语音合成",
      "type": "tts",
      "status": "success",
      "output_files": ["output/job_20260119-120000/out_1.wav"]
    },
    {
      "index": 2,
      "id": "task2",
      "name": "生成字幕",
      "type": "subtitle",
      "status": "success",
      "output_files": ["output/job_20260119-120000/out_2.srt"]
    }
  ]
}
```

#### 4. 执行模板（JSON格式）
```
POST /api/batch/execute_json
```

**功能**：执行模板，使用JSON格式提交参数（适合程序化调用）

**请求头**：
```
Authorization: Bearer {token}
Content-Type: application/json
```

**请求体**：
```json
{
  "template_name": "奥特曼生日祝福",
  "parameters": {
    "username": "小明",
    "age": 6,
    "theme": "生日快乐",
    "character": "奥特曼",
    "sub_character": "赛罗",
    "tts_text": "生日快乐！",
    "user_images": [
      "path/to/image1.jpg",
      "path/to/image2.jpg"
    ]
  }
}
```

**响应示例**：
```json
{
  "success": true,
  "template_name": "奥特曼生日祝福",
  "total_tasks": 9,
  "completed_tasks": 9,
  "final_video": "output/job_20260119-120000/final_video.mp4",
  "task_results": [
    {
      "index": 1,
      "id": "task1",
      "name": "语音合成",
      "type": "tts",
      "status": "success",
      "output_files": ["output/job_20260119-120000/out_1.wav"]
    }
  ]
}
```

### 使用示例

#### Python示例

```python
import requests

# 配置
BASE_URL = "http://127.0.0.1:7860"
TOKEN = "whisper-api-key-2024"
headers = {"Authorization": f"Bearer {TOKEN}"}

# 1. 获取模板列表
response = requests.get(f"{BASE_URL}/api/batch/templates", headers=headers)
templates = response.json()
print(f"可用模板: {templates['count']}个")
for template in templates['templates']:
    print(f"  - {template['name']}: {template['description']}")

# 2. 获取模板详细信息
template_name = "奥特曼生日祝福"
response = requests.get(
    f"{BASE_URL}/api/batch/template/{template_name}",
    headers=headers
)
template_info = response.json()
print(f"模板参数: {template_info['template']['parameters'].keys()}")

# 3. 执行模板（JSON格式）
response = requests.post(
    f"{BASE_URL}/api/batch/execute_json",
    json={
        "template_name": template_name,
        "parameters": {
            "username": "小明",
            "age": 6,
            "theme": "生日快乐",
            "character": "奥特曼",
            "sub_character": "赛罗",
            "tts_text": "生日快乐！",
            "user_images": ["path/to/image1.jpg"]
        }
    },
    headers=headers
)
result = response.json()

if result["success"]:
    print(f"✅ 处理完成！")
    print(f"完成任务: {result['completed_tasks']}/{result['total_tasks']}")
    print(f"最终视频: {result['final_video']}")
    
    # 4. 下载最终视频
    if result["final_video"]:
        video_response = requests.get(
            f"{BASE_URL}/api/file/download",
            params={"file_path": result["final_video"]},
            headers=headers
        )
        with open("output.mp4", "wb") as f:
            f.write(video_response.content)
        print("✅ 视频已下载到 output.mp4")
else:
    print(f"❌ 处理失败: {result.get('error')}")
```

#### cURL示例

```bash
# 配置
BASE_URL="http://127.0.0.1:7860"
TOKEN="whisper-api-key-2024"

# 1. 获取模板列表
curl -X GET "${BASE_URL}/api/batch/templates" \
  -H "Authorization: Bearer ${TOKEN}"

# 2. 执行模板（JSON格式）
curl -X POST "${BASE_URL}/api/batch/execute_json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "奥特曼生日祝福",
    "parameters": {
      "username": "小明",
      "age": 6,
      "theme": "生日快乐"
    }
  }'

# 3. 下载最终视频
curl -X GET "${BASE_URL}/api/file/download?file_path=output/job_xxx/final_video.mp4" \
  -H "Authorization: Bearer ${TOKEN}" \
  -o output.mp4
```

### 任务执行结果说明

每个任务的执行结果包含以下字段：

- `index`: 任务序号
- `id`: 任务ID
- `name`: 任务名称
- `type`: 任务类型（tts/subtitle/image_process/video_editor/video_transition/video_merge）
- `status`: 任务状态（success/failed）
- `error`: 错误信息（如果失败）
- `output_files`: 输出文件列表

### 错误处理

API返回以下HTTP状态码：

- `200 OK`: 请求成功
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 认证失败
- `404 Not Found`: 模板不存在
- `500 Internal Server Error`: 服务器内部错误

错误响应示例：
```json
{
  "detail": "模板不存在: xxx"
}
```

### 注意事项

1. **认证**：所有API接口都需要通过JWT token或固定token认证
2. **文件大小**：上传的文件大小限制为50MB
3. **图片数量**：最多支持6张用户图片
4. **异步处理**：模板执行是异步的，可能需要较长时间
5. **文件路径**：使用路径方式时，确保文件路径可访问
6. **最终视频**：API会自动提取并返回最终生成的视频文件路径

## 故障排除

### 常见问题

1. **FFmpeg 未找到**
   - 确保 FFmpeg 已安装并在 PATH 中
   - 或在 `config.FFMPEG_PATHS` 中配置路径

2. **模型下载失败**
   - 检查网络连接
   - 或使用本地模型目录

3. **内存不足**
   - 使用更小的 Whisper 模型（tiny/base）
   - 减少并发请求数

4. **端口被占用**
   - 修改 `config.PORT` 配置
   - 或杀死占用端口的进程

5. **模型下载地址**
   - 背景移除： https://modelscope.cn/models/AI-ModelScope/RMBG-1.4/resolve/master/onnx/model.onnx
   - 语音识别：modelscope download --model angelala00/faster-whisper-small --local_dir ./dir

## 版本历史

### v3.0.0 (当前版本)
- 模块化重构，采用高内聚、低耦合架构
- 拆分配置、工具、功能、API、UI 等模块
- 新增语音合成模块（VoxCPM）
- 新增高级字幕生成模块
- 优化代码组织和可维护性
- 备份原版本为 `app_old_backup.py`

### v2.0.0
- 整合 Whisper 服务和视频转场功能
- 添加 Gradio Web 界面
- 支持 JWT 和固定 token 认证
- 添加高级字幕生成功能

### v1.0.0
- 初始版本
- 基础 Whisper 语音转文字服务
- FastAPI REST API