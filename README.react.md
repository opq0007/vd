# VD - 视频处理服务 (React + FastAPI 版本)

基于 React + FastAPI + Remotion 的现代化视频处理平台。

## 🚀 快速开始

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- Node.js 18+ (本地开发)

### 一键部署

#### Linux/Mac

```bash
chmod +x deploy.sh
./deploy.sh
```

#### Windows

```bash
deploy.bat
```

#### Docker Compose

```bash
docker-compose up -d
```

### 本地开发

#### 后端开发

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 启动 FastAPI 服务
python app.py
```

#### 前端开发

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

## 📁 项目结构

```
vd/
├── frontend/              # React 前端
│   ├── src/
│   │   ├── components/    # 通用组件
│   │   ├── pages/         # 页面组件
│   │   ├── services/      # API 服务
│   │   ├── hooks/         # 自定义 Hooks
│   │   ├── store/         # 状态管理
│   │   ├── types/         # TypeScript 类型
│   │   ├── utils/         # 工具函数
│   │   ├── styles/        # 样式文件
│   │   └── remotion/      # Remotion 视频组件
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── api/                   # FastAPI 路由
├── modules/               # 业务逻辑模块
├── utils/                 # 工具类
├── config.py              # 配置文件
├── app.py                 # FastAPI 应用入口
├── Dockerfile.react       # Docker 镜像
├── docker-compose.yml     # Docker Compose 配置
└── deploy.sh              # 部署脚本
```

## 🔧 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `API_TOKEN` | API 认证令牌 | `opq#key` |
| `SECRET_KEY` | JWT 加密密钥 | `your-secret-key` |
| `ENABLE_GRADIO_UI` | 启用 React UI | `false` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `FW_MODEL` | Whisper 模型 | `small` |
| `FW_DEVICE` | 计算设备 | `cpu` |
| `FW_COMPUTE` | 计算类型 | `int8` |

### 前端环境变量

创建 `frontend/.env.local` 文件：

```env
VITE_API_BASE_URL=/api
VITE_APP_TITLE=VD - 视频处理服务
```

## 🎯 功能特性

### 已实现功能

- ✅ 用户认证（JWT）
- ✅ 模板管理
- ✅ 邮件发送
- ✅ 文件持久化
- ✅ Remotion 视频工作室
- ✅ 响应式设计
- ✅ 暗色主题支持

### 待迁移功能

- ⏳ 语音合成 (TTS)
- ⏳ 字幕生成
- ⏳ 图像处理
- ⏳ 视频编辑
- ⏳ 视频转场
- ⏳ 视频合并
- ⏳ 综合处理
- ⏳ ComfyUI 集成
- ⏳ HTTP 集成

## 📊 技术栈

### 前端

- React 18
- TypeScript
- Vite
- Ant Design
- React Router
- Zustand
- Remotion

### 后端

- FastAPI
- Python 3.10
- Uvicorn
- Pydantic
- PyJWT

### 基础设施

- Docker
- Nginx
- FFmpeg

## 🌐 访问地址

- **Web 界面**: http://localhost:7860
- **API 文档**: http://localhost:7860/docs
- **ReDoc 文档**: http://localhost:7860/redoc

## 📝 开发指南

### 添加新页面

1. 在 `frontend/src/pages/` 创建页面组件
2. 在 `frontend/src/App.tsx` 添加路由
3. 在 `frontend/src/components/Layout.tsx` 添加菜单项

### 添加新 API

1. 在 `api/` 目录创建路由文件
2. 在 `api/__init__.py` 注册路由
3. 在 `frontend/src/services/` 创建 API 客户端

### 添加 Remotion 组件

1. 在 `frontend/src/remotion/` 创建组件
2. 在 `frontend/src/pages/RemotionStudio.tsx` 集成

## 🐛 故障排除

### 前端构建失败

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

### 后端启动失败

```bash
pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

### Docker 构建失败

```bash
docker system prune -a
docker build -f Dockerfile.react -t vd-service:latest .
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！