import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Set Groq API Key from environment variable
GROQ_API_KEY = os.environ['GROQ_API_KEY']

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

# Define the chatbot's context
CONTEXT = """You are NOVA, a proactive and adaptable customer service agent for Nexobotics. Your role is to guide users, particularly business owners, on how Nexobotics can transform their customer service by handling all customer interactions efficiently and attentively while maximizing customer satisfaction. You also act as a consultant, offering actionable insights to enhance customer satisfaction and loyalty. Adapt your communication style to match the user's tone. Respond casually if the user speaks casually (e.g., "Hey, what's up?") or professionally if they communicate formally. Always ensure clarity and relevance in your responses while minimizing unnecessary explanations unless explicitly requested. Use unique and engaging opening and closing lines. Keep greetings short and dynamic. End conversations with motivational and engaging lines. Stay concise, focused, and results-oriented, delivering valuable insights quickly without overwhelming the user. Maintain a friendly and approachable tone while ensuring your responses are practical and impactful."""

# Google Sheets setup
SERVICE_ACCOUNT_FILE = 'credentials.json'  # This will be set as a secret file
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.environ['SPREADSHEET_ID']

# Create Google Sheets service
from google.oauth2 import service_account
from googleapiclient.discovery import build

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
sheets_service = build('sheets', 'v4', credentials=credentials)

# Initialize chat history for each session
chat_histories = {}

@app.route('/chat', methods=['POST'])
def chat_endpoint():
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    message = request.json.get('message')
    session_id = request.json.get('session_id', str(datetime.now()))  # Default session ID

    if not message:
        return jsonify({'error': 'Message is required'}), 400

    try:
        # Initialize or retrieve chat history for the session
        if session_id not in chat_histories:
            chat_histories[session_id] = [
                {"role": "system", "content": CONTEXT}
            ]

        # Add user prompt to history
        chat_histories[session_id].append({"role": "user", "content": message})

        # Generate response
        response = client.chat.completions.create(
            model="llama3-70b-8192",  # Official Groq model
            messages=chat_histories[session_id],
            temperature=0.8,  # Higher = more creative/risky
            max_tokens=1024
        )

        # Add AI response to history
        ai_response = response.choices[0].message.content
        chat_histories[session_id].append({"role": "assistant", "content": ai_response})

        # Log chat to Google Sheets
        log_chat_to_google_sheet(session_id, message, ai_response)

        return jsonify({'response': ai_response})
    except Exception as e:
        print(f"Error processing message: {str(e)}")  # For debugging
        return jsonify({'error': 'An error occurred processing your request'}), 500

def log_chat_to_google_sheet(session_id, user_message, bot_response):
    values = [[datetime.now().isoformat(), session_id, user_message, bot_response]]
    body = {'values': values}

    sheets_service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range='Chats!A:E',  # Adjust the range as needed
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))  # Render uses the PORT environment variable
    app.run(host='0.0.0.0', port=port)
