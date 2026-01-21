@echo off
echo Starting Integrated Whisper Service...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install dependencies if needed
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Start the service
echo.
echo ========================================
echo 🎙️ 整合版 Whisper 语音转文字服务
echo ========================================
echo 🌐 服务地址: http://localhost:7860
echo 📚 API文档: http://localhost:7860/docs

REM Check if Gradio UI is enabled
if "%ENABLE_GRADIO_UI%"=="false" (
    echo 📱 运行模式: API 专用模式 (Gradio UI 已禁用)
) else (
    echo 📱 Gradio界面: http://localhost:7860/ui
    echo 📱 运行模式: 完整模式 (Gradio UI 已启用)
)

echo ========================================
echo.
echo Starting service...
python app.py

pause
