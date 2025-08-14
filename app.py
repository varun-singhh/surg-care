# app.py

from flask import Flask, render_template, request, jsonify
import os
import asyncio
import aiohttp
import jwt
import time
import json
from datetime import datetime, timedelta

# Ensure environment variables are loaded
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# Environment variables
LIVEKIT_URL = os.getenv('LIVEKIT_URL')
LIVEKIT_API_KEY = os.getenv('LIVEKIT_API_KEY')
LIVEKIT_API_SECRET = os.getenv('LIVEKIT_API_SECRET')
SIP_TRUNK_ID = os.getenv('SIP_TRUNK_ID')

def generate_access_token():
    """Generate admin JWT token with all permissions"""
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise ValueError("Missing LIVEKIT_API_KEY or LIVEKIT_API_SECRET")
    
    now = int(time.time())
    exp = now + 3600  # 1 hour expiration
    
    # More permissive payload - grants admin access to everything
    payload = {
        'iss': LIVEKIT_API_KEY,
        'exp': exp,
        'nbf': now,
        'sub': 'admin-service',
        # Grant admin access to all services
        'video': {
            'room': '*',
            'roomCreate': True,
            'roomJoin': True,
            'roomList': True,
            'roomAdmin': True,
            'canPublish': True,
            'canSubscribe': True,
            'canUpdateOwnMetadata': True,
            'canPublishData': True,
            'canSubscribeData': True
        },
        'sip': {
            'call': True,
            'admin': True
        },
        'agent': {
            'dispatch': True,
            'list': True,
            'admin': True
        },
        'ingress': {
            'create': True,
            'update': True,
            'list': True,
            'delete': True,
            'admin': True
        },
        'egress': {
            'create': True,
            'update': True,
            'list': True,
            'delete': True,
            'admin': True
        }
    }
    
    try:
        token = jwt.encode(payload, LIVEKIT_API_SECRET, algorithm='HS256')
        return token
    except Exception as e:
        raise ValueError(f"Failed to generate JWT: {e}")

async def create_room_and_call(phone_number: str):
    """Create a LiveKit room and initiate SIP call using REST API"""
    
    # Validate environment variables
    if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, SIP_TRUNK_ID]):
        missing_vars = [v for v in ['LIVEKIT_URL', 'LIVEKIT_API_KEY', 'LIVEKIT_API_SECRET', 'SIP_TRUNK_ID'] if not os.getenv(v)]
        return f"Error: Missing environment variables: {', '.join(missing_vars)}"
    
    try:
        # Generate unique room name
        timestamp = int(time.time())
        room_name = f"surgical-call-{timestamp}"
        
        # Generate admin token with all permissions
        try:
            token = generate_access_token()  # Use the new admin token function
        except ValueError as e:
            return f"Token generation error: {e}"
        
        # LiveKit API base URL - handle different URL formats
        if LIVEKIT_URL.startswith('wss://'):
            api_url = LIVEKIT_URL.replace('wss://', 'https://')
        elif LIVEKIT_URL.startswith('ws://'):
            api_url = LIVEKIT_URL.replace('ws://', 'http://')
        else:
            api_url = LIVEKIT_URL
            
        # Ensure no trailing slash
        api_url = api_url.rstrip('/')
        
        print(f"🔗 Using API URL: {api_url}")
        print(f"🔑 Using API Key: {LIVEKIT_API_KEY}")
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Step 1: Create room first with agent metadata
            room_data = {
                'name': room_name,
                'empty_timeout': 300,  # 5 minutes
                'max_participants': 10,
                'metadata': json.dumps({
                    'agent_required': True,
                    'agent_name': 'telephone_agent',
                    'call_type': 'sip_outbound',
                    'phone_number': phone_number,
                    'timestamp': timestamp
                })
            }
            
            print(f"🏠 Creating room: {room_name}")
            
            create_room_url = f'{api_url}/twirp/livekit.RoomService/CreateRoom'
            async with session.post(create_room_url, json=room_data, headers=headers) as response:
                response_text = await response.text()
                print(f"📡 Room creation response: {response.status} - {response_text}")
                
                if response.status != 200:
                    return f"Error creating room: {response.status} - {response_text}"
            
            # Step 2: Skip manual agent dispatch - let agent auto-join via room metadata
            print(f"🤖 Room created with agent metadata - agent should auto-join")
            
            # Step 3: Create SIP participant (outbound call)
            sip_data = {
                'sip_trunk_id': SIP_TRUNK_ID,
                'sip_call_to': phone_number,
                'room_name': room_name,
                'participant_identity': f'phone-{phone_number.replace("+", "").replace("-", "")}',
                'participant_name': f'Phone Call to {phone_number}',
                'participant_metadata': json.dumps({
                    'phone_number': phone_number,
                    'call_type': 'outbound',
                    'timestamp': timestamp
                }),
                'play_dialtone': True,
            }
            
            print(f"📞 Creating SIP call to: {phone_number}")
            
            sip_call_url = f'{api_url}/twirp/livekit.SIP/CreateSIPParticipant'
            async with session.post(sip_call_url, json=sip_data, headers=headers) as response:
                response_text = await response.text()
                print(f"📡 SIP call response: {response.status} - {response_text}")
                
                if response.status == 200:
                    result = await response.json()
                    return f"✅ Call initiated successfully!\nRoom: {room_name}\nParticipant ID: {result.get('participant_id', 'N/A')}\n🤖 Agent should join the call shortly"
                else:
                    return f"Error creating SIP participant: {response.status} - {response_text}"
                    
    except Exception as e:
        return f"Exception occurred: {str(e)}"
     
