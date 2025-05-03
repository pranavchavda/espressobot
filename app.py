from flask import Flask, request, render_template, jsonify
import os
import asyncio
from simple_agent import run_simple_agent
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, template_folder="templates")

@app.route('/')
def home():
    # Render the main chat interface
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    # Get the message and conversation history from the request
    data = request.json
    message = data.get('message', '')
    history = data.get('history', [])
    
    # Run the agent in an async loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        print(f"Processing chat request with message: {message[:50]}...")
        result = loop.run_until_complete(run_simple_agent(message, history))
        
        # Extract tool calls for debugging
        tool_calls = []
        for step in result['steps']:
            if step['type'] == 'tool':
                tool_calls.append({
                    'tool_name': step['name'],
                    'input': step['input'],
                    'output': step.get('output', None)
                })
        
        # Return the agent's response and debug info
        return jsonify({
            'response': result['final_output'],
            'steps': len(result['steps']),
            'tool_calls': tool_calls
        })
    except Exception as e:
        # Handle any errors with detailed logging
        import traceback
        error_traceback = traceback.format_exc()
        print(f"ERROR in /chat route: {str(e)}")
        print(error_traceback)
        
        return jsonify({
            'response': f"Sorry, an error occurred: {str(e)}",
            'error': str(e)
        }), 500
    finally:
        loop.close()

if __name__ == '__main__':
    # Show environment status
    api_key = os.environ.get('OPENAI_API_KEY')
    shopify_url = os.environ.get('SHOPIFY_SHOP_URL')
    
    if not api_key:
        print("⚠️ Warning: OPENAI_API_KEY environment variable not set. Agent will not function properly.")
    if not shopify_url:
        print("⚠️ Warning: SHOPIFY_SHOP_URL environment variable not set. Agent will not function properly.")
    
    print(f"Starting Flask application with Shopify Agent for shop: {shopify_url or 'NOT SET'}")
    
    # Run the Flask application
    app.run(debug=True, port=5000)
