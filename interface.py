# web_interface.py (Minimal example)
from flask import Flask, request, jsonify
from director import Director
from memory.chat_memory import ChatMemory # Assuming path is correct
import os

# NOTE: Use a test user email that has been properly logged in via login.py
TEST_USER_EMAIL = "Amritesh3R@gmail.com" 

# --- Initialization ---
try:
    # Initialize Core Components once
    chat_memory = ChatMemory(user_email=TEST_USER_EMAIL)
    # We must pass the memory instance to the Director for Contextual Injection
    director = Director(user_email=TEST_USER_EMAIL, chat_memory_instance=chat_memory)
    chat_memory.start_new_conversation() # Start a fresh conversation state
    CORE_LOADED = True
except Exception as e:
    print(f"FATAL: Core initialization failed: {e}")
    CORE_LOADED = False

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    if not CORE_LOADED:
         return jsonify({
             "status": "error",
             "message": "Core services failed to load during initialization. Check logs for token errors."
         }), 500
         
    return jsonify({
        "status": "ready",
        "message": "Wingman API is running. Send a JSON POST request to /query with your question.",
        "example_post_body": {
            "query": "Send an email to John about the meeting."
        }
    })

@app.route('/query', methods=['POST'])
def handle_web_query():
    if not CORE_LOADED:
        return jsonify({"error": "Core services failed to load. Check server logs."}), 500

    data = request.json
    user_query = data.get('query')

    if not user_query:
        return jsonify({"response": "Please provide a 'query' field."})

    try:
        # Use Director to execute the task
        # NOTE: Director.handle_query returns a Dict {'message': str, 'raw_data': Any, 'agent_key': str}
        director_output = director.handle_query(user_query)
        
        # In an API, we send the message and potentially the final raw data for debugging
        return jsonify({
            "query": user_query,
            "response": director_output['message'],
            "status": "success",
            "last_agent": director_output['agent_key'],
            "raw_data_context": str(director_output.get('raw_data')) # Send raw data for inspection
        })

    except Exception as e:
        return jsonify({"response": f"An unhandled system error occurred: {str(e)}", "status": "error"}), 500

if __name__ == '__main__':
    # Running on port 5000 is common for Flask
    app.run(host='0.0.0.0', port=5000, debug=True) # Recommended!