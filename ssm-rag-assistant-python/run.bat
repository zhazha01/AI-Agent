@echo off
chcp 65001 >nul
echo ========================================
echo   SSM RAG Assistant - 启动应用
echo ========================================
echo.

call venv\Scripts\activate.bat

echo 启动 FastAPI 服务...
echo.
echo 访问地址: http://localhost:8080
echo API 文档: http://localhost:8080/docs
echo.
echo 按 Ctrl+C 停止服务
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
