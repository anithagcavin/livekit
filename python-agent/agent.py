import asyncio
import logging
import os
from dotenv import load_dotenv
from livekit import rtc, api
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import openai, deepgram
import json

load_dotenv()

logger = logging.getLogger("voice-assistant")
logger.setLevel(logging.INFO)

async def entrypoint(ctx: JobContext):
    """Main entry point for the voice assistant agent"""
    logger.info("Starting voice assistant agent")
    
    # Connect to the room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # Set up AI services
    assistant = VoiceAssistant(
        vad=ctx.proc.userdata.get("vad"),
        stt=deepgram.STT(),
        llm=openai.LLM(),
        tts=openai.TTS(),
        chat_ctx=llm.ChatContext().append(
            role="system",
            text=(
                "You are a voice assistant created by LiveKit. Your interface with users will be voice. "
                "You should use short and concise responses, and avoiding usage of unpronouncable punctuation."
            ),
        ),
    )
    
    # Start the assistant
    assistant.start(ctx.room)
    
    # Handle participant events
    @ctx.room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant):
        logger.info(f"Participant connected: {participant.identity}")
        
    @ctx.room.on("participant_disconnected") 
    def on_participant_disconnected(participant: rtc.RemoteParticipant):
        logger.info(f"Participant disconnected: {participant.identity}")
    
    # Handle track subscriptions
    @ctx.room.on("track_subscribed")
    def on_track_subscribed(
        track: rtc.Track,
        publication: rtc.RemoteTrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        logger.info(f"Track subscribed: {track.kind} from {participant.identity}")
        
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info("Audio track received - processing with voice assistant")
            # The VoiceAssistant will automatically handle audio processing
    
    # Handle data messages (chat)
    @ctx.room.on("data_received")
    def on_data_received(data: bytes, participant: rtc.RemoteParticipant):
        try:
            message = json.loads(data.decode())
            logger.info(f"Data received from {participant.identity}: {message}")
            
            # Echo back or process the message
            response = {
                "type": "response",
                "message": f"Received: {message.get('message', 'No message')}",
                "timestamp": message.get("timestamp")
            }
            
            # Send response back via data track
            asyncio.create_task(
                ctx.room.local_participant.publish_data(
                    json.dumps(response).encode(),
                    destination_sids=[participant.sid]
                )
            )
            
        except Exception as e:
            logger.error(f"Error processing data message: {e}")
    
    logger.info("Voice assistant agent is ready and waiting for audio/data")

def prewarm(proc: JobProcess):
    """Prewarm function to initialize resources"""
    # Initialize VAD (Voice Activity Detection)
    proc.userdata["vad"] = ctx.proc.userdata.get("vad")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run the agent
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )