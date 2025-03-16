"""
OpenAI API Logger

This module provides logging functionality for OpenAI API calls.
It captures request details, token counts, and other relevant information
to help debug context length issues and analyze API usage.
"""

import os
import json
import logging
import datetime
from pathlib import Path
import tiktoken
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create a logger for this module
logger = logging.getLogger('openai_logger')

# Set up file handler for detailed logs
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)
file_handler = logging.FileHandler(log_dir / 'openai_api.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Check if logging is enabled via environment variable
OPENAI_LOG_API_REQUESTS = os.environ.get('OPENAI_LOG_API_REQUESTS', 'true').lower() == 'true'

def count_tokens(messages, model="gpt-4o"):
    """
    Count the number of tokens in a list of messages.
    
    Args:
        messages (list): List of message dictionaries with 'role' and 'content' keys
        model (str): The model name to use for token counting
        
    Returns:
        int: Estimated token count
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fall back to cl100k_base encoding if model-specific encoding not found
        encoding = tiktoken.get_encoding("cl100k_base")
    
    num_tokens = 0
    
    # Count tokens in each message
    for message in messages:
        # Add tokens for message role
        num_tokens += 4  # Every message follows <im_start>{role/name}\n{content}<im_end>\n
        
        # Add tokens for content
        if "content" in message and message["content"]:
            num_tokens += len(encoding.encode(message["content"]))
            
        # Add tokens for name if present
        if "name" in message:
            num_tokens += len(encoding.encode(message["name"]))
            
        # Add tokens for function_call if present
        if "function_call" in message:
            function_call = message["function_call"]
            if isinstance(function_call, dict):
                if "name" in function_call:
                    num_tokens += len(encoding.encode(function_call["name"]))
                if "arguments" in function_call:
                    num_tokens += len(encoding.encode(function_call["arguments"]))
    
    # Add tokens for the formatting of the messages
    num_tokens += 2  # Every reply is primed with <im_start>assistant
    
    return num_tokens

def count_tool_tokens(tools):
    """
    Count the number of tokens in a list of tools.
    
    Args:
        tools (list): List of tool dictionaries
        
    Returns:
        int: Estimated token count
    """
    if not tools:
        return 0
        
    try:
        encoding = tiktoken.encoding_for_model("gpt-4o")
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    
    tools_string = json.dumps(tools)
    return len(encoding.encode(tools_string))

def truncate_content(content, max_length=500):
    """
    Truncate content to a maximum length and add ellipsis if needed.
    
    Args:
        content (str): The content to truncate
        max_length (int): Maximum length in characters
        
    Returns:
        str: Truncated content
    """
    if not content or len(content) <= max_length:
        return content
    return content[:max_length] + "..."

def log_openai_request(model, messages, tools=None, **kwargs):
    """
    Log an OpenAI API request with token counts and other details.
    
    Args:
        model (str): The model name
        messages (list): List of message dictionaries
        tools (list, optional): List of tool dictionaries
        **kwargs: Additional parameters passed to the API
    """
    if not OPENAI_LOG_API_REQUESTS:
        return
    
    # Calculate token counts
    message_token_count = count_tokens(messages, model)
    tool_token_count = count_tool_tokens(tools) if tools else 0
    total_token_count = message_token_count + tool_token_count
    
    # Create a summary of the messages
    message_summary = []
    for msg in messages:
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        
        # For system and user messages, include truncated content
        if role in ['system', 'user']:
            message_summary.append({
                'role': role,
                'content_preview': truncate_content(content),
                'content_length': len(content) if content else 0
            })
        # For other message types, just include the role and length
        else:
            message_summary.append({
                'role': role,
                'content_length': len(content) if content else 0
            })
    
    # Create a summary of the tools if present
    tool_summary = None
    if tools:
        tool_summary = []
        for tool in tools:
            if 'function' in tool:
                function_info = tool['function']
                tool_summary.append({
                    'type': 'function',
                    'name': function_info.get('name', 'unknown'),
                    'description_length': len(function_info.get('description', ''))
                })
    
    # Create the log entry
    log_entry = {
        'timestamp': datetime.datetime.now().isoformat(),
        'model': model,
        'token_counts': {
            'messages': message_token_count,
            'tools': tool_token_count,
            'total': total_token_count
        },
        'message_count': len(messages),
        'message_summary': message_summary,
        'tool_summary': tool_summary,
        'additional_params': {k: v for k, v in kwargs.items() if k not in ['model', 'messages', 'tools']}
    }
    
    # Log a summary to the console
    logger.info(f"OpenAI API Request: {model}, {total_token_count} tokens ({message_token_count} in messages, {tool_token_count} in tools)")
    
    # Log the full details to the file
    logger.debug(f"OpenAI API Request Details: {json.dumps(log_entry, indent=2)}")
    
    # Write the full log entry to the detailed log file
    with open(log_dir / 'openai_api_detailed.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry) + '\n')
    
    # Check if we're approaching the token limit
    if total_token_count > 120000:  # 90% of the 128k limit
        logger.warning(f"⚠️ Approaching token limit: {total_token_count}/128000 tokens")

def log_openai_response(response):
    """
    Log an OpenAI API response with usage information.
    
    Args:
        response: The response object from the OpenAI API
    """
    if not OPENAI_LOG_API_REQUESTS:
        return
    
    # Extract usage information if available
    usage = None
    if hasattr(response, 'usage'):
        usage = {
            'prompt_tokens': response.usage.prompt_tokens,
            'completion_tokens': response.usage.completion_tokens,
            'total_tokens': response.usage.total_tokens
        }
    
    # Create the log entry
    log_entry = {
        'timestamp': datetime.datetime.now().isoformat(),
        'model': response.model if hasattr(response, 'model') else 'unknown',
        'id': response.id if hasattr(response, 'id') else 'unknown',
        'usage': usage
    }
    
    # Log a summary to the console
    if usage:
        logger.info(f"OpenAI API Response: {log_entry['model']}, {usage['total_tokens']} tokens used ({usage['prompt_tokens']} prompt, {usage['completion_tokens']} completion)")
    else:
        logger.info(f"OpenAI API Response: {log_entry['model']}, usage information not available")
    
    # Log the full details to the file
    logger.debug(f"OpenAI API Response Details: {json.dumps(log_entry, indent=2)}")
    
    # Write the full log entry to the detailed log file
    with open(log_dir / 'openai_api_detailed.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry) + '\n')

def openai_logging_wrapper(func):
    """
    Decorator to add logging to OpenAI API calls.
    
    Args:
        func: The function to wrap
        
    Returns:
        function: The wrapped function with logging
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Log the request
        model = kwargs.get('model', 'unknown')
        messages = kwargs.get('messages', [])
        tools = kwargs.get('tools', None)
        
        # Create a copy of kwargs without 'model', 'messages', and 'tools' to avoid duplicate parameters
        filtered_kwargs = {k: v for k, v in kwargs.items() if k not in ['model', 'messages', 'tools']}
        log_openai_request(model, messages, tools, **filtered_kwargs)
        
        # Call the original function
        response = func(*args, **kwargs)
        
        # Log the response
        log_openai_response(response)
        
        return response
    
    return wrapper 