async def list_sip_trunks():
    """List available SIP trunks to help debug configuration"""
    if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
        return "Missing LiveKit credentials"
    
    try:
        token = generate_access_token()
        api_url = LIVEKIT_URL.replace('wss://', 'https://').replace('ws://', 'http://')
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{api_url}/twirp/livekit.SIP/ListSIPOutboundTrunk', 
                                  json={}, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    trunks = result.get('items', [])
                    if trunks:
                        trunk_info = "\n".join([f"• {trunk.get('name', 'Unnamed')} (ID: {trunk.get('sipTrunkId', 'N/A')})" 
                                              for trunk in trunks])
                        return f"Available SIP Trunks:\n{trunk_info}"
                    else:
                        return "No SIP trunks found. You need to create one first."
                else:
                    error_text = await response.text()
                    return f"Error listing trunks: {response.status} - {error_text}"
                    
    except Exception as e:
        return f"Exception: {str(e)}"

@app.route('/debug/manual-dispatch')
def manual_dispatch():
    """Manually dispatch agent to a room"""
    room_name = request.args.get('room', 'test-room')
    
    try:
        # First create a room
        token = generate_access_token()
        api_url = LIVEKIT_URL.replace('wss://', 'https://').replace('ws://', 'http://').rstrip('/')
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        
        import requests
        
        room_data = {'name': room_name}
        room_response = requests.post(f'{api_url}/twirp/livekit.RoomService/CreateRoom', 
                                    json=room_data, headers=headers)
        
        result = f"Room creation: {room_response.status_code}\n"
        
        # Try to manually dispatch agent
        dispatch_data = {
            'room': room_name,
            'agent_name': 'telephone_agent'
        }
        
        dispatch_response = requests.post(f'{api_url}/twirp/livekit.AgentDispatchService/CreateDispatch', 
                                        json=dispatch_data, headers=headers)
        
        result += f"Agent dispatch: {dispatch_response.status_code}\n"
        result += f"Response: {dispatch_response.text}\n"
        
        return f"<pre>{result}</pre>"
        
    except Exception as e:
        return f"<pre>Exception: {e}</pre>"


