#!/bin/bash

cd "$(dirname "$0")"

PORT=2222
PID_FILE=".server.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Server is already running (PID: $PID)"
        echo "Access: http://localhost:$PORT"
        exit 0
    else
        rm "$PID_FILE"
    fi
fi

echo "Starting Low-Code Platform server..."
echo "Port: $PORT"
echo "Access: http://localhost:$PORT"
echo ""

uv run python -c "from backend.server import main; main()" &
PID=$!

echo "$PID" > "$PID_FILE"

echo "Server started (PID: $PID)"
echo "Use ./stop.sh to stop the server"
