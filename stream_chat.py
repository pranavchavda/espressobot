"""
Implementation of streaming chat functionality using the OpenAI responses API.
This module provides a Flask blueprint for streaming chat responses with the responses API.
"""
import os
import asyncio
import json
import uuid
import datetime
import logging
from flask import current_app, request, Response, stream_with_context, jsonify, Blueprint
from flask_login import current_user, login_required

# Import db from extensions module
from extensions import db

# Import models from the new models.py file
from models import Conversation, Message, User

# Import the responses agent
from responses_agent import run_responses_agent, generate_conversation_title

# Configure logging
logger = logging.getLogger(__name__)

def create_stream_blueprint(app, openai_client):
    stream_bp = Blueprint('stream_chat', __name__)

    @stream_bp.route('/stream_chat', methods=['POST'])
    @login_required
    def stream_chat():
        data = request.json
        conv_id = data.get('conv_id')
        message_text = data.get('message', '')

        conversation = None
        if conv_id:
            conversation = db.session.get(Conversation, conv_id)
            if not conversation or conversation.user_id != current_user.id:
                conv_id = None
                conversation = None

        if not conv_id:
            title_to_set = f"Chat from {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            try:
                loop_for_title = asyncio.new_event_loop()
                asyncio.set_event_loop(loop_for_title)

                async def get_title_async():
                    # Use the responses API for title generation
                    return await generate_conversation_title(message_text)

                generated_title = loop_for_title.run_until_complete(get_title_async())
                if generated_title:
                    title_to_set = generated_title
                loop_for_title.close()
            except Exception as e:
                logger.error(f"Error generating title: {e}")
                if 'loop_for_title' in locals() and not loop_for_title.is_closed():
                    loop_for_title.close()

            unique_filename = f"{uuid.uuid4()}.json"

            conversation = Conversation(
                user_id=current_user.id,
                title=title_to_set,
                filename=unique_filename
            )
            db.session.add(conversation)
            db.session.commit()
            conv_id = conversation.id

        user_message = Message(conv_id=conv_id, role='user', content=message_text)
        db.session.add(user_message)
        db.session.commit()

        messages_from_db = Message.query.filter_by(conv_id=conv_id).order_by(Message.created_at).all()
        history = [{'role': msg.role, 'content': msg.content} for msg in messages_from_db]

        def generate():
            yield f"data: {{\n"
            yield f"data: \"conv_id\": {conv_id},\n"
            yield f"data: \"streaming\": true,\n"
            yield f"data: \"content\": \"\",\n"
            yield f"data: \"suggestions\": [],\n"
            yield f"data: \"tool_calls\": []\n"
            yield f"data: }}\n\n"

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            full_response = ""
            final_assistant_message_content = None
            active_tool_calls = {}
            
            try:
                async def process_agent():
                    nonlocal full_response, final_assistant_message_content, active_tool_calls
                    # Get user's ID for user-specific memory
                    user_id = str(current_user.id)
                    
                    # Use the responses agent instead of simple_agent
                    logger.info(f"Starting responses agent for user {user_id} with message: {message_text[:50]}...")
                    
                    async for chunk in run_responses_agent(message_text, history, user_id=user_id):
                        logger.info(f"Received chunk type: {chunk.get('type')}")
                        
                        # Handle different types of chunks
                        if chunk.get('type') == 'content':
                            # Handle both delta and result content types
                            if 'delta' in chunk:
                                delta = chunk.get('delta', '')
                                if delta:  # Only process non-empty deltas
                                    full_response += delta
                                    yield f"data: {{\n"
                                    yield f"data: \"delta\": {json.dumps(delta)},\n"
                                    yield f"data: \"content\": {json.dumps(full_response)}\n"
                                    yield f"data: }}\n\n"
                            elif 'result' in chunk:
                                try:
                                    result = json.loads(chunk['result'])
                                    if 'content' in result:
                                        final_assistant_message_content = result['content']
                                        # Also send this as a delta to ensure UI gets it
                                        if final_assistant_message_content and final_assistant_message_content != full_response:
                                            yield f"data: {{\n"
                                            yield f"data: \"delta\": {json.dumps(final_assistant_message_content)},\n"
                                            yield f"data: \"content\": {json.dumps(final_assistant_message_content)}\n"
                                            yield f"data: }}\n\n"
                                except Exception as e:
                                    logger.error(f"Error parsing result: {e}")
                        
                        # Handle tool calls - both standard and function call arguments delta events
                        elif chunk.get('type') == 'tool' or 'function_call' in str(chunk.get('type', '')):
                            # For standard tool calls
                            if chunk.get('type') == 'tool':
                                tool_data = {
                                    "name": chunk.get('name', ''),
                                    "input": chunk.get('input', {})
                                }
                                yield f"data: {{\n"
                                yield f"data: \"tool_call\": {json.dumps(chunk)}\n"
                                yield f"data: }}\n\n"
                            
                            # For function call arguments delta events (from ResponseFunctionCallArgumentsDeltaEvent)
                            elif 'function_call' in str(chunk.get('type', '')):
                                # These need special handling as they come in pieces
                                if 'id' in chunk:
                                    call_id = chunk.get('id')
                                    if call_id not in active_tool_calls:
                                        active_tool_calls[call_id] = {
                                            "name": chunk.get('name', ''),
                                            "arguments": ""
                                        }
                                    
                                    # Accumulate arguments
                                    if 'arguments' in chunk:
                                        active_tool_calls[call_id]["arguments"] += chunk.get('arguments', '')
                                    
                                    # Send the updated tool call
                                    tool_data = {
                                        "id": call_id,
                                        "name": active_tool_calls[call_id]["name"],
                                        "input": active_tool_calls[call_id]["arguments"]
                                    }
                                    yield f"data: {{\n"
                                    yield f"data: \"tool_call\": {json.dumps(tool_data)}\n"
                                    yield f"data: }}\n\n"
                        
                        # Handle tool results
                        elif chunk.get('type') == 'tool_result':
                            # Send tool results to the frontend
                            yield f"data: {{\n"
                            yield f"data: \"tool_result\": {json.dumps(chunk)}\n"
                            yield f"data: }}\n\n"
                        
                        # Handle suggestions
                        elif chunk.get('type') == 'suggestions' and chunk.get('suggestions'):
                            yield f"data: {{\n"
                            yield f"data: \"suggestions\": {json.dumps(chunk.get('suggestions', []))}\n"
                            yield f"data: }}\n\n"
                        
                        # Handle any other event types by logging them
                        else:
                            logger.info(f"Unhandled chunk type: {chunk.get('type')}")

                async_gen = process_agent()
                while True:
                    try:
                        chunk = loop.run_until_complete(async_gen.__anext__())
                        yield chunk
                    except StopAsyncIteration:
                        break
                    except Exception as e_agen: # Catch exceptions from the async generator itself
                        logger.error(f"Error during async_gen iteration: {e_agen}")
                        yield f"data: {{\"error\": {json.dumps(str(e_agen))}}}\n\n"
                        break # Stop streaming on error within the generator

                logger.info(f"Final response content: {final_assistant_message_content[:100] if final_assistant_message_content else 'None'}...")
                
                # If we don't have a final message content but we have accumulated a full response,
                # use that instead
                if not final_assistant_message_content and full_response:
                    final_assistant_message_content = full_response
                
                # Clean the content to remove thinking tags
                if final_assistant_message_content:
                    import re
                    # Remove <THINKING>...</THINKING> blocks
                    final_assistant_message_content = re.sub(r'<THINKING>.*?</THINKING>', '', 
                                                           final_assistant_message_content, 
                                                           flags=re.DOTALL)
                    # Remove any remaining tags
                    final_assistant_message_content = re.sub(r'<[^>]+>', '', final_assistant_message_content)
                    final_assistant_message_content = final_assistant_message_content.strip()
                    
                    # Save to database
                    assistant_message = Message(conv_id=conv_id, role='assistant', content=final_assistant_message_content)
                    db.session.add(assistant_message)
                    db.session.commit()
                    logger.info(f"Saved assistant message to database: {final_assistant_message_content[:100]}...")

                yield f"data: {{\n"
                yield f"data: \"done\": true\n"
                yield f"data: }}\n\n"
            except Exception as e:
                import traceback
                error_traceback = traceback.format_exc()
                logger.error(f"ERROR in /stream_chat route: {str(e)}")
                logger.error(error_traceback)
                # Yield the full error and traceback to the client for debugging
                yield f"data: {{\n"
                yield f"data: \"error\": {json.dumps(str(e))},\n"
                yield f"data: \"traceback\": {json.dumps(error_traceback)}\n"
                yield f"data: }}\n\n"
            finally:
                loop.close()

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )

    return stream_bp
