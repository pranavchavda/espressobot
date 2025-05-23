import os
import sys
import uuid


# --- Ensure running inside venv ---
def _in_venv():
    return (hasattr(sys, 'real_prefix')
            or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))


def _find_venv_python():
    venv_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'myenv')
    if os.name == 'nt':
        python_path = os.path.join(venv_dir, 'Scripts', 'python.exe')
    else:
        python_path = os.path.join(venv_dir, 'bin', 'python')
    return python_path if os.path.exists(python_path) else None


if not _in_venv():
    venv_python = _find_venv_python()
    if venv_python:
        print(f"[INFO] Relaunching in venv: {venv_python}")
        os.execv(venv_python, [venv_python] + sys.argv)
    else:
        print(
            "[WARNING] No venv found! Running with system Python. It is recommended to use a virtual environment in ./venv."
        )

from flask import Flask, request, jsonify, redirect, session, url_for
from uvicorn.middleware.wsgi import WSGIMiddleware
import uvicorn
import os
import json
import asyncio
from datetime import datetime
from simple_agent import run_simple_agent, client as openai_client
from responses_agent import run_responses_agent, generate_conversation_title
from dotenv import load_dotenv
from flask_login import login_user, logout_user, current_user, login_required
from memory_service import memory_service
# UserMixin will be in models.py with the User model
import google_tasks


# Import Models
from models import User, Conversation, Message

# Import extensions
from extensions import db, migrate, login_manager, verify_db_connection

# Import blueprints - ensure stream_chat is imported before its blueprint is created/used
from stream_chat import create_stream_blueprint

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY',
                                'devsecret')  # Needed for session

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    f"sqlite:///{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shopify_agent.db')}"
)
print(f"DEBUG: Connecting to DB: {app.config['SQLALCHEMY_DATABASE_URI']}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Add SQLAlchemy connection pool settings for better resilience
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,  # Recycle connections after 5 minutes
    'pool_timeout': 20,  # Wait up to 20 seconds for a connection
    'pool_pre_ping': True,  # Enable connection health checks
    'connect_args': {
        'sslmode': 'require',  # Require SSL but don't verify
        'connect_timeout': 10,  # 10 second connection timeout
    }
}

# Initialize extensions with the app object
db.init_app(app)
migrate.init_app(app, db)  # Migrate needs db instance as well
login_manager.init_app(app)

# Verify database connection on startup
try:
    with app.app_context():
        success, message = verify_db_connection()
        if success:
            print("✅ Database connection verified successfully")
        else:
            print(f"⚠️ Warning: Database connection check failed: {message}")
except Exception as e:
    print(f"⚠️ Warning: Error checking database connection: {e}")

login_manager.login_view = None  # We are an API, frontend handles login prompts
login_manager.session_protection = "strong"


@app.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    return jsonify({
        "name": current_user.name,
        "email": current_user.
        email,  # Email is usually good to return, though not editable here
        "bio": current_user.bio
    }), 200


@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    data = request.get_json()

    if 'name' in data:
        current_user.name = data['name']
    if 'bio' in data:
        current_user.bio = data['bio']

    db.session.commit()
    return jsonify({"message": "Profile updated successfully."}), 200


# User loader function uses the imported User model
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(
        User, int(user_id))  # Use db.session.get for SQLAlchemy 2.0 style


@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    raw_email = data.get('email')
    password = data.get('password')
    name = data.get('name', None)

    if not raw_email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    email = raw_email.lower()  # Convert to lowercase

    # Check if user already exists using the case-insensitive email
    if User.query.filter(db.func.lower(User.email) == email).first():
        return jsonify({"error": "Email address already registered"}), 400

    allowed_emails_str = os.environ.get('ALLOWED_EMAILS', '')
    # Convert allowed emails to lowercase for case-insensitive comparison
    allowed_emails = [
        e.strip().lower() for e in allowed_emails_str.split(',') if e.strip()
    ]
    is_whitelisted = email in allowed_emails

    new_user = User(email=email, name=name, is_whitelisted=is_whitelisted)
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        "message": "User registered successfully",
        "user_id": new_user.id,
        "email": new_user.email,
        "is_whitelisted": new_user.is_whitelisted
    }), 201


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    raw_email = data.get('email')
    password = data.get('password')

    if not raw_email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    email_to_check = raw_email.lower()  # Convert to lowercase for lookup

    # Case-insensitive email lookup
    user = User.query.filter(
        db.func.lower(User.email) == email_to_check).first()

    if user and user.check_password(password):
        if not user.is_whitelisted:
            return jsonify({"error":
                            "Access denied. User not whitelisted."}), 403

        login_user(user)
        return jsonify({
            "message": "Logged in successfully",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "is_whitelisted": user.is_whitelisted
            }
        }), 200

    return jsonify({"error": "Invalid email or password"}), 401


