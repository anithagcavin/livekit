import asyncio
import logging
import json
import subprocess
import os
from aiohttp import web, ClientSession
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("webhook-handler")
logging.basicConfig(level=logging.INFO)

# Store active agent processes
active_agents = {}

async def webhook_handler(request):
    """Handle LiveKit webhooks to trigger agents"""
    try:
        # Verify webhook signature if needed
        webhook_api_key = os.getenv("WEBHOOK_API_KEY", "your_webhook_api_key")
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header.startswith("Bearer "):
            return web.Response(status=401, text="Unauthorized")
            
        # Parse the webhook payload
        payload = await request.json()
        event = payload.get("event")
        room_name = payload.get("room", {}).get("name")
        
        logger.info(f"Received webhook: {event} for room: {room_name}")
        
        if event == "participant_joined":
            participant = payload.get("participant", {})
            participant_identity = participant.get("identity")
            
            logger.info(f"Participant {participant_identity} joined room {room_name}")
            
            # Check if we should start an agent for this room
            if room_name and room_name not in active_agents:
                await start_agent_for_room(room_name)
                
        elif event == "track_published":
            track = payload.get("track", {})
            track_type = track.get("type")
            participant = payload.get("participant", {})
            
            if track_type == "audio":
                logger.info(f"Audio track published in room {room_name}")
                
                # Ensure agent is running for this room
                if room_name and room_name not in active_agents:
                    await start_agent_for_room(room_name)
                    
        elif event == "room_finished":
            logger.info(f"Room {room_name} finished")
            
            # Stop agent for this room
            if room_name in active_agents:
                await stop_agent_for_room(room_name)
        
        return web.Response(status=200, text="OK")
        
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        return web.Response(status=500, text="Internal Server Error")

async def start_agent_for_room(room_name):
    """Start a Python agent for the specified room"""
    try:
        logger.info(f"Starting agent for room: {room_name}")
        
        # Set environment variables for the agent
        env = os.environ.copy()
        env["LIVEKIT_ROOM"] = room_name
        
        # Start the agent process
        process = await asyncio.create_subprocess_exec(
            "python", "agent.py", "--room", room_name,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Store the process
        active_agents[room_name] = process
        
        logger.info(f"Agent started for room {room_name} with PID {process.pid}")
        
        # Monitor the process
        asyncio.create_task(monitor_agent_process(room_name, process))
        
    except Exception as e:
        logger.error(f"Error starting agent for room {room_name}: {e}")

async def stop_agent_for_room(room_name):
    """Stop the agent for the specified room"""
    if room_name in active_agents:
        process = active_agents[room_name]
        try:
            process.terminate()
            await process.wait()
            logger.info(f"Agent stopped for room {room_name}")
        except Exception as e:
            logger.error(f"Error stopping agent for room {room_name}: {e}")
        finally:
            del active_agents[room_name]

async def monitor_agent_process(room_name, process):
    """Monitor an agent process and handle its output"""
    try:
        stdout, stderr = await process.communicate()
        
        if stdout:
            logger.info(f"Agent {room_name} stdout: {stdout.decode()}")
        if stderr:
            logger.error(f"Agent {room_name} stderr: {stderr.decode()}")
            
        # Clean up when process exits
        if room_name in active_agents:
            del active_agents[room_name]
            
        logger.info(f"Agent process for room {room_name} exited with code {process.returncode}")
        
    except Exception as e:
        logger.error(f"Error monitoring agent process for room {room_name}: {e}")

async def health_check(request):
    """Health check endpoint"""
    return web.Response(status=200, text="Webhook handler is running")

async def status_endpoint(request):
    """Get status of active agents"""
    status = {
        "active_agents": list(active_agents.keys()),
        "agent_count": len(active_agents)
    }
    return web.json_response(status)

def create_app():
    """Create the web application"""
    app = web.Application()
    
    # Routes
    app.router.add_post("/webhook", webhook_handler)
    app.router.add_get("/health", health_check)
    app.router.add_get("/status", status_endpoint)
    
    return app

if __name__ == "__main__":
    app = create_app()
    
    port = int(os.getenv("WEBHOOK_PORT", 8080))
    logger.info(f"Starting webhook handler on port {port}")
    
    web.run_app(app, host="0.0.0.0", port=port)