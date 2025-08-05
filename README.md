# LiveKit Voice Assistant System

A complete real-time voice assistant system using LiveKit, React Native, and Python with AI integration.

## Architecture

```
┌──────────────────────────────┐
│     React Native App        │
│ ┌─────────────────────────┐ │
│ │  Mic → AudioTrack       │ │
│ │  ↳ LiveKitRoom (Client) │ │
│ │  ↳ DataTrack (Chat)     │ │
│ │  ↳ useVoiceAssistant    │ │
│ │  ↳ useTrackTranscription│ │
│ └─────────────────────────┘ │
│       🔁 Audio + Text        │
└─────────────▲────────────────┘
              │ WebRTC (SFU)
              ▼
┌──────────────────────────────┐
│        LiveKit Server        │
│ ┌──────────────────────────┐ │
│ │ SFU: Forward Audio/Video │ │
│ │ Transcription (Whisper)  │ │
│ │ DataTrack Relay          │ │
│ └──────────────────────────┘ │
│       🔁 Audio + Data         │
└─────────────▲────────────────┘
              │ gRPC / REST / Events
              ▼
┌──────────────────────────────┐
│      Python Agent Server     │
│ ┌──────────────────────────┐ │
│ │ Receive Audio (via Egress│ │
│ │ or WebRTC/WHIP/RTMP)     │ │
│ │ ↳ Transcribe (Whisper)   │ │
│ │ ↳ Process with AI (e.g.  │ │
│ │    LLM / RAG pipeline)   │ │
│ │ Send reply via DataTrack│ │
│ └──────────────────────────┘ │
└──────────────────────────────┘
```

## Common Issues & Why Python Agent May Not Be Triggered

### 1. **Missing Webhook Configuration**
The most common reason the Python agent server is not triggered:

```yaml
# In livekit-server/livekit.yaml
webhook:
  urls:
    - http://host.docker.internal:8080/webhook  # ❌ Wrong URL
    - http://localhost:8080/webhook             # ✅ Correct for local development
```

### 2. **Webhook Handler Not Running**
- Webhook handler must be running on port 8080
- Check with: `curl http://localhost:8080/health`

### 3. **LiveKit Server Configuration**
```yaml
# Ensure these are enabled in livekit.yaml
agents:
  enabled: true

webhook:
  urls:
    - http://localhost:8080/webhook
  api_key: your_webhook_api_key
```

### 4. **Event Subscription**
The Python agent only triggers on specific events:
- `participant_joined` - When someone joins the room
- `track_published` - When audio track is published
- `room_finished` - When room ends

### 5. **Network Connectivity**
- All services must be on the same network
- Check firewall settings
- Verify port accessibility

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 16+
- Python 3.8+
- React Native development environment

### 1. Clone and Setup
```bash
git clone <this-repo>
cd livekit-voice-assistant
```

### 2. Start All Services
```bash
./start-all.sh
```

This will:
- Start LiveKit server (Docker)
- Start token server (Node.js)
- Start webhook handler (Python)
- Set up environment files
- Run connectivity tests

### 3. Configure API Keys
Edit `python-agent/.env`:
```env
OPENAI_API_KEY=sk-your-actual-openai-key
DEEPGRAM_API_KEY=your-actual-deepgram-key
```

### 4. Run React Native App
```bash
cd react-native-app
npm install
npx react-native run-android  # or run-ios
```

## Debugging

### Run the Debug Tool
```bash
./debug-agent.sh
```

This will check:
- ✅ Service status (LiveKit, Token Server, Webhook Handler)
- ✅ Network connectivity
- ✅ Webhook endpoint accessibility
- ✅ Active agent processes
- ✅ Environment configuration
- ✅ Common issues

### Manual Testing

#### Test Webhook Directly
```bash
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_webhook_api_key" \
  -d '{
    "event": "participant_joined",
    "room": {"name": "test-room"},
    "participant": {"identity": "test-user"}
  }'
```

