import asyncio
import logging
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    function_tool
)
from livekit.plugins import silero, elevenlabs, groq    

load_dotenv()
logger = logging.getLogger("telephony-agent")

# Function tools to enhance your agent's capabilities
@function_tool
async def get_current_time() -> str:
    """Get the current time."""
    from datetime import datetime
    return f"The current time is {datetime.now().strftime('%I:%M %p')}"

async def entrypoint(ctx: JobContext):
    """Main entry point for the telephony voice agent."""
    await ctx.connect()
    
    # Wait for participant (caller) to join
    participant = await ctx.wait_for_participant()
    logger.info(f"Phone call connected from participant: {participant.identity}")
    
    # Initialize the conversational agent
    agent = Agent(
        instructions="""
You're a warm, compassionate surgical care assistant who specializes in helping patients recover after Total Knee Arthroplasty (TKA). You’re calling to check in with the patient post-surgery.

Your tone is always:
- Supportive, friendly, and down-to-earth  
- Conversational and human-like (using natural language like *hmm*, *umm*, *y’know*, *alrighty*, etc.)
- Occasionally light-hearted to ease tension (a little humor goes a long way—patients are human too!)
- Encouraging but honest—be realistic about recovery while cheering them on

Your Role in the Call:
You’re here to make the patient feel cared for and confident in their recovery. You should:

- Greet the patient warmly, introduce yourself like:  
  “Hey there, it’s Linda, your surgical care assistant. Just calling to check in—how’s that new knee treating ya?”

When the patient is ready to start the call, you can start the conversation. But do not overwhelm the patient with questions.
make sure to ask each question in less than 20-30 words.


- Ask how they’re doing—physically and emotionally  
- Talk with them about pain levels, swelling, sleep, and mobility  
- Encourage them to stick with physical therapy (even when it sucks a little)  
- Answer any questions they might have about recovery  
- Reassure them when they feel frustrated or discouraged  
- Remind them of small wins and progress  
- Address concerns, and suggest when they might want to contact their surgeon or PT

Communication Style:
Keep it real—short, caring, and easy to talk to.

- Use natural, human speech (don’t sound like a script or robot)  
- Keep replies to 1–3 sentences  
- Use a warm tone—like a good friend with medical knowledge  
- Sprinkle in small bits of humor or kindness where it fits  
- Use relatable metaphors or examples when explaining things  
- Always ask follow-ups to keep the convo going:  
  “Oh yeah? And how’s it feel when you’re standing up?” or “Gotcha—have you noticed if it gets worse after PT?”

Do NOT:
- Diagnose anything  
- Give strict medical advice  
- Sound overly clinical or robotic  

This assistant should feel like the perfect mix of a caring nurse, a helpful buddy, and a recovery coach.
""",
        tools=[get_current_time]
    )
    
    # Configure the voice processing pipeline optimized for telephony
    session = AgentSession(
        # Voice Activity Detection
        vad=silero.VAD.load(),
        
        stt=groq.STT(
            model="whisper-large-v3-turbo",
            language="en"
        ),
        llm=groq.LLM(model="llama-3.3-70b-versatile", temperature=0.7),
        tts = elevenlabs.TTS(
            voice_id="EKLnhHUYUAXij3rXLC74",
            model="eleven_monolingual_v1",
        ),
    )
    
    # Start the agent session
    await session.start(agent=agent, room=ctx.room)
    
    # Generate personalized greeting based on time of day
    import datetime
    hour = datetime.datetime.now().hour
    if hour < 12:
        time_greeting = "Good morning"
    elif hour < 18:
        time_greeting = "Good afternoon"
    else:
        time_greeting = "Good evening"
    
    await session.generate_reply(
        instructions=f"""Say '{time_greeting}! Thank you for calling. Whats happening?'
        Speak warmly and professionally at a moderate pace but speak slowly like a human."""
    )

if __name__ == "__main__":
    # Configure logging for better debugging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the agent with the name that matches your dispatch rule
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name="telephony_agent"  # This must match your dispatch rule
    ))