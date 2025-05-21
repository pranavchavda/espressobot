import os
import asyncio
import json
import uuid
import datetime
from flask import current_app, request, Response, stream_with_context, jsonify, Blueprint
from flask_login import current_user, login_required

# Import db from extensions module
from extensions import db

# Import models from the new models.py file
from models import Conversation, Message, User

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
                    return await openai_client.chat.completions.create(
                        model=os.environ.get('DEFAULT_MODEL', 'gpt-4.1-nano'),
                        messages=[
                            {'role': 'system', 'content': 'You are an assistant that generates concise conversation titles.'},
                            {'role': 'user', 'content': f"Generate a short title (max 5 words) for a conversation starting with: {message_text}"}
                        ],
                        max_tokens=20
                    )

                title_resp = loop_for_title.run_until_complete(get_title_async())
                generated_title = title_resp.choices[0].message.content.strip()
                if generated_title:
                    title_to_set = generated_title
                loop_for_title.close()
            except Exception as e:
                print(f"Error generating title: {e}")
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
            try:
                async def process_agent():
                    nonlocal full_response, final_assistant_message_content
                    from simple_agent import run_simple_agent
                    # Get user's name and bio
                    user_name = current_user.name
                    user_bio = current_user.bio
                    # Pass the user_id for user-specific memory
                    user_id = current_user.id
                    async for chunk in run_simple_agent(message_text, user_name, user_bio, history, streaming=True, user_id=user_id):
                        if chunk.get('type') == 'content':
                            delta = chunk.get('delta', '')
                            full_response += delta
                            yield f"data: {{\n"
                            yield f"data: \"delta\": {json.dumps(delta)},\n"
                            yield f"data: \"content\": {json.dumps(full_response)}\n"
                            yield f"data: }}\n\n"
                        elif chunk.get('type') == 'tool_call':
                            yield f"data: {{\n"
                            yield f"data: \"tool_call\": {json.dumps(chunk)}\n"
                            yield f"data: }}\n\n"
                        elif chunk.get('type') == 'suggestions' and chunk.get('suggestions'):
                            yield f"data: {{\n"
                            yield f"data: \"suggestions\": {json.dumps(chunk.get('suggestions', []))}\n"
                            yield f"data: }}\n\n"
                        elif chunk.get('type') == 'final':
                            final_assistant_message_content = chunk.get('content', '')

                async_gen = process_agent()
                while True:
                    try:
                        chunk = loop.run_until_complete(async_gen.__anext__())
                        yield chunk
                    except StopAsyncIteration:
                        break
                    except Exception as e_agen: # Catch exceptions from the async generator itself
                        print(f"Error during async_gen iteration: {e_agen}")
                        yield f"data: {{\"error\": {json.dumps(str(e_agen))}}}\n\n"
                        break # Stop streaming on error within the generator

                print(f"DEBUG stream_chat.py: final_assistant_message_content BEFORE save: '{final_assistant_message_content}'") # DEBUG
                if final_assistant_message_content:
                    assistant_message = Message(conv_id=conv_id, role='assistant', content=final_assistant_message_content)
                    db.session.add(assistant_message)
                    db.session.commit()

                yield f"data: {{\n"
                yield f"data: \"done\": true\n"
                yield f"data: }}\n\n"
            except Exception as e:
                import traceback
                error_traceback = traceback.format_exc()
                print(f"ERROR in /stream_chat route: {str(e)}")
                print(error_traceback)
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