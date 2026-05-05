# VD Frontend

基于 React + TypeScript + Vite 的现代化前端应用。

## 技术栈

- React 18
- TypeScript
- Vite
- Ant Design
- React Router
- Zustand (状态管理)
- Remotion (视频处理)

## 开发

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 类型检查
npm run type-check

# 代码检查
npm run lint
```

## 构建

```bash
# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## 环境变量

创建 `.env.local` 文件配置环境变量：

```env
VITE_API_BASE_URL=/api
VITE_APP_TITLE=VD - 视频处理服务
```

## 项目结构

```
src/
├── components/     # 通用组件
├── pages/         # 页面组件
├── services/      # API服务
├── hooks/         # 自定义Hooks
├── store/         # 状态管理
├── types/         # TypeScript类型
├── utils/         # 工具函数
├── styles/        # 样式文件
└── remotion/      # Remotion视频组件
```