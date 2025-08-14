#!/bin/bash

# LiveKit SIP Agent Setup Script
echo "🚀 Setting up LiveKit SIP Agent..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📈 Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📥 Installing LiveKit dependencies..."

# Install core LiveKit packages
pip install livekit>=0.15.0
pip install livekit-agents>=0.10.0

# Install plugin packages
pip install livekit-plugins-groq>=0.5.0
pip install livekit-plugins-elevenlabs>=0.6.0
pip install livekit-plugins-silero>=0.6.0

# Install web framework dependencies
pip install flask>=3.0.0
pip install aiohttp>=3.9.0
pip install python-dotenv>=1.0.0
pip install PyJWT>=2.8.0

echo "✅ Installation complete!"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "📝 Creating sample .env file..."
    cat > .env << EOF
# LiveKit Configuration
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# SIP Configuration
SIP_TRUNK_ID=your_trunk_id

# AI Service Keys
GROQ_API_KEY=your_groq_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key

# Optional: Twilio Configuration (if using Twilio as SIP provider)
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX
EOF
    echo "📄 Sample .env file created. Please edit it with your actual credentials."
else
    echo "📄 .env file already exists."
fi

echo ""
echo "🎉 Setup complete! Next steps:"
echo ""
echo "1. Edit your .env file with actual credentials:"
echo "   nano .env"
echo ""
echo "2. Test the simple agent:"
echo "   python agent_simple.py dev"
echo ""
echo "3. In another terminal, start the web interface:"
echo "   python app.py"
echo ""
echo "4. Make test calls through http://localhost:5001"
echo ""
echo "⚠️  Remember: Always start the agent BEFORE making calls!"