"""
Client for making requests to OpenAI API.
"""
import logging
import json
import os
import openai
from openai import OpenAI
import config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Remove hardcoded key
DEFAULT_OPENAI_API_KEY = ""  # Empty string as fallback

def call_openai_api(api_request):
    """
    Call the OpenAI API with the formatted request.
    """
    # Use the API key from config, environment, or default
    api_key = config.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        logger.error("OpenAI API key not found")
        return {"error": "API key not configured"}
    
    # Rest of function remains the same        
    try:
        logger.info("Calling OpenAI API...")
        
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model=api_request.get("model", "gpt-3.5-turbo"),
            messages=api_request.get("messages", []),
            temperature=api_request.get("temperature", 0),
            max_tokens=api_request.get("max_tokens", 1000)
        )
        
        # Format the response to be more usable
        formatted_response = {
            "id": response.id,
            "model": response.model,
            "content": response.choices[0].message.content,
            "finish_reason": response.choices[0].finish_reason,
            "usage": {
                "completion_tokens": response.usage.completion_tokens,
                "prompt_tokens": response.usage.prompt_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
        
        logger.info(f"OpenAI API call successful: used {formatted_response['usage']['total_tokens']} tokens")
        return formatted_response
    except Exception as e:
        error_message = f"Exception calling OpenAI API: {str(e)}"
        logger.error(error_message)
        return {"error": error_message}

def call_llm_api(api_request, provider=None):
    """
    Call the appropriate LLM API based on provider.
    
    Args:
        api_request: Formatted API request
        provider: LLM provider (currently only supports "openai")
        
    Returns:
        API response
    """
    # For now, only support OpenAI
    return call_openai_api(api_request)