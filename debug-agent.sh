#!/bin/bash

echo "🔍 LiveKit Voice Assistant Debugging Tool"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "\n${BLUE}=== SYSTEM STATUS ===${NC}"

# Check if services are running
echo -e "${BLUE}Checking service status...${NC}"

# LiveKit Server
if curl -s http://localhost:7880 >/dev/null 2>&1; then
    echo -e "  ✅ LiveKit Server: ${GREEN}Running${NC} (port 7880)"
else
    echo -e "  ❌ LiveKit Server: ${RED}Not running${NC} (port 7880)"
fi

# Token Server
if curl -s http://localhost:3001/health >/dev/null 2>&1; then
    echo -e "  ✅ Token Server: ${GREEN}Running${NC} (port 3001)"
else
    echo -e "  ❌ Token Server: ${RED}Not running${NC} (port 3001)"
fi

# Webhook Handler
if curl -s http://localhost:8080/health >/dev/null 2>&1; then
    echo -e "  ✅ Webhook Handler: ${GREEN}Running${NC} (port 8080)"
else
    echo -e "  ❌ Webhook Handler: ${RED}Not running${NC} (port 8080)"
fi

# Check webhook status
echo -e "\n${BLUE}=== WEBHOOK STATUS ===${NC}"
WEBHOOK_STATUS=$(curl -s http://localhost:8080/status 2>/dev/null)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Webhook Handler Response:${NC}"
    echo "$WEBHOOK_STATUS" | python3 -m json.tool 2>/dev/null || echo "$WEBHOOK_STATUS"
else
    echo -e "${RED}Cannot connect to webhook handler${NC}"
fi

# Check active agents
echo -e "\n${BLUE}=== ACTIVE AGENTS ===${NC}"
AGENT_PROCESSES=$(ps aux | grep -E "(python.*agent\.py|python.*webhook_handler\.py)" | grep -v grep)
if [ ! -z "$AGENT_PROCESSES" ]; then
    echo -e "${GREEN}Active Python processes:${NC}"
    echo "$AGENT_PROCESSES"
else
    echo -e "${YELLOW}No Python agent processes found${NC}"
fi

# Test token generation
echo -e "\n${BLUE}=== TOKEN GENERATION TEST ===${NC}"
echo -e "${BLUE}Testing token generation...${NC}"
TOKEN_RESPONSE=$(curl -s -X POST http://localhost:3001/api/token \
  -H "Content-Type: application/json" \
  -d '{"room": "debug-room", "identity": "debug-user"}' 2>/dev/null)

if echo "$TOKEN_RESPONSE" | grep -q "token"; then
    echo -e "  ✅ ${GREEN}Token generation working${NC}"
    # Pretty print the response
    echo "$TOKEN_RESPONSE" | python3 -m json.tool 2>/dev/null | head -10
    echo "  ..."
else
    echo -e "  ❌ ${RED}Token generation failed${NC}"
    echo "  Response: $TOKEN_RESPONSE"
fi

# Check LiveKit server logs
echo -e "\n${BLUE}=== LIVEKIT SERVER LOGS ===${NC}"
echo -e "${BLUE}Recent LiveKit server logs:${NC}"
cd livekit-server
docker-compose logs --tail=20 livekit 2>/dev/null || echo -e "${RED}Cannot access LiveKit logs${NC}"
cd ..

# Check environment files
echo -e "\n${BLUE}=== ENVIRONMENT CONFIGURATION ===${NC}"
echo -e "${BLUE}Checking environment files...${NC}"

if [ -f python-agent/.env ]; then
    echo -e "  ✅ python-agent/.env exists"
    # Check for API keys (without revealing them)
    if grep -q "OPENAI_API_KEY=your_" python-agent/.env; then
        echo -e "  ⚠️  ${YELLOW}OpenAI API key not configured${NC}"
    else
        echo -e "  ✅ OpenAI API key configured"
    fi
    
    if grep -q "DEEPGRAM_API_KEY=your_" python-agent/.env; then
        echo -e "  ⚠️  ${YELLOW}Deepgram API key not configured${NC}"
    else
        echo -e "  ✅ Deepgram API key configured"
    fi
else
    echo -e "  ❌ python-agent/.env missing"
fi

# Network connectivity test
echo -e "\n${BLUE}=== NETWORK CONNECTIVITY ===${NC}"
echo -e "${BLUE}Testing webhook connectivity...${NC}"

# Simulate a webhook call
WEBHOOK_TEST=$(curl -s -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_webhook_api_key" \
  -d '{
    "event": "participant_joined",
    "room": {
      "name": "debug-test-room"
    },
    "participant": {
      "identity": "debug-participant"
    }
  }' 2>/dev/null)

if [ $? -eq 0 ]; then
    echo -e "  ✅ ${GREEN}Webhook endpoint accessible${NC}"
    echo -e "  Response: $WEBHOOK_TEST"
else
    echo -e "  ❌ ${RED}Webhook endpoint not accessible${NC}"
fi

# Common issues check
echo -e "\n${BLUE}=== COMMON ISSUES CHECK ===${NC}"

# Check if Docker is running
if docker info >/dev/null 2>&1; then
    echo -e "  ✅ Docker is running"
else
    echo -e "  ❌ ${RED}Docker is not running${NC}"
fi

# Check if required Python packages are installed
cd python-agent
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
    if python -c "import livekit" 2>/dev/null; then
        echo -e "  ✅ LiveKit Python SDK installed"
    else
        echo -e "  ❌ ${RED}LiveKit Python SDK not installed${NC}"
    fi
    deactivate
else
    echo -e "  ⚠️  ${YELLOW}Python virtual environment not found${NC}"
fi
cd ..

# Debugging recommendations
echo -e "\n${BLUE}=== DEBUGGING RECOMMENDATIONS ===${NC}"

if ! curl -s http://localhost:8080/health >/dev/null 2>&1; then
    echo -e "  🔧 ${YELLOW}Start webhook handler: cd python-agent && python webhook_handler.py${NC}"
fi

if ! curl -s http://localhost:7880 >/dev/null 2>&1; then
    echo -e "  🔧 ${YELLOW}Start LiveKit server: cd livekit-server && docker-compose up${NC}"
fi

if grep -q "your_" python-agent/.env 2>/dev/null; then
    echo -e "  🔧 ${YELLOW}Configure API keys in python-agent/.env${NC}"
fi

echo -e "\n${BLUE}=== MANUAL AGENT TEST ===${NC}"
echo -e "${BLUE}To manually test the agent:${NC}"
echo -e "  1. cd python-agent"
echo -e "  2. source venv/bin/activate"
echo -e "  3. python agent.py --room debug-room"
echo -e "\n${BLUE}To monitor webhook calls:${NC}"
echo -e "  tail -f python-agent/webhook.log (if logging to file)"

echo -e "\n${GREEN}Debug complete! Check the issues above and follow the recommendations.${NC}"