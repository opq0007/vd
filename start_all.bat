@echo off
echo ========================================
echo VD 服务启动脚本
echo ========================================
echo.

echo [1/3] 启动主后端服务 (端口 7860)...
start "VD Backend" cmd /k "cd /d %~dp0 && python app.py"

echo [2/3] 等待主后端服务启动...
timeout /t 5 /nobreak > nul

echo [3/3] 启动 Remotion API 服务 (端口 3001)...
cd frontend\remo-fects\api
start "Remotion API" cmd /k "npm run api"
cd ..\..\..

echo.
echo ========================================
echo 所有服务已启动！
echo ========================================
echo.
echo 主后端服务: http://localhost:7860
echo Remotion API:  http://localhost:3001
echo 前端服务:    http://localhost:3000
echo.
echo 按 Ctrl+C 停止所有服务
echo.

pause