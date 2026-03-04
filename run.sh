#!/bin/bash
# 启动 Seedance Video Generator 前后端

cd "$(dirname "$0")"

# 颜色
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}启动后端 (FastAPI :8000)...${NC}"
uvicorn backend.main:app --port 8000 --reload &
BACKEND_PID=$!

echo -e "${GREEN}启动前端 (Next.js :3000)...${NC}"
cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  后端: http://localhost:8000${NC}"
echo -e "${GREEN}  前端: http://localhost:3000${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "按 Ctrl+C 停止所有服务"

cleanup() {
    echo ""
    echo "正在停止服务..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "已停止"
}

trap cleanup EXIT INT TERM
wait
