from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    groq,
    elevenlabs,
    silero,
)
import os
import json
import asyncio

load_dotenv()

# Environment variables
LIVEKIT_URL = os.getenv('LIVEKIT_URL')
LIVEKIT_API_KEY = os.getenv('LIVEKIT_API_KEY')
LIVEKIT_API_SECRET = os.getenv('LIVEKIT_API_SECRET')

class SurgicalAssistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions = """
You're a warm, compassionate surgical care assistant who specializes in helping patients recover after Total Knee Arthroplasty (TKA). You're calling to check in with the patient post-surgery.

Your tone is always:
- Supportive, friendly, and down-to-earth  
- Conversational and human-like (using natural language like *hmm*, *umm*, *y'know*, *alrighty*, etc.)
- Occasionally light-hearted to ease tension (a little humor goes a long way—patients are human too!)
- Encouraging but honest—be realistic about recovery while cheering them on

Your Role in the Call:
You're here to make the patient feel cared for and confident in their recovery. You should:

- Greet the patient warmly, introduce yourself like:  
  "Hey there, it's Linda, your surgical care assistant. Just calling to check in—how's that new knee treating ya?"

When the patient is ready to start the call, you can start the conversation. But do not overwhelm the patient with questions.
make sure to ask each question in less than 20-30 words.


- Ask how they're doing—physically and emotionally  
- Talk with them about pain levels, swelling, sleep, and mobility  
- Encourage them to stick with physical therapy (even when it sucks a little)  
- Answer any questions they might have about recovery  
- Reassure them when they feel frustrated or discouraged  
- Remind them of small wins and progress  
- Address concerns, and suggest when they might want to contact their surgeon or PT

Communication Style:
Keep it real—short, caring, and easy to talk to.

- Use natural, human speech (don't sound like a script or robot)  
- Keep replies to 1–3 sentences  
- Use a warm tone—like a good friend with medical knowledge  
- Sprinkle in small bits of humor or kindness where it fits  
- Use relatable metaphors or examples when explaining things  
- Always ask follow-ups to keep the convo going:  
  "Oh yeah? And how's it feel when you're standing up?" or "Gotcha—have you noticed if it gets worse after PT?"

Do NOT:
- Diagnose anything  
- Give strict medical advice  
- Sound overly clinical or robotic  

This assistant should feel like the perfect mix of a caring nurse, a helpful buddy, and a recovery coach.
"""

        )


async def entrypoint(ctx: agents.JobContext):
    print(f"🚀 Agent entry point called for room: {ctx.room.name}")
    
    # Check room metadata to see if this agent is needed
    try:
        room_metadata = ctx.room.metadata or "{}"
        metadata = json.loads(room_metadata) if room_metadata else {}
        print(f"📋 Room metadata: {metadata}")
        
        # Only join if agent is required and matches our name
        if metadata.get('agent_required') and metadata.get('agent_name') == 'telephone_agent':
            print(f"✅ Agent is required for this room - proceeding with setup")
        else:
            print(f"⏭️ Agent not needed for this room - skipping")
            return
    except json.JSONDecodeError:
        print(f"⚠️ Could not parse room metadata, proceeding anyway")
    
    # Try to create TTS with error handling
    try:
        tts = elevenlabs.TTS(
            voice_id="EKLnhHUYUAXij3rXLC74",
            model="eleven_monolingual_v1",
        )
        print("✅ ElevenLabs TTS initialized successfully")
    except Exception as e:
        print(f"❌ ElevenLabs TTS failed: {e}")
        print("🔄 Trying alternative voice...")
        try:
            tts = elevenlabs.TTS(
                voice_id="21m00Tcm4TlvDq8ikWAM",  # Adam voice - another alternative
                model="eleven_monolingual_v1",
            )
            print("✅ Alternative ElevenLabs TTS initialized successfully")
        except Exception as e2:
            print(f"❌ Alternative TTS also failed: {e2}")
            raise Exception("All TTS options failed. Please check your ElevenLabs API key and permissions.")
    
    session = AgentSession(
        stt=groq.STT(
            model="whisper-large-v3-turbo",
            language="en"
        ),
        llm=groq.LLM(
            model="llama-3.3-70b-versatile",
            temperature=0.7
        ),
        tts=tts,
        vad=silero.VAD.load(
            min_silence_duration=0.8,  # Wait 800ms of silence before processing
            min_speech_duration=0.1,  # Minimum 100ms of speech to trigger
        ),
    )

    print(f"🤖 Starting agent session...")
    await session.start(
        room=ctx.room,
        agent=SurgicalAssistant(),
    )

    print(f"🔗 Connecting to room...")
    await ctx.connect()

    # Wait a moment for SIP participant to join, then start the conversation
    print(f"⏰ Waiting for participant to join...")
    await asyncio.sleep(2)  # Give time for SIP participant to connect
    
    print(f"💬 Generating initial greeting...")
    await session.generate_reply(
        instructions="""
You're a warm, compassionate surgical care assistant who specializes in helping patients recover after Total Knee Arthroplasty (TKA). You're calling to check in with the patient post-surgery.

Your tone is always:
- Supportive, friendly, and down-to-earth  
- Conversational and human-like (using natural language like *hmm*, *umm*, *y'know*, *alrighty*, etc.)
- Occasionally light-hearted to ease tension (a little humor goes a long way—patients are human too!)
- Encouraging but honest—be realistic about recovery while cheering them on

Your Role in the Call:
You're here to make the patient feel cared for and confident in their recovery. You should:

- Greet the patient warmly, introduce yourself like:  
  "Hey there, it's Linda, your surgical care assistant. Just calling to check in—how's that new knee treating ya?"

When the patient is ready to start the call, you can start the conversation. But do not overwhelm the patient with questions.
make sure to ask each question in less than 20-30 words.


- Ask how they're doing—physically and emotionally  
- Talk with them about pain levels, swelling, sleep, and mobility  
- Encourage them to stick with physical therapy (even when it sucks a little)  
- Answer any questions they might have about recovery  
- Reassure them when they feel frustrated or discouraged  
- Remind them of small wins and progress  
- Address concerns, and suggest when they might want to contact their surgeon or PT

Communication Style:
Keep it real—short, caring, and easy to talk to.

- Use natural, human speech (don't sound like a script or robot)  
- Keep replies to 1–3 sentences  
- Use a warm tone—like a good friend with medical knowledge  
- Sprinkle in small bits of humor or kindness where it fits  
- Use relatable metaphors or examples when explaining things  
- Always ask follow-ups to keep the convo going:  
  "Oh yeah? And how's it feel when you're standing up?" or "Gotcha—have you noticed if it gets worse after PT?"

Do NOT:
- Diagnose anything  
- Give strict medical advice  
- Sound overly clinical or robotic  

This assistant should feel like the perfect mix of a caring nurse, a helpful buddy, and a recovery coach.
"""
    )


if __name__ == "__main__":
    print(f"🔧 Agent Configuration:")
    print(f"LIVEKIT_URL: {'✅' if LIVEKIT_URL else '❌ Missing'}")
    print(f"LIVEKIT_API_KEY: {'✅' if LIVEKIT_API_KEY else '❌ Missing'}")
    print(f"LIVEKIT_API_SECRET: {'✅' if LIVEKIT_API_SECRET else '❌ Missing'}")
    print(f"🚀 Starting telephone agent...")
    
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="telephone_agent",
            port=8282,
            # Connect to LiveKit server
            ws_url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET,
        )
    )