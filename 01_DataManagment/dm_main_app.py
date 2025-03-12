''' Main script for Data Management APIs with function calling '''
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

from dm_0_config import MODEL_NAME, MODEL_CONFIG
from dm_1_prompts import DATA_MANAGEMENT_PROMPT
from dm_3_helpers import get_hubs, get_projects, get_items, get_versions

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI()

# Define the available tools for OpenAI function calling
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_hubs",
            "description": "Retrieves accessible hubs for the authenticated member",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_projects",
            "description": "Retrieves projects from a specified hub",
            "parameters": {
                "type": "object",
                "properties": {
                    "hub_id": {
                        "type": "string",
                        "description": "The ID of the hub to retrieve projects from"
                    }
                },
                "required": ["hub_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_items",
            "description": "Retrieves metadata for up to 50 items in a project",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "The ID of the project to retrieve items from"
                    }
                },
                "required": ["project_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_versions",
            "description": "Returns versions for a given item",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "The ID of the project containing the item"
                    },
                    "item_id": {
                        "type": "string",
                        "description": "The ID of the item to retrieve versions for"
                    }
                },
                "required": ["project_id", "item_id"]
            }
        }
    }
]

# Function to handle user queries
def process_query(user_input, chat_history=None):
    """
    Process user input, determine appropriate functions to call, and generate a response.
    
    Args:
        user_input (str): The user's query
        chat_history (list, optional): List of previous messages. Defaults to None.
    
    Returns:
        tuple: (response, updated_chat_history)
    """
    # Initialize chat history if None
    if chat_history is None:
        chat_history = [
            {"role": "system", "content": DATA_MANAGEMENT_PROMPT}
        ]
    
    # Add user message to history
    chat_history.append({"role": "user", "content": user_input})
    
    # Get model response with function calling enabled
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=chat_history,
        tools=tools,
        **MODEL_CONFIG
    )
    
    # Get the assistant's message
    assistant_message = response.choices[0].message
    
    # Add the assistant's message to chat history
    chat_history.append(assistant_message)
    
    # Check if the assistant wants to call a function
    if assistant_message.tool_calls:
        # Debug info - what function is being called
        tool_call = assistant_message.tool_calls[0]
        function_name = tool_call.function.name
        print(f"\n[DEBUG] Function being called: {function_name}")
        
        # Process each tool call
        for tool_call in assistant_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            print(f"[DEBUG] Function args: {json.dumps(function_args, indent=2)}")
            
            # Execute the function
            function_response = execute_function(function_name, function_args)
            
            # Format and display the function response for debug purposes
            print("\n[DEBUG] Function response summary:")
            print_formatted_response(function_name, function_response)
            
            # Add the function response to chat history
            chat_history.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": json.dumps(function_response)
            })
        
        # Get a new response from the assistant
        second_response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=chat_history,
            **MODEL_CONFIG
        )
        
        # Add the new response to chat history
        assistant_response = second_response.choices[0].message
        chat_history.append(assistant_response)
        
        return assistant_response.content, chat_history
    
    return assistant_message.content, chat_history

def print_formatted_response(function_name, response_data):
    """
    Format and print the API response data in a user-friendly way
    
    Args:
        function_name (str): The name of the function that was called
        response_data (dict): The response data returned by the function
    """
    # Check for errors
    if 'error' in response_data:
        print(f"  Error: {response_data['error']}")
        return
    
    # Format based on function type
    if function_name == "get_hubs":
        print(f"  Found {response_data.get('count', 0)} hubs:")
        for i, hub in enumerate(response_data.get('hubs', []), 1):
            print(f"  {i}. {hub.get('name')} (ID: {hub.get('id')})")
    
    elif function_name == "get_projects":
        print(f"  Found {response_data.get('count', 0)} projects in hub {response_data.get('hub_id')}:")
        for i, project in enumerate(response_data.get('projects', []), 1):
            print(f"  {i}. {project.get('name')} (ID: {project.get('id')})")
    
    elif function_name == "get_items":
        print(f"  Found {response_data.get('count', 0)} items in project {response_data.get('project_id')}:")
        for i, item in enumerate(response_data.get('items', []), 1):
            print(f"  {i}. {item.get('name')} (Type: {item.get('file_type')}, ID: {item.get('id')})")
            print(f"     Last Modified: {item.get('last_modified', 'Unknown')}")
    
    elif function_name == "get_versions":
        print(f"  Found {response_data.get('count', 0)} versions for item in project {response_data.get('project_id')}:")
        for i, version in enumerate(response_data.get('versions', []), 1):
            print(f"  {i}. Version {version.get('version_number')} - {version.get('name')}")
            print(f"     Created by: {version.get('created_by')} on {version.get('created_date', 'Unknown')}")
            print(f"     Type: {version.get('file_type')}, Size: {version.get('storage_size', 'Unknown')}")
            print(f"     ID: {version.get('id')}")
            print()

def execute_function(function_name, function_args):
    """
    Execute the appropriate function based on the function name and arguments.
    
    Args:
        function_name (str): The name of the function to execute
        function_args (dict): Arguments for the function
    
    Returns:
        dict: The function's result
    """
    try:
        if function_name == "get_hubs":
            return get_hubs()
        elif function_name == "get_projects":
            return get_projects(function_args["hub_id"])
        elif function_name == "get_items":
            return get_items(function_args["project_id"])
        elif function_name == "get_versions":
            return get_versions(function_args["project_id"], function_args["item_id"])
        else:
            return {"error": f"Unknown function: {function_name}"}
    except Exception as e:
        return {"error": f"Error executing {function_name}: {str(e)}"}

def main():
    """
    Main function to run a simple command-line interface for the Data Management assistant.
    """
    print("\n========================================================")
    print("   Welcome to the Autodesk Data Management Assistant!")
    print("========================================================")
    print("This assistant can help you navigate your Autodesk hubs,")
    print("projects, and files using natural language commands.")
    print("\nExample queries:")
    print("- Show me my hubs")
    print("- List projects in hub b.c1370b5-08ab-4bb9-a248-a0c366abcdef")
    print("- Get items in project b.abcdef1234567890")
    print("- What versions are available for item urn:adsk.wipprod:fs.file:vf.abcdef1234567890?version=1")
    print("\nType 'exit' to quit.")
    print("========================================================\n")
    
    chat_history = None
    
    while True:
        user_input = input("\nYou: ")
        
        if user_input.lower() == 'exit':
            print("\nGoodbye! Thank you for using the Autodesk Data Management Assistant.")
            break
        
        print("\nProcessing your request...\n")
        
        response, chat_history = process_query(user_input, chat_history)
        
        print("\nAssistant:")
        print(response)

if __name__ == "__main__":
    main()
