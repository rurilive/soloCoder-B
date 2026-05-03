#!/bin/bash

# 日程共享与会议安排工具 - 重启脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  日程共享与会议安排工具 - 重启脚本"
echo "=========================================="
echo ""

# 停止服务
echo "正在停止现有服务..."
"$SCRIPT_DIR/stop.sh"

# 等待片刻
sleep 2

# 启动服务
echo "正在启动服务..."
"$SCRIPT_DIR/start.sh"
