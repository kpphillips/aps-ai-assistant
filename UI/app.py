import streamlit as st
import sys
import os
import json
from datetime import datetime

# Add the DataManagement directory to the path
data_mgmt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "01_DataManagment")
sys.path.append(data_mgmt_path)

# Import the Autodesk API helper and OpenAI configuration
from dm_3_helpers import AutodeskAPIHelper
from dm_0_config import MODEL_NAME, MODEL_CONFIG
from dm_1_prompts import DATA_MANAGEMENT_PROMPT

# Initialize OpenAI client
from openai import OpenAI
client = OpenAI()

# Initialize the Autodesk API Helper
api_helper = AutodeskAPIHelper()

# Set up page configuration
st.set_page_config(
    page_title="Autodesk Data Management API Demo",
    page_icon="🏗️",
    layout="wide"
)

class ChatAssistant:
    """Class for handling the chat assistant functionality"""
    
    def __init__(self):
        """Initialize the chat assistant"""
        self.api_helper = api_helper
        self.tools = [
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
    
    def process_message(self, user_input, chat_history=None):
        """Process a user message and return the response"""
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
            tools=self.tools,
            **MODEL_CONFIG
        )
        
        # Get the assistant's message
        assistant_message = response.choices[0].message
        
        # Add the assistant's message to chat history
        chat_history.append(assistant_message)
        
        # Check if the assistant wants to call a function
        if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
            # Process each tool call
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Execute the function
                function_result = self.execute_function(function_name, function_args)
                
                # Add the function result to chat history
                chat_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": json.dumps(function_result)
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
    
    def execute_function(self, function_name, function_args):
        """Execute a function and return the result"""
        try:
            if function_name == "get_hubs":
                return self.api_helper.get_hubs()
            elif function_name == "get_projects":
                hub_id = function_args["hub_id"]
                return self.api_helper.get_projects(hub_id)
            elif function_name == "get_items":
                project_id = function_args["project_id"]
                return self.api_helper.get_items(project_id)
            elif function_name == "get_versions":
                project_id = function_args["project_id"]
                item_id = function_args["item_id"]
                return self.api_helper.get_versions(project_id, item_id)
            else:
                return {"error": f"Unknown function: {function_name}"}
        except Exception as e:
            return {"error": f"Error executing {function_name}: {str(e)}"}

# Initialize the chat assistant
assistant = ChatAssistant()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "chat_history" not in st.session_state:
    st.session_state.chat_history = None

# Set up the Streamlit UI
st.title("Autodesk Data Management Assistant")
st.markdown("""
This assistant can help you navigate your Autodesk Platform Services (APS) data. 
Ask questions about your hubs, projects, items, and file versions.
""")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Get user input
prompt = st.chat_input("Ask me about your Autodesk data...")

# Process user input
if prompt:
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # Add a placeholder for the assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Thinking...")
        
        try:
            # Process the user message
            response, st.session_state.chat_history = assistant.process_message(
                prompt, st.session_state.chat_history
            )
            
            # Update the placeholder with the final response
            message_placeholder.markdown(response)
            
            # Add assistant message to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})
            
        except Exception as e:
            error_message = f"Error: {str(e)}"
            message_placeholder.markdown(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})

# Add sidebar with information
with st.sidebar:
    st.title("About")
    st.markdown("""
    This assistant demonstrates the use of AI function calling to interact with Autodesk Platform Services (APS) APIs.
    
    You can ask questions like:
    - Show me my hubs
    - List projects in hub abc123
    - Get items in project xyz789
    - Show versions of item def456 in project xyz789
    """) 