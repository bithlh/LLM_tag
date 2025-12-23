#!/bin/bash

# 生产环境启动脚本
echo "=========================================="
echo "🚀 LLM标签筛选系统 - 生产环境启动脚本"
echo "=========================================="

# 设置环境变量
export FLASK_ENV=production
export PYTHONPATH=$(pwd)

# 创建日志目录
mkdir -p logs

# 激活虚拟环境（如果存在）
if [ -f "venv/bin/activate" ]; then
    echo "✓ 激活虚拟环境..."
    source venv/bin/activate
elif [ -f "env/bin/activate" ]; then
    echo "✓ 激活虚拟环境..."
    source env/bin/activate
fi

# 检查依赖是否安装
echo "✓ 检查依赖..."
pip install -r requirements.txt

# 创建必要的目录
mkdir -p data static/images

# 使用Flask生产服务器启动服务（单进程模式）
echo "✓ 启动Flask生产服务器..."
echo "  - 绑定地址: 0.0.0.0:8000"
echo "  - 工作进程: 1 (单进程模式)"
echo "  - 文件锁保护: 已启用"
echo ""

python -c "from app import create_app; import os; os.environ['FLASK_ENV'] = 'production'; app = create_app(); app.run(host='0.0.0.0', port=8000, debug=False, threaded=True, processes=1)"

echo "=========================================="
echo "✓ 服务已停止"
echo "=========================================="
