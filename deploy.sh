#!/bin/bash

# VD 项目部署脚本 - React + FastAPI 版本

set -e

echo "========================================="
echo "VD 项目部署脚本"
echo "========================================="

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 构建镜像
echo "📦 构建 Docker 镜像..."
docker build -f Dockerfile.react -t vd-service:latest .

# 运行容器
echo "🚀 启动容器..."
docker run -d \
    --name vd-service \
    -p 7860:7860 \
    -e API_TOKEN=opq#key \
    -e SECRET_KEY=your-secret-key-change-in-production \
    -e ENABLE_GRADIO_UI=false \
    -e LOG_LEVEL=INFO \
    vd-service:latest

echo "✅ 部署完成！"
echo "🌐 访问地址: http://localhost:7860"
echo "📚 API 文档: http://localhost:7860/docs"
echo ""
echo "查看日志: docker logs -f vd-service"
echo "停止服务: docker stop vd-service"
echo "删除容器: docker rm vd-service"