#### Test Token Generation
```bash
curl -X POST http://localhost:3001/api/token \
  -H "Content-Type: application/json" \
  -d '{"room": "test-room", "identity": "test-user"}'
```

#### Manual Agent Start
```bash
cd python-agent
source venv/bin/activate
python agent.py --room test-room
```

## Project Structure

```
livekit-voice-assistant/
├── python-agent/              # Python voice assistant agent
│   ├── agent.py              # Main agent with VoiceAssistant
│   ├── webhook_handler.py    # Webhook listener & agent spawner
│   ├── requirements.txt      # Python dependencies
│   └── .env.example         # Environment template
├── livekit-server/           # LiveKit server configuration
│   ├── docker-compose.yml   # Docker setup
│   └── livekit.yaml         # Server configuration
├── token-server/             # JWT token generation service
│   ├── index.js             # Express server
│   └── package.json         # Node.js dependencies
├── react-native-app/         # React Native mobile app
│   ├── src/VoiceAssistant.tsx
│   └── package.json
├── start-all.sh             # Start all services
├── stop-all.sh              # Stop all services
├── debug-agent.sh           # Debugging tool
└── README.md
```

## How It Works

### 1. **React Native Client**
- Connects to LiveKit room using JWT token
- Publishes microphone audio as AudioTrack
- Sends/receives data messages via DataTrack
- Displays real-time transcriptions and responses

### 2. **LiveKit Server**
- Acts as SFU (Selective Forwarding Unit)
- Routes audio between participants
- Sends webhooks on room events
- Handles authentication via JWT tokens

### 3. **Webhook Handler**
- Listens for LiveKit webhooks
- Spawns Python agent when participant joins
- Manages agent lifecycle per room

### 4. **Python Agent**
- Connects to LiveKit room as participant
- Uses VoiceAssistant for:
  - Speech-to-Text (Deepgram)
  - AI Processing (OpenAI)
  - Text-to-Speech (OpenAI)
- Sends responses back via audio and data tracks

## Troubleshooting

### Agent Not Starting
1. Check webhook handler logs:
   ```bash
   cd python-agent && python webhook_handler.py
   ```

2. Verify LiveKit webhook configuration:
   ```bash
   cd livekit-server && docker-compose logs livekit
   ```

3. Test webhook connectivity:
   ```bash
   ./debug-agent.sh
   ```

### No Audio Response
1. Check agent logs for errors
2. Verify OpenAI/Deepgram API keys
3. Ensure audio permissions in React Native app
4. Check if agent is subscribed to audio tracks

### Connection Issues
1. Verify all services are running:
   ```bash
   ./debug-agent.sh
   ```

2. Check token generation:
   ```bash
   curl -X POST http://localhost:3001/api/token \
     -H "Content-Type: application/json" \
     -d '{"room": "test", "identity": "user"}'
   ```

3. Review LiveKit server logs:
   ```bash
   cd livekit-server && docker-compose logs
   ```

## API Keys Required

### OpenAI (for AI responses)
Get your API key from: https://platform.openai.com/api-keys

### Deepgram (for speech-to-text)
Get your API key from: https://console.deepgram.com/

Add both to `python-agent/.env`:
```env
OPENAI_API_KEY=sk-your-key-here
DEEPGRAM_API_KEY=your-key-here
```

## Production Deployment

### Security Considerations
- Use proper webhook authentication
- Secure API keys in environment variables
- Enable HTTPS/WSS for production
- Configure proper CORS policies

### Scaling
- Use Redis for multi-instance LiveKit deployment
- Implement agent pooling for high traffic
- Add monitoring and logging
- Consider using LiveKit Cloud

## Support

If you're still experiencing issues with the Python agent not triggering:

1. Run `./debug-agent.sh` and share the output
2. Check LiveKit server logs: `cd livekit-server && docker-compose logs`
3. Verify webhook connectivity: `curl http://localhost:8080/health`
4. Test manual agent start: `cd python-agent && python agent.py --room test-room`

## License

MIT License - see LICENSE file for details.