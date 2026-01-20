#!/bin/bash

echo "Starting Integrated Whisper Service..."
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Start the service
echo
echo "========================================"
echo "🎙️ 整合版 Whisper 语音转文字服务"
echo "========================================"
echo "🌐 服务地址: http://localhost:7860"
echo "📚 API文档: http://localhost:7860/docs"

# Check if Gradio UI is enabled
if [ "$ENABLE_GRADIO_UI" = "false" ]; then
    echo "📱 运行模式: API 专用模式 (Gradio UI 已禁用)"
else
    echo "📱 Gradio界面: http://localhost:7860/ui"
    echo "📱 运行模式: 完整模式 (Gradio UI 已启用)"
fi

echo "========================================"
echo
echo "Starting service..."
python app.py
