@echo off
chcp 65001 >nul
echo ========================================
echo   SSM RAG Assistant - 启动脚本
echo   Python版本 (无需JDK 11+)
echo ========================================
echo.

echo [1/5] 检查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python！请先安装 Python 3.9+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version

echo.
echo [2/5] 创建虚拟环境...
if not exist "venv" (
    python -m venv venv
    echo 虚拟环境已创建
) else (
    echo 虚拟环境已存在
)

echo.
echo [3/5] 激活虚拟环境并安装依赖...
call venv\Scripts\activate.bat
pip install -r requirements.txt -q

echo.
echo [4/5] 创建配置文件...
if not exist ".env" (
    copy .env.example .env >nul
    echo 配置文件已创建
) else (
    echo 配置文件已存在
)

echo.
echo [5/5] 创建项目文件目录...
if not exist "project-files" (
    mkdir project-files
    echo 项目文件目录已创建: project-files
    echo.
    echo 请将您的 SSM 项目文件复制到 project-files 目录中
) else (
    echo 项目文件目录已存在
)

echo.
echo ========================================
echo   环境准备完成！
echo ========================================
echo.
echo 接下来请确保以下服务已启动:
echo.
echo   1. Ollama (http://localhost:11434)
echo      安装: https://ollama.ai
echo      运行: ollama serve
echo      拉取模型: ollama pull qwen2.5-coder:7b
echo.
echo   2. ChromaDB (http://localhost:8000)
echo      运行: docker run -d -p 8000:8000 chromadb/chroma
echo.
echo 启动应用:
echo   run.bat
echo.
echo 访问地址:
echo   http://localhost:8080
echo.
pause