# Modified create_room_and_call with delay and manual agent trigger
async def create_room_and_call_with_agent_delay(phone_number: str):
    """Create room, make SIP call, then manually add agent"""
    
    if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, SIP_TRUNK_ID]):
        missing_vars = [v for v in ['LIVEKIT_URL', 'LIVEKIT_API_KEY', 'LIVEKIT_API_SECRET', 'SIP_TRUNK_ID'] if not os.getenv(v)]
        return f"Error: Missing environment variables: {', '.join(missing_vars)}"
    
    try:
        timestamp = int(time.time())
        room_name = f"surgical-call-{timestamp}"
        
        token = generate_access_token()
        
        if LIVEKIT_URL.startswith('wss://'):
            api_url = LIVEKIT_URL.replace('wss://', 'https://')
        elif LIVEKIT_URL.startswith('ws://'):
            api_url = LIVEKIT_URL.replace('ws://', 'http://')
        else:
            api_url = LIVEKIT_URL
        api_url = api_url.rstrip('/')
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Step 1: Create room (no agent metadata yet)
            room_data = {
                'name': room_name,
                'empty_timeout': 300,
                'max_participants': 10,
            }
            
            print(f"🏠 Creating room: {room_name}")
            create_room_url = f'{api_url}/twirp/livekit.RoomService/CreateRoom'
            async with session.post(create_room_url, json=room_data, headers=headers) as response:
                if response.status != 200:
                    return f"Error creating room: {response.status} - {await response.text()}"
            
            # Step 2: Create SIP call
            sip_data = {
                'sip_trunk_id': SIP_TRUNK_ID,
                'sip_call_to': phone_number,
                'room_name': room_name,
                'participant_identity': f'phone-{phone_number.replace("+", "").replace("-", "")}',
                'participant_name': f'Phone Call to {phone_number}',
                'participant_metadata': json.dumps({
                    'phone_number': phone_number,
                    'call_type': 'outbound',
                    'timestamp': timestamp
                }),
                'play_dialtone': True,
            }
            
            print(f"📞 Creating SIP call to: {phone_number}")
            sip_call_url = f'{api_url}/twirp/livekit.SIP/CreateSIPParticipant'
            async with session.post(sip_call_url, json=sip_data, headers=headers) as response:
                if response.status != 200:
                    return f"Error creating SIP participant: {response.status} - {await response.text()}"
                
                sip_result = await response.json()
                print(f"✅ SIP call created: {sip_result.get('participant_id')}")
            
            # Step 3: Wait a moment for call to establish, then try to add agent
            await asyncio.sleep(3)
            
            # Try to update room metadata to trigger agent
            update_data = {
                'room': room_name,
                'metadata': json.dumps({
                    'agent_required': True,
                    'agent_name': 'telephone_agent',
                    'call_established': True
                })
            }
            
            update_url = f'{api_url}/twirp/livekit.RoomService/UpdateRoomMetadata'
            async with session.post(update_url, json=update_data, headers=headers) as response:
                print(f"📋 Room metadata update: {response.status}")
            
            return f"✅ Call initiated to {phone_number}!\nRoom: {room_name}\n🤖 Attempting to add agent..."
                    
    except Exception as e:
        return f"Exception occurred: {str(e)}"
    
@app.route('/', methods=['GET', 'POST'])
def index():
    message = None
    if request.method == 'POST':
        phone_number = request.form['phone_number']
        
        # Validate phone number format
        if not phone_number.startswith("+"):
            message = "❌ Error: Phone number must be in E.164 format (e.g., +1XXXXXXXXXX)."
        else:
            message = asyncio.run(create_room_and_call(phone_number))
    
    return render_template('index.html', message=message)

@app.route('/debug/call-status/<call_id>')
def debug_call_status(call_id):
    """Debug endpoint to check SIP call status"""
    try:
        token = generate_access_token()
        api_url = LIVEKIT_URL.replace('wss://', 'https://').replace('ws://', 'http://').rstrip('/')
        
        import requests
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Try to get SIP call info
        response = requests.post(f'{api_url}/twirp/livekit.SIP/ListSIPParticipant', 
                               json={}, headers=headers)
        
        if response.status_code == 200:
            participants = response.json().get('items', [])
            call_info = [p for p in participants if call_id in p.get('sip_call_id', '')]
            return f"<pre>Call Status for {call_id}:\n{json.dumps(call_info, indent=2)}</pre>"
        else:
            return f"<pre>Error getting call status: {response.status_code} - {response.text}</pre>"
            
    except Exception as e:
        return f"<pre>Exception: {str(e)}</pre>"

