"""
Test script to directly test the OpenAI responses API outside of the Flask application.
This helps isolate API connectivity and authentication issues.
"""
import os
import json
import asyncio
from openai import OpenAI, AsyncOpenAI

# Configure logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
async_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

def test_sync_responses_api():
    """Test the OpenAI responses API using synchronous client."""
    logger.info("Testing synchronous OpenAI responses API...")
    
    try:
        # Print the API key (first few chars) for debugging
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            logger.info(f"Using API key: {api_key[:5]}...{api_key[-4:]}")
        else:
            logger.error("API key not found in environment variables")
            return
            
        # Print the model being used
        model = "gpt-4.1-mini"  # Use gpt-4.1-mini as requested
        logger.info(f"Using model: {model}")
        
        # Make a simple API call
        response = client.responses.create(
            model=model,
            instructions="You are a helpful assistant.",
            input="Hello, can you help me with a product?",
        )
        
        # Log the response
        logger.info(f"Response ID: {response.id}")
        logger.info(f"Response output: {response.output_text}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in test_sync_responses_api: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

async def test_async_responses_api():
    """Test the OpenAI responses API using asynchronous client."""
    logger.info("Testing asynchronous OpenAI responses API...")
    
    try:
        # Print the API key (first few chars) for debugging
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            logger.info(f"Using API key: {api_key[:5]}...{api_key[-4:]}")
        else:
            logger.error("API key not found in environment variables")
            return
            
        # Print the model being used
        model = "gpt-4.1-mini"  # Use gpt-4.1-mini as requested
        logger.info(f"Using model: {model}")
        
        # Make a simple API call
        response = await async_client.responses.create(
            model=model,
            instructions="You are a helpful assistant.",
            input="Hello, can you help me with a product?",
        )
        
        # Log the response
        logger.info(f"Response ID: {response.id}")
        logger.info(f"Response output: {response.output_text}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in test_async_responses_api: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

async def test_streaming_responses_api():
    """Test the OpenAI responses API with streaming."""
    logger.info("Testing streaming OpenAI responses API...")
    
    try:
        # Print the API key (first few chars) for debugging
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            logger.info(f"Using API key: {api_key[:5]}...{api_key[-4:]}")
        else:
            logger.error("API key not found in environment variables")
            return
            
        # Print the model being used
        model = "gpt-4.1-mini"  # Use gpt-4.1-mini as requested
        logger.info(f"Using model: {model}")
        
        # Make a streaming API call
        stream = await async_client.responses.create(
            model=model,
            instructions="You are a helpful assistant.",
            input="Hello, can you help me with a product?",
            stream=True,
        )
        
        # Process the streaming response
        response_id = None
        content = ""
        
        async for chunk in stream:
            # Log the chunk type
            logger.info(f"Chunk type: {type(chunk).__name__}")
            
            # Handle different types of events
            if hasattr(chunk, 'id') and not response_id:
                response_id = chunk.id
                logger.info(f"Response ID: {response_id}")
            
            # Check for output_text attribute and log it
            if hasattr(chunk, 'output_text') and chunk.output_text:
                content += chunk.output_text
                logger.info(f"Content delta: {chunk.output_text}")
            
            # For ResponseTextDeltaEvent, check the delta attribute
            if type(chunk).__name__ == 'ResponseTextDeltaEvent' and hasattr(chunk, 'delta'):
                content += chunk.delta
                logger.info(f"Text delta: {chunk.delta}")
        
        logger.info(f"Final content: {content}")
        
    except Exception as e:
        logger.error(f"Error in test_streaming_responses_api: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    # Run the synchronous test
    sync_response = test_sync_responses_api()
    
    # Run the asynchronous tests
    asyncio.run(test_async_responses_api())
    asyncio.run(test_streaming_responses_api())
