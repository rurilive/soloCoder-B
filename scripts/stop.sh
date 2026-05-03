#!/bin/bash

# 日程共享与会议安排工具 - 停止脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_DIR="$PROJECT_ROOT/.pids"

echo "=========================================="
echo "  日程共享与会议安排工具 - 停止脚本"
echo "=========================================="
echo ""

kill_process() {
    local pid_file="$1"
    local service_name="$2"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            kill -TERM "$pid" 2>/dev/null || true
            if ps -p "$pid" > /dev/null 2>&1; then
                sleep 1
                if ps -p "$pid" > /dev/null 2>&1; then
                    kill -9 "$pid" 2>/dev/null || true
                fi
            fi
            echo "✓ $service_name 已停止 (PID: $pid)"
        else
            echo "⚠ $service_name 进程不存在"
        fi
        rm -f "$pid_file"
    else
        echo "⚠ $service_name PID 文件不存在"
    fi
}

# 停止前端
kill_process "$PID_DIR/frontend.pid" "前端服务"

# 停止后端
kill_process "$PID_DIR/backend.pid" "后端服务"

# 清理 PID 目录
rm -rf "$PID_DIR"

echo ""
echo "=========================================="
echo "  所有服务已停止"
echo "=========================================="
echo ""
