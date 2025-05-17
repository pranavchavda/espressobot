import os
import asyncio
import json
from flask import Flask, request, Response, stream_with_context, jsonify
from simple_agent import run_simple_agent
from database import get_db

def create_stream_blueprint(app):
    @app.route('/stream_chat', methods=['POST'])
    def stream_chat():
        data = request.json
        conv_id = data.get('conv_id')
        message = data.get('message', '')

        # Insert user message into database
        db = get_db()
        if not conv_id:
            # Create new conversation
            cur = db.execute('INSERT INTO conversations DEFAULT VALUES')
            conv_id = cur.lastrowid
            db.commit()

            # Generate a title for the new conversation
            try:
                from simple_agent import client as openai_client
                title_resp = openai_client.chat.completions.create(
                    model=os.environ.get('DEFAULT_MODEL', 'gpt-4.1-nano'),
                    messages=[
                        {'role': 'system', 'content': 'You are an assistant that generates concise conversation titles.'},
                        {'role': 'user', 'content': f"Generate a short title (max 5 words) for a conversation starting with: {message}"}
                    ]
                )
                title = title_resp.choices[0].message.content.strip()
            except Exception:
                title = f"Conversation {conv_id}"

            db.execute('UPDATE conversations SET title = ? WHERE id = ?', (title, conv_id))
            db.commit()

        # Insert user message
        db.execute(
            'INSERT INTO messages (conv_id, role, content) VALUES (?, ?, ?)',
            (conv_id, 'user', message)
        )
        db.commit()

        # Prepare history for the agent
        rows = db.execute(
            'SELECT role, content FROM messages WHERE conv_id = ? ORDER BY id',
            (conv_id,)
        ).fetchall()
        history = [{'role': r['role'], 'content': r['content']} for r in rows]

        # Set up streaming response
        def generate():
            # Initial JSON data with conversation ID
            yield f"data: {{\n"
            yield f"data: \"conv_id\": {conv_id},\n"
            yield f"data: \"streaming\": true,\n"
            yield f"data: \"content\": \"\",\n"
            yield f"data: \"suggestions\": [],\n"
            yield f"data: \"tool_calls\": []\n"
            yield f"data: }}\n\n"

            # Create async event loop for the agent
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Set up for incremental streaming
            full_response = ""
            try:
                # Run agent in async mode
                async def process_agent():
                    nonlocal full_response

                    # Run the agent with streaming=True
                    async for chunk in run_simple_agent(message, history, streaming=True):
                        if chunk.get('type') == 'content':
                            delta = chunk.get('delta', '')
                            full_response += delta
                            yield f"data: {{\n"
                            yield f"data: \"delta\": {json.dumps(delta)},\n"
                            yield f"data: \"content\": {json.dumps(full_response)}\n"
                            yield f"data: }}\n\n"
                        elif chunk.get('type') == 'tool_call':
                            # Send tool call information
                            yield f"data: {{\n"
                            yield f"data: \"tool_call\": {json.dumps(chunk)}\n"
                            yield f"data: }}\n\n"
                        elif chunk.get('type') == 'suggestions' and chunk.get('suggestions'):
                            # Send suggestions when available
                            yield f"data: {{\n"
                            yield f"data: \"suggestions\": {json.dumps(chunk.get('suggestions', []))}\n"
                            yield f"data: }}\n\n"

                # Define the async generator function
                async def process_agent():
                    nonlocal full_response
                    # Run the agent with streaming=True
                    async for chunk in run_simple_agent(message, history, streaming=True):
                        if chunk.get('type') == 'content':
                            delta = chunk.get('delta', '')
                            full_response += delta
                            yield f"data: {{\n"
                            yield f"data: \"delta\": {json.dumps(delta)},\n"
                            yield f"data: \"content\": {json.dumps(full_response)}\n"
                            yield f"data: }}\n\n"
                        elif chunk.get('type') == 'tool_call':
                            # Send tool call information
                            yield f"data: {{\n"
                            yield f"data: \"tool_call\": {json.dumps(chunk)}\n"
                            yield f"data: }}\n\n"
                        elif chunk.get('type') == 'suggestions' and chunk.get('suggestions'):
                            # Send suggestions when available
                            yield f"data: {{\n"
                            yield f"data: \"suggestions\": {json.dumps(chunk.get('suggestions', []))}\n"
                            yield f"data: }}\n\n"
                
                # Use asyncio to run the async generator and yield its results
                for chunk in loop.run_until_complete(collect_async_generator(process_agent())):
                    yield chunk
                
                # Helper function to collect results from async generator
                async def collect_async_generator(agen):
                    results = []
                    async for item in agen:
                        results.append(item)
                    return results

                # Store the final response in the database
                if full_response:
                    db.execute(
                        'INSERT INTO messages (conv_id, role, content) VALUES (?, ?, ?)',
                        (conv_id, 'assistant', full_response)
                    )
                    db.commit()

                # Send completion message
                yield f"data: {{\n"
                yield f"data: \"done\": true\n"
                yield f"data: }}\n\n"

            except Exception as e:
                import traceback
                error_traceback = traceback.format_exc()
                print(f"ERROR in /stream_chat route: {str(e)}")
                print(error_traceback)

                # Send error message
                yield f"data: {{\n"
                yield f"data: \"error\": {json.dumps(str(e))}\n"
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

    return app