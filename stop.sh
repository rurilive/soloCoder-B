#!/bin/bash

cd "$(dirname "$0")"

PID_FILE=".server.pid"
PORT=2222

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping server (PID: $PID)..."
        kill "$PID"
        
        for i in {1..10}; do
            if ! kill -0 "$PID" 2>/dev/null 2>&1; then
                echo "Server stopped successfully"
                rm -f "$PID_FILE"
                exit 0
            fi
            sleep 0.5
        done
        
        echo "Server did not stop gracefully, force killing..."
        kill -9 "$PID"
        rm -f "$PID_FILE"
        echo "Server force stopped"
    else
        echo "Server not running (stale PID file removed)"
        rm -f "$PID_FILE"
    fi
else
    echo "Server PID file not found. Trying to find by port/process name..."
    
    PIDS=$(pkill -f "backend.server" 2>&1)
    if [ $? -eq 0 ]; then
        echo "Killed processes matching 'backend.server'"
    else
        PIDS=$(lsof -i :$PORT -t 2>/dev/null)
        if [ -n "$PIDS" ]; then
            echo "Killing processes on port $PORT: $PIDS"
            kill $PIDS 2>/dev/null || kill -9 $PIDS 2>/dev/null
        else
            echo "No server process found"
        fi
    fi
fi
