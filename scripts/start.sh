#!/bin/bash

# 日程共享与会议安排工具 - 启动脚本
# 端口绑定到 0.0.0.0:2222

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
PID_DIR="$PROJECT_ROOT/.pids"

mkdir -p "$PID_DIR"

echo "=========================================="
echo "  日程共享与会议安排工具 - 启动脚本"
echo "=========================================="
echo ""

# 检查 uv 是否安装
if ! command -v uv &> /dev/null; then
    echo "错误: 未找到 uv 命令，请先安装 uv"
    echo "安装命令: pip install uv 或 curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# 检查 Node.js 和 npm 是否安装
if ! command -v node &> /dev/null; then
    echo "错误: 未找到 Node.js，请先安装 Node.js"
    exit 1
fi

# 启动后端
echo "📦 安装后端依赖..."
cd "$BACKEND_DIR"
uv sync

echo ""
echo "🚀 启动后端服务 (端口: 2222)..."
cd "$BACKEND_DIR"
uv run uvicorn app.main:app --host 0.0.0.0 --port 2222 --reload &
BACKEND_PID=$!
echo $BACKEND_PID > "$PID_DIR/backend.pid"
echo "后端服务已启动，PID: $BACKEND_PID"

# 安装前端依赖并启动
echo ""
echo "📦 安装前端依赖..."
cd "$FRONTEND_DIR"
if [ ! -d "node_modules" ]; then
    npm install
fi

echo ""
echo "🌐 启动前端服务..."
cd "$FRONTEND_DIR"
npm start &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$PID_DIR/frontend.pid"
echo "前端服务已启动，PID: $FRONTEND_PID"

echo ""
echo "=========================================="
echo "  服务启动完成！"
echo "=========================================="
echo ""
echo "后端 API:  http://0.0.0.0:2222"
echo "API 文档:  http://0.0.0.0:2222/docs"
echo "前端地址:  http://localhost:3000"
echo ""
echo "停止服务:  ./scripts/stop.sh"
echo "查看状态:  ./scripts/status.sh"
echo ""
