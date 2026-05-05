@echo off
REM VD 项目部署脚本 - React + FastAPI 版本 (Windows)

echo =========================================
echo VD 项目部署脚本
echo =========================================

REM 检查 Docker 是否安装
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker 未安装，请先安装 Docker
    exit /b 1
)

REM 构建镜像
echo 📦 构建 Docker 镜像...
docker build -f Dockerfile.react -t vd-service:latest .

if %errorlevel% neq 0 (
    echo ❌ 镜像构建失败
    exit /b 1
)

REM 运行容器
echo 🚀 启动容器...
docker run -d ^
    --name vd-service ^
    -p 7860:7860 ^
    -e API_TOKEN=opq#key ^
    -e SECRET_KEY=your-secret-key-change-in-production ^
    -e ENABLE_GRADIO_UI=false ^
    -e LOG_LEVEL=INFO ^
    vd-service:latest

if %errorlevel% neq 0 (
    echo ❌ 容器启动失败
    exit /b 1
)

echo ✅ 部署完成！
echo 🌐 访问地址: http://localhost:7860
echo 📚 API 文档: http://localhost:7860/docs
echo.
echo 查看日志: docker logs -f vd-service
echo 停止服务: docker stop vd-service
echo 删除容器: docker rm vd-service

pause