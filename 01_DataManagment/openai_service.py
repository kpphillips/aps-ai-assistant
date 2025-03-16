"""
OpenAI Service Wrapper

This module provides a wrapper around the OpenAI client to add logging functionality.
It's designed to be a drop-in replacement for the OpenAI client in the existing code.
"""

from openai import OpenAI
from openai_logger import openai_logging_wrapper

class OpenAIServiceWrapper:
    """
    A wrapper around the OpenAI client that adds logging functionality.
    """
    
    def __init__(self, client=None):
        """
        Initialize the wrapper with an optional client.
        
        Args:
            client (OpenAI, optional): An existing OpenAI client to wrap.
                If not provided, a new client will be created.
        """
        self.client = client or OpenAI()
        
        # Wrap the chat.completions.create method with logging
        self.client.chat.completions.create = openai_logging_wrapper(
            self.client.chat.completions.create
        )
    
    def __getattr__(self, name):
        """
        Pass through any attribute access to the wrapped client.
        
        Args:
            name (str): The name of the attribute to access
            
        Returns:
            Any: The attribute from the wrapped client
        """
        return getattr(self.client, name)

# Create a singleton instance for easy import
service = OpenAIServiceWrapper()

def get_openai_client():
    """
    Get the wrapped OpenAI client with logging functionality.
    
    Returns:
        OpenAI: The wrapped OpenAI client
    """
    return service.client 