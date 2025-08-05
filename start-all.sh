#!/bin/bash

echo "🚀 Starting LiveKit Voice Assistant System..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${YELLOW}Port $1 is already in use${NC}"
        return 0
    else
        return 1
    fi
}

# Function to wait for service
wait_for_service() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${BLUE}Waiting for $name to start...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $name is ready!${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}Attempt $attempt/$max_attempts - waiting for $name...${NC}"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}❌ $name failed to start within expected time${NC}"
    return 1
}

# Create .env files if they don't exist
echo -e "${BLUE}📝 Setting up environment files...${NC}"

if [ ! -f python-agent/.env ]; then
    cp python-agent/.env.example python-agent/.env
    echo -e "${YELLOW}Created python-agent/.env - please update with your API keys${NC}"
fi

if [ ! -f token-server/.env ]; then
    cat > token-server/.env << EOF
LIVEKIT_API_KEY=APIyourkey
LIVEKIT_API_SECRET=yoursecret
PORT=3001
EOF
    echo -e "${GREEN}Created token-server/.env${NC}"
fi

# Step 1: Start LiveKit Server
echo -e "\n${BLUE}🔧 Step 1: Starting LiveKit Server...${NC}"
cd livekit-server
if check_port 7880; then
    echo -e "${YELLOW}LiveKit server appears to be running already${NC}"
else
    docker-compose up -d
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ LiveKit server started${NC}"
    else
        echo -e "${RED}❌ Failed to start LiveKit server${NC}"
        exit 1
    fi
fi
cd ..

# Wait for LiveKit server
wait_for_service "http://localhost:7880" "LiveKit Server"

# Step 2: Start Token Server
echo -e "\n${BLUE}🔧 Step 2: Starting Token Server...${NC}"
cd token-server
if check_port 3001; then
    echo -e "${YELLOW}Token server appears to be running already${NC}"
else
    npm install > /dev/null 2>&1
    npm start &
    TOKEN_SERVER_PID=$!
    echo "Token server PID: $TOKEN_SERVER_PID" > .token_server_pid
    echo -e "${GREEN}✅ Token server started (PID: $TOKEN_SERVER_PID)${NC}"
fi
cd ..

# Wait for Token server
wait_for_service "http://localhost:3001/health" "Token Server"

# Step 3: Start Webhook Handler
echo -e "\n${BLUE}🔧 Step 3: Starting Webhook Handler...${NC}"
cd python-agent
if check_port 8080; then
    echo -e "${YELLOW}Webhook handler appears to be running already${NC}"
else
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo -e "${BLUE}Creating Python virtual environment...${NC}"
        python3 -m venv venv
    fi
    
    # Activate virtual environment and install dependencies
    source venv/bin/activate
    pip install -r requirements.txt > /dev/null 2>&1
    
    # Start webhook handler
    python webhook_handler.py &
    WEBHOOK_PID=$!
    echo "Webhook handler PID: $WEBHOOK_PID" > .webhook_pid
    echo -e "${GREEN}✅ Webhook handler started (PID: $WEBHOOK_PID)${NC}"
fi
cd ..

# Wait for Webhook handler
wait_for_service "http://localhost:8080/health" "Webhook Handler"

echo -e "\n${GREEN}🎉 All services are running!${NC}"
echo -e "\n${BLUE}📊 Service Status:${NC}"
echo -e "  • LiveKit Server: http://localhost:7880"
echo -e "  • Token Server: http://localhost:3001"
echo -e "  • Webhook Handler: http://localhost:8080"

echo -e "\n${BLUE}🔍 Testing Setup:${NC}"
echo -e "${YELLOW}Testing token generation...${NC}"
TOKEN_RESPONSE=$(curl -s -X POST http://localhost:3001/api/token \
  -H "Content-Type: application/json" \
  -d '{"room": "test-room", "identity": "test-user"}')

if echo "$TOKEN_RESPONSE" | grep -q "token"; then
    echo -e "${GREEN}✅ Token generation working${NC}"
else
    echo -e "${RED}❌ Token generation failed${NC}"
    echo "Response: $TOKEN_RESPONSE"
fi

echo -e "\n${BLUE}📱 Next Steps:${NC}"
echo -e "1. Update python-agent/.env with your OpenAI and Deepgram API keys"
echo -e "2. For React Native app:"
echo -e "   cd react-native-app"
echo -e "   npm install"
echo -e "   npx react-native run-android (or run-ios)"
echo -e "\n${BLUE}🛑 To stop all services, run: ./stop-all.sh${NC}"