@app.route('/debug/trunk-config')
def debug_trunk_config():
    """Debug endpoint to show trunk configuration"""
    config_info = f"""
<h2>Current Configuration</h2>
<pre>
LIVEKIT_URL: {LIVEKIT_URL}
LIVEKIT_API_KEY: {LIVEKIT_API_KEY}
SIP_TRUNK_ID: {SIP_TRUNK_ID}
TWILIO_PHONE_NUMBER: {os.getenv('TWILIO_PHONE_NUMBER')}

Expected Twilio Trunk Domain: Should end with .pstn.twilio.com
Expected Authentication: Username/Password credentials configured

LiveKit Trunk JSON should look like:
{{
  "trunk": {{
    "name": "Your Trunk Name",
    "address": "your-trunk-name.pstn.twilio.com",
    "numbers": ["{os.getenv('TWILIO_PHONE_NUMBER', '+1XXXXXXXXXX')}"],
    "auth_username": "your_username",
    "auth_password": "your_password"
  }}
}}
</pre>

<h3>Next Steps:</h3>
<ol>
<li>Verify your Twilio trunk domain ends with .pstn.twilio.com</li>
<li>Check that credentials are properly configured in Twilio</li>
<li>Ensure phone number is associated with the trunk</li>
<li>Test a simple call from Twilio console first</li>
</ol>
    """
    return config_info

@app.route('/health')
def health():
    """Health check endpoint"""
    config_status = {
        'LIVEKIT_URL': '✅' if LIVEKIT_URL else '❌',
        'LIVEKIT_API_KEY': '✅' if LIVEKIT_API_KEY else '❌', 
        'LIVEKIT_API_SECRET': '✅' if LIVEKIT_API_SECRET else '❌',
        'SIP_TRUNK_ID': '✅' if SIP_TRUNK_ID else '❌'
    }
    
    status_html = "<h2>Configuration Status</h2><ul>"
    for key, status in config_status.items():
        status_html += f"<li>{key}: {status}</li>"
    status_html += "</ul>"
    
    if all(val == '✅' for val in config_status.values()):
        status_html += "<p>✅ All configuration looks good!</p>"
    else:
        status_html += "<p>❌ Please check your .env file for missing variables.</p>"
    
    return status_html

if __name__ == '__main__':
    # Configuration check
    print("\n🔧 LiveKit SIP Configuration Check:")
    print(f"LIVEKIT_URL: {'✅' if LIVEKIT_URL else '❌ Missing'}")
    print(f"LIVEKIT_API_KEY: {'✅' if LIVEKIT_API_KEY else '❌ Missing'}")
    print(f"LIVEKIT_API_SECRET: {'✅' if LIVEKIT_API_SECRET else '❌ Missing'}")
    print(f"SIP_TRUNK_ID: {'✅' if SIP_TRUNK_ID else '❌ Missing'}")
    
    if not SIP_TRUNK_ID:
        print("\n⚠️  SIP_TRUNK_ID is missing!")
        print("📋 To get your SIP_TRUNK_ID:")
        print("   1. Set up a SIP provider (Twilio, Telnyx, etc.)")
        print("   2. Configure outbound trunk in LiveKit")
        print("   3. Use the returned trunk ID in your .env file")
        print("   4. Visit /debug/trunks to see available trunks")
    
    print(f"\n🚀 Starting server on http://localhost:5001")
    print(f"🔍 Debug endpoint: http://localhost:5001/debug/trunks")
    print(f"❤️  Health check: http://localhost:5001/health")
    
    app.run(debug=True, port=5001)