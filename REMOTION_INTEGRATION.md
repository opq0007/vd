# Remotion 工作室集成方案

## 方案概述

采用**独立服务 + 前端代理**的集成方案，将 `remo-fects/api` 作为独立的后端服务运行，前端通过 Vite 代理访问。

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                        前端层 (React)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Pages   │  │Components│  │ Services │  │  Store   │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    Vite 开发服务器 (3000)                │
│  ┌──────────────────────────────────────────────────┐  │
│  │  代理配置:                                        │  │
│  │  /api/* → http://localhost:7860/api/*          │  │
│  │  /remotion/* → http://localhost:3001/api/*      │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌─────────────────────────┐  ┌─────────────────────────┐
│   主后端服务 (7860)     │  │  Remotion API (3001)    │
│  ┌──────────────────┐   │  │  ┌──────────────────┐   │
│  │  FastAPI Routes │   │  │  │  Express Server  │   │
│  │  - /api/*        │   │  │  │  - /api/projects │   │
│  │  - /comfyui/*    │   │  │  │  - /api/render   │   │
│  │  - /templates/*  │   │  │  │  - /api/compose  │   │
│  │  - /batch/*      │   │  │  │  - /api/jobs     │   │
│  └──────────────────┘   │  │  └──────────────────┘   │
└─────────────────────────┘  └─────────────────────────┘
```

## 优势

1. **保持独立性**：remo-fects 项目完全独立，可以单独更新和维护
2. **简化集成**：无需修改 remo-fects 源码，通过代理即可访问
3. **降低复杂度**：避免了 Python 调用 Node.js 的跨语言复杂性
4. **易于调试**：两个服务独立运行，问题定位更清晰
5. **灵活部署**：可以独立部署 Remotion 服务到不同服务器

## 启动步骤

### 方式一：使用一键启动脚本

```bash
# Windows
start_all.bat
```

### 方式二：手动启动

**1. 启动主后端服务**
```bash
cd D:\workspace\c\ai\iflow\vd
python app.py
```

**2. 启动 Remotion API 服务**
```bash
cd D:\workspace\c\ai\iflow\vd\frontend\remo-fects\api
npm install
npm run api
```

**3. 启动前端服务**
```bash
cd D:\workspace\c\ai\iflow\vd\frontend
npm install
npm run dev
```

## 配置说明

### 前端代理配置

```typescript
// frontend/vite.config.ts
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:7860',
      changeOrigin: true,
    },
    '/remotion': {
      target: 'http://localhost:3001',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/remotion/, '/api'),
    },
  },
}
```

### Remotion API 配置

```typescript
// frontend/src/services/remotionApi.ts
baseURL: '/remotion'
```

## API 端点映射

| 前端请求 | 代理转发 | Remotion API |
|---------|---------|-------------|
| `/remotion/projects` | → | `http://localhost:3001/api/projects` |
| `/remotion/render/:id` | → | `http://localhost:3001/api/render/:id` |
| `/remotion/compose` | → | `http://localhost:3001/api/compose` |
| `/remotion/jobs/:id` | → | `http://localhost:3001/api/jobs/:id` |
| `/remotion/download/:id` | → | `http://localhost:3001/api/download/:id` |

## 文件结构

```
vd/
├── app.py                          # 主后端服务
├── api/
│   └── routes.py                   # 主后端路由（已移除 Remotion 路由）
├── frontend/
│   ├── vite.config.ts              # Vite 配置（添加 Remotion 代理）
│   ├── src/
│   │   ├── pages/
│   │   │   └── RemotionStudio.tsx  # Remotion 工作室页面
│   │   ├── services/
│   │   │   └── remotionApi.ts      # Remotion API 客户端
│   │   └── components/
│   │       └── RemotionEffects/    # Remotion 组件
│   │           ├── EffectSelector.tsx
│   │           ├── EffectConfig.tsx
│   │           └── EffectRender.tsx
│   └── remo-fects/
│       └── api/                    # 独立的 Remotion API 服务
│           ├── server.js
│           ├── render.js
│           ├── package.json
│           └── effect-configs/
└── start_all.bat                    # 一键启动脚本
```

## 使用示例

### 前端调用

```typescript
import { remotionApi } from '../services/remotionApi'

// 获取项目列表
const projects = await remotionApi.getProjects()

// 创建渲染任务
const result = await remotionApi.createRenderJob('text-rain-effect', {
  words: ['福', '禄', '寿'],
  duration: 10,
  width: 720,
  height: 1280,
  fps: 24,
})

// 查询任务状态
const job = await remotionApi.getJobStatus(result.jobId)

// 下载视频
const blob = await remotionApi.downloadJobOutput(result.jobId)
```

## 故障排查

### Remotion API 无法访问

1. 检查服务是否启动：`http://localhost:3001/api/projects`
2. 检查端口是否被占用：`netstat -ano | findstr :3001`
3. 检查代理配置是否正确

### 前端请求 404

1. 检查 Vite 代理配置
2. 检查 baseURL 是否为 `/remotion`
3. 检查 Remotion API 服务是否正常

### 渲染失败

1. 检查 Node.js 版本（需要 >= 18.0.0）
2. 检查 FFmpeg 是否安装
3. 查看 Remotion API 服务日志

## 注意事项

1. **服务依赖**：Remotion API 服务必须先启动，前端才能正常调用
2. **端口冲突**：确保端口 3001 未被占用
3. **文件路径**：Remotion API 的输出文件保存在 `frontend/remo-fects/api/outputs/`
4. **跨域问题**：Vite 代理已处理跨域，无需额外配置

## 更新维护

### 更新 remo-fects 项目

```bash
cd frontend/remo-fects
git pull
cd api
npm install
```

### 更新前端组件

直接修改 `frontend/src/components/RemotionEffects/` 下的组件即可。

## 总结

这个方案通过**独立服务 + 前端代理**的方式，实现了：
- ✅ 保持 remo-fects 项目的独立性
- ✅ 简化集成复杂度
- ✅ 降低维护成本
- ✅ 提高开发效率
- ✅ 便于问题排查

相比之前的 Python 调用 Node.js 方案，这个方案更加合理和实用。