@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"}), 200


@app.route('/api/check_auth', methods=['GET'])
def check_auth_status():
    if current_user.is_authenticated:
        return jsonify({
            "isAuthenticated": True,
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "name": current_user.name,
                "is_whitelisted": current_user.is_whitelisted
            }
        }), 200
    else:
        return jsonify({"isAuthenticated": False}), 401


@app.route('/api/check_db', methods=['GET'])
def check_db_connection():
    """Route to check database connection status"""
    success, error_message = verify_db_connection()
    return jsonify({
        "success":
        success,
        "message":
        "Database connection successful"
        if success else f"Database connection error: {error_message}"
    }), 200 if success else 500


# Initialize streaming endpoints
# openai_client is imported from simple_agent earlier in the file
stream_bp = create_stream_blueprint(
    app, openai_client)  # Pass app and openai_client
app.register_blueprint(stream_bp)  # Register the blueprint

# The old PASSWORD var and 'from flask import session' might still be needed by other parts of the app.
# We will address removing them later if they become fully obsolete.


@app.route('/chat', methods=['POST'])
@login_required
def chat():
    # Get the message and conversation history from the request
    data = request.json

    conv_id = data.get('conv_id')
    
    # Handle conversation creation or retrieval
    if not conv_id:
        # Create a new conversation
        try:
            # Generate a title for the new conversation using the responses API
            # Use synchronous approach for Flask compatibility
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            title = loop.run_until_complete(generate_conversation_title(data.get('message', '')))
            loop.close()
        except Exception as e:
            print(f"Error generating title with responses API: {e}")
            # Fallback to default title if responses API fails
            title = f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Generate a unique filename using UUID to avoid uniqueness constraint violations
        unique_filename = f"{uuid.uuid4()}.json"
        
        # Create new conversation in database with unique filename
        new_conversation = Conversation(
            title=title, 
            user_id=current_user.id,
            filename=unique_filename  # Use UUID to ensure uniqueness
        )
        db.session.add(new_conversation)
        db.session.commit()
        conv_id = new_conversation.id
    else:
        # Verify the conversation belongs to the current user
        conversation = Conversation.query.filter_by(
            id=conv_id, user_id=current_user.id).first_or_404()
    
    # Add user message to database - removed user_id as it's not in the Message model
    user_message = Message(
        conv_id=conv_id, 
        role='user', 
        content=data.get('message', '')
    )
    db.session.add(user_message)
    db.session.commit()
    
    # Retrieve conversation history
    messages = Message.query.filter_by(conv_id=conv_id).order_by(Message.created_at.asc()).all()
    history = [{'role': msg.role, 'content': msg.content} for msg in messages]

    # Run the agent in an async loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Create a task that can be cancelled
    task = None
    try:
        print(f"Processing chat request with message: {data.get('message','')[:50]}...")
        
        # Run the responses agent and collect results
        result = {'steps': []}
        try:
            async def collect_results():
                nonlocal result
                final_output = ""
                steps = []
                user_id = str(current_user.id)  # Ensure user_id is a string
                user_message = data.get('message', '')
                response_id = None
                
                # Use the new responses agent implementation
                async for chunk in run_responses_agent(
                    user_message,
                    history,
                    user_id=user_id
                ):
                    if chunk.get('type') == 'content':
                        if 'delta' in chunk:
                            final_output += chunk['delta']
                        elif 'result' in chunk:
                            try:
                                parsed = json.loads(chunk['result'])
                                if 'content' in parsed:
                                    final_output = parsed['content']
                                if 'steps' in parsed:
                                    steps = parsed['steps']
                                if 'response_id' in parsed:
                                    response_id = parsed['response_id']
                            except:
                                pass
                    elif chunk.get('type') in ['tool', 'tool_result']:
                        steps.append(chunk)
                
                return {
                    'final_output': final_output,
                    'steps': steps,
                    'suggestions': [],
                    'response_id': response_id
                }

            task = loop.create_task(collect_results())
            result = loop.run_until_complete(task)
        except asyncio.CancelledError:
            # On cancellation, ensure task is properly cancelled
            if task and not task.done():
                task.cancel()
                try:
                    loop.run_until_complete(task)
                except asyncio.CancelledError:
                    pass

            # Return response with conversation ID preserved
            return jsonify({
                'response': 'Request cancelled by user.',
                'conv_id': conv_id,
                'suggestions': [],
                'steps': 0,
                'tool_calls': []
            })
        finally:
            if task and not task.done():
                task.cancel()
                try:
                    loop.run_until_complete(task)
                except asyncio.CancelledError:
                    pass

        # Extract tool calls for debugging
        steps_list = result.get('steps', [])
        tool_calls = []
        for idx, step in enumerate(steps_list):
            if step.get('type') == 'tool':
                name = step.get('name')
                inp = step.get('input')
                output_raw = None
                # check for matching tool_result
                if idx + 1 < len(steps_list) and steps_list[idx + 1].get(
                        'type') == 'tool_result' and steps_list[idx + 1].get(
                            'name') == name:
                    output_raw = steps_list[idx + 1].get('output')
                # ensure JSON-serializable
                if not isinstance(
                        output_raw,
                    (str, int, float, bool, list, dict, type(None))):
                    output = str(output_raw)
                else:
                    output = output_raw
                tool_calls.append({
                    'tool_name': name,
                    'input': inp,
                    'output': output
                })

        # Return the agent's response and debug info
        final_output = result.get(
            'final_output', result.get('response', 'No response available'))
        
        # Add assistant message to database - removed user_id as it's not in the Message model
        assistant_message = Message(
            conv_id=conv_id, 
            role='assistant', 
            content=final_output
        )
        db.session.add(assistant_message)
        db.session.commit()
        
        return jsonify({
            'conv_id': conv_id,
            'response': final_output,
            'steps': len(result['steps']),
            'tool_calls': tool_calls,
            'suggestions': result.get('suggestions', []),
            'response_id': result.get('response_id')
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


@app.route('/conversations', methods=['GET'])
@login_required
def list_conversations():
    # Fetch conversations for the currently logged-in user
    user_conversations = Conversation.query.filter_by(
        user_id=current_user.id).order_by(
            Conversation.created_at.desc()).all()
    return jsonify([{
        'id':
        conv.id,
        'title':
        conv.title,
        'created_at':
        conv.created_at.isoformat() if conv.created_at else None
    } for conv in user_conversations])


@app.route('/conversations/<int:conv_id>', methods=['GET'])
@login_required
def get_conversation(conv_id):
    # First, get the conversation and verify it belongs to the current user
    conversation = Conversation.query.filter_by(
        id=conv_id, user_id=current_user.id).first_or_404()

    # Then, get all messages for that conversation, ordered by creation time
    messages = Message.query.filter_by(conv_id=conversation.id).order_by(
        Message.created_at.asc()).all()

    return jsonify([{
        'role':
        msg.role,
        'content':
        msg.content,
        'timestamp':
        msg.created_at.isoformat() if msg.created_at else None,
        'tool_call_id':
        msg.tool_call_id,
        'tool_name':
        msg.tool_name
    } for msg in messages])


@app.route('/conversations/<int:conv_id>', methods=['DELETE'])
@login_required
def delete_conversation(conv_id):
    conversation = Conversation.query.filter_by(
        id=conv_id, user_id=current_user.id).first_or_404()

    # Messages associated with this conversation will be deleted automatically
    # due to the cascade="all, delete-orphan" setting in the Conversation.messages relationship.
    db.session.delete(conversation)
    db.session.commit()

    return jsonify({"message": "Conversation deleted successfully"}), 200


@app.route('/conversations/<int:conv_id>/title', methods=['PUT'])
@login_required
def update_conversation_title(conv_id):
    data = request.get_json()
    new_title = data.get('title')

    if not new_title:
        return jsonify({"error": "Title is required"}), 400

    conversation = Conversation.query.filter_by(
        id=conv_id, user_id=current_user.id).first_or_404()
    conversation.title = new_title
    db.session.commit()

    return jsonify({"message": "Conversation title updated successfully"}), 200


if __name__ == '__main__':
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()

    # Run the app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
