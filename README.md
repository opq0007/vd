# Whisper 语音转文字服务
![图片](./ui.png)
基于 faster-whisper 和 FastAPI 的高性能语音转文字 API 服务，提供现代化 Web 界面和完整的 RESTful API。

## 功能特性

- ⚡ **高性能** - 基于 FastAPI，异步处理，性能优越
- 🔄 **模型复用** - 单例模式，避免重复加载模型
- 🔐 **JWT 身份验证** - 安全的 token 认证机制
- 🌐 **RESTful API** - 标准化 API 接口，自动生成文档
- 💻 **现代化界面** - 响应式 Web 界面，支持拖拽上传
- 📁 **文件管理** - 自动清理临时文件
- ⚙️ **参数配置** - 支持自定义转录参数
- 🚀 **一键启动** - 跨平台启动脚本

## 快速开始

### 方式一：使用一键启动脚本

**Windows 平台:**
```bash
# 双击运行或在命令行执行
start_windows.bat
```

**Linux/macOS 平台:**
```bash
# 添加执行权限
chmod +x start_linux.sh

# 运行脚本
./start_linux.sh
```

### 方式二：手动启动

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **启动服务**
   ```bash
   python api_server.py
   ```

服务将在 `http://localhost:5000` 启动。

## 默认账号

- 管理员账号: `admin` / `admin123`
- 普通用户账号: `user` / `user123`

## 服务地址

- **Web 界面**: http://localhost:5000
- **API 文档**: http://localhost:5000/docs (Swagger UI)
- **ReDoc 文档**: http://localhost:5000/redoc

## API 接口

### 登录获取 Token
```http
POST /api/login
Content-Type: application/json

{
    "username": "admin",
    "password": "admin123"
}
```

### 固定 API Token（用于自动化调用）

除了登录获取的 JWT token 外，还支持固定 token 用于自动化调用：

```http
# 使用固定 token
Authorization: Bearer whisper-api-key-2024
```

可用的固定 token：
- `whisper-api-key-2024` - 自动化调用
- `test-token` - 测试用途

### 获取模型信息
```http
GET /api/model/info
Authorization: Bearer <token>
```

### 语音转文字
```http
POST /api/transcribe
Authorization: Bearer <token>
Content-Type: multipart/form-data

audio: <音频文件>
beam_size: 5 (可选)
```

### 健康检查
```http
GET /api/health
```

## 使用说明

1. 启动服务后，访问 `http://localhost:5000`
2. 使用默认账号登录
3. 上传音频文件（支持拖拽）
4. 调整参数（可选）
5. 点击"开始转录"按钮
6. 查看转录结果

## 文件结构

```
whisper/
├── api_server.py        # FastAPI 服务器
├── whisper_service.py   # Whisper 服务类
├── index.html          # Web 界面
├── requirements.txt    # 依赖包列表
├── start_windows.bat   # Windows 启动脚本
├── start_linux.sh      # Linux/macOS 启动脚本
└── README.md          # 说明文档
```

## 性能优势

- **FastAPI**: 相比 Flask 性能提升 2-3 倍
- **异步处理**: 支持并发请求，提高吞吐量
- **自动文档**: 无需手动维护 API 文档
- **类型检查**: 减少运行时错误

## 系统要求

- Python 3.8+
- 至少 4GB RAM（推荐 8GB+）
- 支持的音频格式：MP3, WAV, M4A, FLAC 等

## 注意事项

- 首次运行时会自动下载 Whisper 模型（约 150MB），需要网络连接
- 音频文件大小限制为 50MB
- 上传的文件会在转录完成后自动删除
- 生产环境请修改 `SECRET_KEY` 并使用更安全的认证方式
- Linux/macOS 用户需要给 `start_linux.sh` 添加执行权限

## 故障排除

1. **模型下载失败**: 检查网络连接，或手动下载模型文件
2. **内存不足**: 尝试使用更小的模型（如 `tiny` 或 `base`）
3. **端口被占用**: 修改 `api_server.py` 中的端口号
4. **依赖安装失败**: 尝试升级 pip：`pip install --upgrade pip`

## 开发说明

如需自定义配置，可修改 `whisper_service.py` 中的以下参数：
- `model_size`: 模型大小（tiny, base, small, medium, large）
- `device`: 计算设备（cpu, cuda）
- `compute_type`: 计算类型（int8, float16, float32）