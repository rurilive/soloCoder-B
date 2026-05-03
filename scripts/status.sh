#!/bin/bash

# 日程共享与会议安排工具 - 状态检查脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_DIR="$PROJECT_ROOT/.pids"

echo "=========================================="
echo "  日程共享与会议安排工具 - 状态检查"
echo "=========================================="
echo ""

check_service() {
    local pid_file="$1"
    local service_name="$2"
    local port="$3"
    
    echo "[$service_name]"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "  状态: 运行中 (PID: $pid)"
            if [ -n "$port" ]; then
                local port_used=$(lsof -i :$port 2>/dev/null | grep LISTEN)
                if [ -n "$port_used" ]; then
                    echo "  端口 $port: 已监听"
                else
                    echo "  端口 $port: 未监听"
                fi
            fi
        else
            echo "  状态: 进程不存在 (PID 文件存在但进程已结束)"
        fi
    else
        echo "  状态: 未运行"
    fi
    echo ""
}

check_service "$PID_DIR/backend.pid" "后端服务 (FastAPI)" "2222"
check_service "$PID_DIR/frontend.pid" "前端服务 (React)" "3000"

echo "=========================================="
echo ""
echo "使用说明:"
echo "  启动服务: ./scripts/start.sh"
echo "  停止服务: ./scripts/stop.sh"
echo ""
