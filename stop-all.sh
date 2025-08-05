#!/bin/bash

echo "🛑 Stopping LiveKit Voice Assistant System..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Stop Python Agent processes
echo -e "${BLUE}Stopping Python agents...${NC}"
pkill -f "python.*agent.py" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Python agents stopped${NC}"
else
    echo -e "${YELLOW}No Python agents found running${NC}"
fi

# Stop Webhook Handler
echo -e "${BLUE}Stopping Webhook Handler...${NC}"
if [ -f python-agent/.webhook_pid ]; then
    WEBHOOK_PID=$(cat python-agent/.webhook_pid)
    kill $WEBHOOK_PID 2>/dev/null
    rm python-agent/.webhook_pid
    echo -e "${GREEN}✅ Webhook handler stopped (PID: $WEBHOOK_PID)${NC}"
else
    pkill -f "python.*webhook_handler.py" 2>/dev/null
    echo -e "${YELLOW}Webhook handler stopped (no PID file found)${NC}"
fi

# Stop Token Server
echo -e "${BLUE}Stopping Token Server...${NC}"
if [ -f token-server/.token_server_pid ]; then
    TOKEN_PID=$(cat token-server/.token_server_pid)
    kill $TOKEN_PID 2>/dev/null
    rm token-server/.token_server_pid
    echo -e "${GREEN}✅ Token server stopped (PID: $TOKEN_PID)${NC}"
else
    pkill -f "node.*index.js" 2>/dev/null
    echo -e "${YELLOW}Token server stopped (no PID file found)${NC}"
fi

# Stop LiveKit Server
echo -e "${BLUE}Stopping LiveKit Server...${NC}"
cd livekit-server
docker-compose down
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ LiveKit server stopped${NC}"
else
    echo -e "${RED}❌ Failed to stop LiveKit server${NC}"
fi
cd ..

# Kill any remaining processes on our ports
echo -e "${BLUE}Cleaning up any remaining processes...${NC}"
for port in 7880 7881 3001 8080; do
    PID=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$PID" ]; then
        kill -9 $PID 2>/dev/null
        echo -e "${YELLOW}Killed process on port $port (PID: $PID)${NC}"
    fi
done

echo -e "\n${GREEN}🎉 All services stopped!${NC}"