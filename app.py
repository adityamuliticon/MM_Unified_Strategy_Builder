from flask import Flask, render_template, request, jsonify
from config import Config
import os

from core.orchestrator import orchestrator

app = Flask(__name__)
app.config.from_object(Config)

# Memory for session history (simplistic for demo)
memory = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message')
    session_id = data.get('session_id', 'default')
    
    if session_id not in memory:
        memory[session_id] = []

    try:
        response_text = orchestrator.process_message(user_message, memory[session_id])
    except Exception as e:
        error_msg = str(e)
        if "Insufficient credits" in error_msg or "credits" in error_msg.lower():
            response_text = "⚠️ **AI service unavailable**: The Runware AI account has insufficient credits. Please top up at app.runware.ai and try again."
        else:
            response_text = f"⚠️ **Unexpected error**: {error_msg}"

    # Update memory
    memory[session_id].append({"role": "user", "content": user_message})
    memory[session_id].append({"role": "assistant", "content": response_text})

    return jsonify({
        "status": "success",
        "message": response_text
    })

if __name__ == '__main__':
    # Ensure necessary directories exist
    os.makedirs('rag/store', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
