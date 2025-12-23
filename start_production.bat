@echo off
REM 生产环境启动脚本 (Windows)
echo ==========================================
echo 🚀 LLM标签筛选系统 - 生产环境启动脚本
echo ==========================================

REM 设置环境变量
set FLASK_ENV=production
set PYTHONPATH=%CD%

REM 创建日志目录
if not exist logs mkdir logs

REM 激活虚拟环境（如果存在）
if exist venv\Scripts\activate.bat (
    echo ✓ 激活虚拟环境...
    call venv\Scripts\activate.bat
) else if exist env\Scripts\activate.bat (
    echo ✓ 激活虚拟环境...
    call env\Scripts\activate.bat
)

REM 检查依赖是否安装
echo ✓ 检查依赖...
pip install -r requirements.txt

REM 创建必要的目录
if not exist data mkdir data
if not exist static\images mkdir static\images

REM 使用Flask生产服务器启动服务（单进程模式）
echo ✓ 启动Flask生产服务器...
echo   - 绑定地址: 0.0.0.0:8000
echo   - 工作进程: 1 (单进程模式)
echo   - 文件锁保护: 已启用
echo.

python -c "from app import create_app; import os; os.environ['FLASK_ENV'] = 'production'; app = create_app(); app.run(host='0.0.0.0', port=8000, debug=False, threaded=True, processes=1)"

echo ==========================================
echo ✓ 服务已停止
echo ==========================================

pause
