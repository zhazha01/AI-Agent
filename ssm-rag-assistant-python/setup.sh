#!/bin/bash

echo "========================================"
echo "  SSM RAG Assistant - 启动脚本"
echo "  Python版本 (无需JDK 11+)"
echo "========================================"
echo

echo "[1/5] 检查 Python..."
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python！请先安装 Python 3.9+"
    exit 1
fi
python3 --version

echo
echo "[2/5] 创建虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "虚拟环境已创建"
else
    echo "虚拟环境已存在"
fi

echo
echo "[3/5] 激活虚拟环境并安装依赖..."
source venv/bin/activate
pip install -r requirements.txt -q

echo
echo "[4/5] 创建配置文件..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "配置文件已创建"
else
    echo "配置文件已存在"
fi

echo
echo "[5/5] 创建项目文件目录..."
if [ ! -d "project-files" ]; then
    mkdir -p project-files
    echo "项目文件目录已创建: project-files"
    echo
    echo "请将您的 SSM 项目文件复制到 project-files 目录中"
else
    echo "项目文件目录已存在"
fi

echo
echo "========================================"
echo "  环境准备完成！"
echo "========================================"
echo
echo "接下来请确保以下服务已启动:"
echo
echo "  1. Ollama (http://localhost:11434)"
echo "     安装: https://ollama.ai"
echo "     运行: ollama serve"
echo "     拉取模型: ollama pull qwen2.5-coder:7b"
echo
echo "  2. ChromaDB (http://localhost:8000)"
echo "     运行: docker run -d -p 8000:8000 chromadb/chroma"
echo
echo "启动应用:"
echo "   ./run.sh"
echo
echo "访问地址:"
echo "   http://localhost:8080"
echo
