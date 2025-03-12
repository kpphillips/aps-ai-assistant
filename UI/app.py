import streamlit as st
import sys
import os
import json
import importlib.util
from datetime import datetime

# Add the parent directory to the path to import business logic
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add the DataManagement directory to the path
data_mgmt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "01_DataManagment")
sys.path.append(data_mgmt_path)

# Import directly from the helper files
from dm_3_helpers import get_hubs, get_projects, get_items, get_versions
from dm_0_config import MODEL_NAME, MODEL_CONFIG
from dm_1_prompts import DATA_MANAGEMENT_PROMPT

# Initialize OpenAI client
from openai import OpenAI
client = OpenAI()

# Mock API responses for testing
MOCK_RESPONSES = {
    "get_hubs": {
        "hubs": [
            {"id": "mock_hub_1", "name": "Mock Hub 1"},
            {"id": "mock_hub_2", "name": "Mock Hub 2"},
            {"id": "mock_hub_3", "name": "Demo Hub"}
        ],
        "count": 3
    },
    "get_projects": {
        "hub_id": "mock_hub_1",
        "projects": [
            {"id": "mock_project_1", "name": "Mock Project A"},
            {"id": "mock_project_2", "name": "Mock Project B"},
            {"id": "mock_project_3", "name": "Demo Project"}
        ],
        "count": 3
    },
    "get_items": {
        "project_id": "mock_project_1",
        "items": [
            {"id": "mock_item_1", "name": "Mock Drawing.dwg", "file_type": "dwg", "last_modified": "2023-03-15 10:30:00", "version_id": "v1"},
            {"id": "mock_item_2", "name": "Mock Model.rvt", "file_type": "rvt", "last_modified": "2023-03-14 09:15:00", "version_id": "v1"},
            {"id": "mock_item_3", "name": "Demo Document.pdf", "file_type": "pdf", "last_modified": "2023-03-13 14:45:00", "version_id": "v1"}
        ],
        "count": 3
    },
    "get_versions": {
        "project_id": "mock_project_1",
        "item_id": "mock_item_1",
        "versions": [
            {"id": "mock_version_1", "version_number": 2, "name": "Mock Drawing.dwg", "created_by": "Mock User", "created_date": "2023-03-15 10:30:00", "file_type": "dwg", "storage_size": "2.5 MB"},
            {"id": "mock_version_2", "version_number": 1, "name": "Mock Drawing.dwg", "created_by": "Mock User", "created_date": "2023-03-14 15:20:00", "file_type": "dwg", "storage_size": "2.3 MB"}
        ],
        "count": 2
    }
}

# Class for helper functions needed by the UI
class UIHelpers:
    @staticmethod
    def filter_projects(projects, criteria):
        """Filter projects based on criteria"""
        if not criteria:
            return projects
        return [p for p in projects if criteria.lower() in p.get('name', '').lower()]
    
    @staticmethod
    def filter_items(items, criteria):
        """Filter items based on criteria"""
        if not criteria:
            return items
        return [i for i in items if (
            criteria.lower() in i.get('name', '').lower() or 
            criteria.lower() in i.get('file_type', '').lower()
        )]

    @staticmethod
    def process_user_query(user_input, chat_history=None):
        """Process user query through OpenAI"""
        # Tools definition for function calling
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
        
        # Initialize function_calls as None
        function_calls = None
        
        # Check if the assistant wants to call a function
        if assistant_message.tool_calls:
            function_calls = []
            
            # Process each tool call
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Add to function calls list
                function_calls.append({
                    'id': tool_call.id,
                    'name': function_name,
                    'args': function_args
                })
        
        return assistant_message.content, chat_history, function_calls

    @staticmethod
    def process_function_result(chat_history, function_name, function_args, function_response):
        """Process function result and get AI response"""
        # Find the right tool call ID
        tool_call_id = None
        
        # Debug logging
        log_debug(f"\nLooking for tool call ID for function: {function_name}")
        log_debug(f"Function args: {json.dumps(function_args)}")
        
        # We need to be careful with the data structure of chat_history elements
        # The OpenAI API returns objects for assistant messages, but we need to handle both objects and dictionaries
        # First, find the most recent assistant message with tool calls
        assistant_message = None
        for message in reversed(chat_history):
            role = message.get('role') if isinstance(message, dict) else getattr(message, 'role', None)
            if role == 'assistant':
                # Check for tool_calls in this message
                if isinstance(message, dict) and 'tool_calls' in message:
                    assistant_message = message
                    log_debug(f"Found assistant message (dict) with tool_calls")
                    break
                elif hasattr(message, 'tool_calls') and message.tool_calls:
                    assistant_message = message
                    log_debug(f"Found assistant message (object) with tool_calls")
                    break
        
        # If we found an assistant message with tool calls, look for our specific function
        if assistant_message:
            tool_calls = assistant_message.get('tool_calls') if isinstance(assistant_message, dict) else assistant_message.tool_calls
            
            # Convert tool_calls to a standard format regardless of input type
            if isinstance(tool_calls, list):
                log_debug(f"Tool calls is already a list with {len(tool_calls)} items")
                # Direct list from dictionary
                for tc in tool_calls:
                    tc_name = tc.get('function', {}).get('name') if isinstance(tc, dict) else getattr(getattr(tc, 'function', None), 'name', None)
                    if tc_name == function_name:
                        log_debug(f"Found matching function name: {tc_name}")
                        tc_args = tc.get('function', {}).get('arguments') if isinstance(tc, dict) else getattr(getattr(tc, 'function', None), 'arguments', None)
                        
                        # Compare arguments
                        try:
                            tc_args_parsed = json.loads(tc_args) if tc_args else {}
                            if tc_args_parsed == function_args:
                                tool_call_id = tc.get('id') if isinstance(tc, dict) else getattr(tc, 'id', None)
                                log_debug(f"Found matching tool call ID: {tool_call_id}")
                                break
                        except Exception as e:
                            log_error(f"Error parsing arguments: {str(e)}")
            else:
                log_debug(f"Tool calls is not a list, it's a {type(tool_calls)}")
        
        # If we still don't have a tool_call_id, try a more lenient approach
        if not tool_call_id:
            log_debug("Could not find exact match for tool call ID, trying fallback approach")
            
            # Look for any tool call with the right function name
            for message in reversed(chat_history):
                if isinstance(message, dict) and message.get('role') == 'assistant' and 'tool_calls' in message:
                    for tc in message.get('tool_calls', []):
                        if isinstance(tc, dict) and tc.get('function', {}).get('name') == function_name:
                            tool_call_id = tc.get('id')
                            log_debug(f"Fallback: Found tool call ID {tool_call_id} from dict")
                            break
                elif hasattr(message, 'role') and message.role == 'assistant' and hasattr(message, 'tool_calls') and message.tool_calls:
                    for tc in message.tool_calls:
                        if hasattr(tc, 'function') and hasattr(tc.function, 'name') and tc.function.name == function_name:
                            tool_call_id = tc.id
                            log_debug(f"Fallback: Found tool call ID {tool_call_id} from object")
                            break
                
                if tool_call_id:
                    break
        
        # If we still don't have a tool_call_id, create one using a deterministic approach
        if not tool_call_id:
            log_debug("No matching tool call ID found, creating a deterministic ID")
            import hashlib
            # Create a deterministic ID based on function name and arguments
            hash_input = f"{function_name}:{json.dumps(function_args, sort_keys=True)}"
            tool_call_id = f"call_{hashlib.md5(hash_input.encode()).hexdigest()[:24]}"
            log_debug(f"Created deterministic tool call ID: {tool_call_id}")
        
        # Add the function response to chat history
        log_debug(f"Adding tool message with tool_call_id: {tool_call_id}")
        tool_message = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": function_name,
            "content": json.dumps(function_response)
        }
        chat_history.append(tool_message)
        
        # Get a new response from the assistant
        try:
            log_debug("Getting new response from assistant")
            
            # Debugging the message structure
            message_types = []
            for msg in chat_history:
                if isinstance(msg, dict):
                    message_types.append(f"Dict: {msg.get('role')}")
                else:
                    message_types.append(f"Object: {getattr(msg, 'role', 'unknown')}")
            log_debug(f"Chat history contains: {', '.join(message_types)}")
            
            # Ensure all messages are properly formatted dictionaries
            formatted_messages = []
            for msg in chat_history:
                if isinstance(msg, dict):
                    formatted_messages.append(msg)
                else:
                    # Convert from object to dict
                    msg_dict = {"role": msg.role}
                    
                    if hasattr(msg, 'content') and msg.content is not None:
                        msg_dict["content"] = msg.content
                        
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        msg_dict["tool_calls"] = [
                            {
                                "id": tc.id,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            } for tc in msg.tool_calls
                        ]
                        
                        # Add required 'type' field for each tool call
                        for tc in msg_dict["tool_calls"]:
                            tc["type"] = "function"
                        
                    if hasattr(msg, 'tool_call_id') and msg.tool_call_id:
                        msg_dict["tool_call_id"] = msg.tool_call_id
                        
                    if hasattr(msg, 'name') and msg.name:
                        msg_dict["name"] = msg.name
                        
                    formatted_messages.append(msg_dict)
            
            # Make the API call with formatted messages
            log_debug(f"Sending {len(formatted_messages)} messages to OpenAI")
            second_response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=formatted_messages,
                **MODEL_CONFIG
            )
            
            # Add the new response to chat history
            assistant_response = second_response.choices[0].message
            chat_history.append(assistant_response)
            
            log_debug("Received new response from assistant")
            return assistant_response.content, chat_history
        except Exception as e:
            error_msg = f"Error getting assistant response: {str(e)}"
            log_error(error_msg, e)
            import traceback
            log_error(traceback.format_exc())
            return f"I encountered an error processing the function response: {str(e)}", chat_history

    @staticmethod
    def analyze_response_for_options(response):
        """Analyze response to detect options for UI display"""
        # Check if response is None
        if response is None:
            return None
            
        # Check for common phrases that indicate options follow
        option_indicators = [
            "here is a list of",
            "here are the",
            "please select",
            "choose from",
            "select one of the following",
            "here's a list of"
        ]
        
        has_options = any(indicator.lower() in response.lower() for indicator in option_indicators)
        
        if not has_options:
            return None
            
        # Try to determine what type of options these are
        option_types = {
            "hub": ["hub", "hubs"],
            "project": ["project", "projects"],
            "item": ["item", "items", "file", "files"],
            "version": ["version", "versions"]
        }
        
        option_type = None
        for type_key, indicators in option_types.items():
            if any(indicator.lower() in response.lower() for indicator in indicators):
                option_type = type_key
                break
                
        return {
            "has_options": True,
            "option_type": option_type
        }

# Create instance of helper class
ui_helpers = UIHelpers()

# Use the helper functions
filter_projects = ui_helpers.filter_projects
filter_items = ui_helpers.filter_items
process_user_query = ui_helpers.process_user_query
process_function_result = ui_helpers.process_function_result
analyze_response_for_options = ui_helpers.analyze_response_for_options

# Page configuration
st.set_page_config(
    page_title="Autodesk Platform Services Assistant",
    page_icon="🏗️",
    layout="wide"
)

# App title
st.title("Autodesk Platform Services Assistant")
st.markdown("Ask questions about your Autodesk hubs, projects, and files in natural language.")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    
# Initialize session state for chat_history (OpenAI format)
if "chat_history" not in st.session_state:
    st.session_state.chat_history = None
    
# Initialize session state for current data
if "current_data" not in st.session_state:
    st.session_state.current_data = {
        "hubs": None,
        "projects": None,
        "items": None,
        "versions": None
    }

# Initialize session state for displaying options
if "show_options" not in st.session_state:
    st.session_state.show_options = False
    
if "option_type" not in st.session_state:
    st.session_state.option_type = None

# Initialize session state for debugging/logging
if "debug_logs" not in st.session_state:
    st.session_state.debug_logs = []

if "error_logs" not in st.session_state:
    st.session_state.error_logs = []

if "api_calls" not in st.session_state:
    st.session_state.api_calls = []

# Flag to use mock API responses when real API calls fail
if "use_mock_responses" not in st.session_state:
    st.session_state.use_mock_responses = False

# Add a function to log debug messages persistently
def log_debug(message):
    """Add a debug log message that persists between reruns"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append(f"[{timestamp}] {message}")
    print(message)  # Also print to console for server logs

# Add a function to log errors persistently
def log_error(message, exception=None):
    """Add an error log message that persists between reruns"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    error_msg = f"[{timestamp}] ERROR: {message}"
    st.session_state.error_logs.append(error_msg)
    
    if exception:
        import traceback
        trace = traceback.format_exc()
        st.session_state.error_logs.append(trace)
    
    print(error_msg)  # Also print to console for server logs
    if exception:
        print(traceback.format_exc())

# Add a function to log API calls persistently
def log_api_call(function_name, args, result):
    """Log API call details that persist between reruns"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Create a summary of the result
    if "error" in result:
        status = "ERROR"
        summary = result["error"]
    else:
        status = "SUCCESS"
        count = result.get("count", 0)
        summary = f"Retrieved {count} results"
    
    call_info = {
        "timestamp": timestamp,
        "function": function_name,
        "args": args,
        "status": status,
        "summary": summary,
        "details": result
    }
    
    st.session_state.api_calls.append(call_info)
    
    # Also print to console
    print(f"[{timestamp}] API CALL: {function_name} - {status}: {summary}")

# Helper functions for UI
def handle_hub_selection(hub_id, hub_name):
    """Handle hub selection from UI"""
    user_message = f"I select Hub: {hub_name} (ID: {hub_id})"
    st.session_state.messages.append({"role": "user", "content": user_message})
    
    with st.spinner("Processing..."):
        # Call the backend
        projects_result = get_projects(hub_id)
        
        if "error" in projects_result:
            assistant_message = f"I encountered an error: {projects_result['error']}"
        else:
            # Store projects in session state
            st.session_state.current_data["projects"] = projects_result
            
            # Process the result through the assistant
            assistant_response, st.session_state.chat_history = process_function_result(
                st.session_state.chat_history,
                "get_projects",
                {"hub_id": hub_id},
                projects_result
            )
            
            # Add the assistant's response to the messages
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
            
            # Analyze if the response contains options to show
            options_info = analyze_response_for_options(assistant_response)
            if options_info and options_info["has_options"]:
                st.session_state.show_options = True
                st.session_state.option_type = options_info["option_type"]
            else:
                st.session_state.show_options = False

def handle_project_selection(project_id, project_name):
    """Handle project selection from UI"""
    user_message = f"I select Project: {project_name} (ID: {project_id})"
    st.session_state.messages.append({"role": "user", "content": user_message})
    
    with st.spinner("Processing..."):
        # Call the backend
        items_result = get_items(project_id)
        
        if "error" in items_result:
            assistant_message = f"I encountered an error: {items_result['error']}"
            st.session_state.messages.append({"role": "assistant", "content": assistant_message})
        else:
            # Store items in session state
            st.session_state.current_data["items"] = items_result
            
            # Process the result through the assistant
            assistant_response, st.session_state.chat_history = process_function_result(
                st.session_state.chat_history,
                "get_items",
                {"project_id": project_id},
                items_result
            )
            
            # Add the assistant's response to the messages
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
            
            # Analyze if the response contains options to show
            options_info = analyze_response_for_options(assistant_response)
            if options_info and options_info["has_options"]:
                st.session_state.show_options = True
                st.session_state.option_type = options_info["option_type"]
            else:
                st.session_state.show_options = False

def handle_item_selection(item_id, project_id, item_name):
    """Handle item selection from UI"""
    user_message = f"I select Item: {item_name} (ID: {item_id})"
    st.session_state.messages.append({"role": "user", "content": user_message})
    
    with st.spinner("Processing..."):
        # Call the backend
        versions_result = get_versions(project_id, item_id)
        
        if "error" in versions_result:
            assistant_message = f"I encountered an error: {versions_result['error']}"
            st.session_state.messages.append({"role": "assistant", "content": assistant_message})
        else:
            # Store versions in session state
            st.session_state.current_data["versions"] = versions_result
            
            # Process the result through the assistant
            assistant_response, st.session_state.chat_history = process_function_result(
                st.session_state.chat_history,
                "get_versions",
                {"project_id": project_id, "item_id": item_id},
                versions_result
            )
            
            # Add the assistant's response to the messages
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
            
            # Analyze if the response contains options to show
            options_info = analyze_response_for_options(assistant_response)
            if options_info and options_info["has_options"]:
                st.session_state.show_options = True
                st.session_state.option_type = options_info["option_type"]
            else:
                st.session_state.show_options = False

def display_options():
    """Display the appropriate options based on the current state"""
    if not st.session_state.show_options:
        return
        
    if st.session_state.option_type == "hub":
        display_hub_options()
    elif st.session_state.option_type == "project":
        display_project_options()
    elif st.session_state.option_type == "item":
        display_item_options()
    elif st.session_state.option_type == "version":
        display_version_options()

def display_hub_options():
    """Display hub options as buttons or a dropdown"""
    if not st.session_state.current_data["hubs"]:
        return
        
    hubs = st.session_state.current_data["hubs"].get("hubs", [])
    
    if len(hubs) == 0:
        st.info("No hubs available.")
        return
        
    # If we have 5 or fewer hubs, show buttons
    if len(hubs) <= 5:
        st.write("#### Select a Hub:")
        cols = st.columns(len(hubs))
        
        for i, hub in enumerate(hubs):
            with cols[i]:
                if st.button(hub["name"], key=f"hub_{hub['id']}"):
                    handle_hub_selection(hub["id"], hub["name"])
    else:
        # Otherwise, show a dropdown
        st.write("#### Select a Hub:")
        selected_hub = st.selectbox(
            "Filter and select a hub:",
            options=range(len(hubs)),
            format_func=lambda i: hubs[i]["name"]
        )
        
        if st.button("Confirm Hub Selection"):
            hub = hubs[selected_hub]
            handle_hub_selection(hub["id"], hub["name"])

def display_project_options():
    """Display project options as buttons or a dropdown with filter"""
    if not st.session_state.current_data["projects"]:
        return
        
    projects = st.session_state.current_data["projects"].get("projects", [])
    
    if len(projects) == 0:
        st.info("No projects available.")
        return
        
    # Always use dropdown for projects as they can be numerous
    st.write("#### Select a Project:")
    
    # Add a filter input
    filter_text = st.text_input("Filter projects by name:", key="project_filter")
    
    # Filter projects if filter text is provided
    filtered_projects = filter_projects(projects, filter_text)
    
    if len(filtered_projects) == 0:
        st.info("No projects match your filter.")
        return
        
    selected_project = st.selectbox(
        "Select a project:",
        options=range(len(filtered_projects)),
        format_func=lambda i: filtered_projects[i]["name"]
    )
    
    if st.button("Confirm Project Selection"):
        project = filtered_projects[selected_project]
        handle_project_selection(project["id"], project["name"])

def display_item_options():
    """Display item options as a dropdown with filter"""
    if not st.session_state.current_data["items"]:
        return
        
    items = st.session_state.current_data["items"].get("items", [])
    project_id = st.session_state.current_data["items"].get("project_id")
    
    if len(items) == 0:
        st.info("No items available.")
        return
        
    st.write("#### Select an Item:")
    
    # Add a filter input
    filter_text = st.text_input("Filter items by name or type:", key="item_filter")
    
    # Filter items if filter text is provided
    filtered_items = filter_items(items, filter_text)
    
    if len(filtered_items) == 0:
        st.info("No items match your filter.")
        return
        
    selected_item = st.selectbox(
        "Select an item:",
        options=range(len(filtered_items)),
        format_func=lambda i: f"{filtered_items[i]['name']} ({filtered_items[i]['file_type']})"
    )
    
    if st.button("Confirm Item Selection"):
        item = filtered_items[selected_item]
        handle_item_selection(item["id"], project_id, item["name"])

def display_version_options():
    """Display version information"""
    if not st.session_state.current_data["versions"]:
        return
        
    versions = st.session_state.current_data["versions"].get("versions", [])
    
    if len(versions) == 0:
        st.info("No versions available.")
        return
        
    st.write("#### Versions Information:")
    
    # Display versions in an expander
    with st.expander("View All Versions", expanded=True):
        for version in versions:
            st.markdown(f"""
            **Version {version['version_number']}**: {version['name']}  
            **Created By**: {version['created_by']} on {version['created_date']}  
            **File Type**: {version['file_type']}  
            **Size**: {version['storage_size']}  
            **ID**: {version['id']}
            """)
            st.divider()

# Initialize the chat interface
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Display dynamic options if needed
if st.session_state.show_options:
    with st.container():
        st.divider()
        display_options()
        st.divider()

# Handle user input
if prompt := st.chat_input("Ask a question about your Autodesk resources..."):
    # Add user message to the chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get the assistant's response
    with st.spinner("Thinking..."):
        try:
            log_debug(f"Processing user query: '{prompt}'")
            assistant_response, st.session_state.chat_history, function_calls = process_user_query(
                prompt, 
                st.session_state.chat_history
            )
            
            # Display assistant message
            with st.chat_message("assistant"):
                st.markdown(assistant_response)
            
            # Add assistant message to the chat
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
            
            # Analyze if the response contains options to show
            options_info = analyze_response_for_options(assistant_response)
            
            # If function calls were requested, execute them
            if function_calls:
                log_debug(f"Assistant requested {len(function_calls)} function call(s)")
                st.info(f"The assistant wants to execute {len(function_calls)} function call(s) to get more information.")
                
                for call in function_calls:
                    function_name = call["name"]
                    function_args = call["args"]
                    
                    # Log and display thinking info in expandable section that STAYS VISIBLE
                    with st.expander(f"Assistant's function call details for {function_name}", expanded=False):
                        st.code(json.dumps(call, indent=2), language="json")
                        log_debug(f"Function call details: {function_name} with args: {json.dumps(function_args)}")
                    
                    # Create a progress bar for the API call
                    progress_bar = st.progress(0)
                    
                    with st.spinner(f"Executing {function_name} API call..."):
                        try:
                            progress_bar.progress(25)
                            
                            # First try to execute the real API call
                            real_result = None
                            try:
                                if function_name == "get_hubs":
                                    log_debug(f"Executing get_hubs API call")
                                    st.info("Querying Autodesk Platform Services for available hubs...")
                                    real_result = get_hubs()
                                elif function_name == "get_projects" and "hub_id" in function_args:
                                    hub_id = function_args["hub_id"]
                                    log_debug(f"Executing get_projects API call for hub {hub_id}")
                                    st.info(f"Querying Autodesk Platform Services for projects in hub {hub_id}...")
                                    real_result = get_projects(hub_id)
                                elif function_name == "get_items" and "project_id" in function_args:
                                    project_id = function_args["project_id"]
                                    log_debug(f"Executing get_items API call for project {project_id}")
                                    st.info(f"Querying Autodesk Platform Services for items in project {project_id}...")
                                    real_result = get_items(project_id)
                                elif function_name == "get_versions" and "project_id" in function_args and "item_id" in function_args:
                                    project_id = function_args["project_id"]
                                    item_id = function_args["item_id"]
                                    log_debug(f"Executing get_versions API call for item {item_id} in project {project_id}")
                                    st.info(f"Querying Autodesk Platform Services for versions of item {item_id}...")
                                    real_result = get_versions(project_id, item_id)
                                else:
                                    error_msg = f"Unknown function: {function_name} or missing required arguments"
                                    log_error(error_msg)
                                    st.error(error_msg)
                                    continue
                            except Exception as e:
                                log_error(f"Error executing real API call: {str(e)}", e)
                                # Let it fall through to the mock check
                            
                            # Check for error in real result or if using mock mode
                            if st.session_state.use_mock_responses or (real_result and "error" in real_result):
                                # If real API failed or we're in mock mode, use mock data
                                if real_result and "error" in real_result:
                                    error_message = real_result["error"]
                                    log_debug(f"Real API call failed with error: {error_message}, using mock data")
                                    
                                    # Display a warning about using mock data
                                    st.warning(f"API call failed: {error_message}. Using mock data instead.")
                                
                                # Use the mock response if available
                                if function_name in MOCK_RESPONSES:
                                    result = MOCK_RESPONSES[function_name].copy()
                                    
                                    # Update any IDs from the arguments if necessary
                                    if function_name == "get_projects" and "hub_id" in function_args:
                                        result["hub_id"] = function_args["hub_id"]
                                    elif function_name == "get_items" and "project_id" in function_args:
                                        result["project_id"] = function_args["project_id"]
                                    elif function_name == "get_versions" and "project_id" in function_args and "item_id" in function_args:
                                        result["project_id"] = function_args["project_id"]
                                        result["item_id"] = function_args["item_id"]
                                    
                                    log_debug(f"Using mock data for {function_name}")
                                    st.info("Using mock data for demonstration purposes.")
                                else:
                                    # No mock available
                                    result = {"error": f"No mock data available for {function_name}", "mock": True}
                                    log_error(f"No mock data available for {function_name}")
                            else:
                                # Use the real result
                                result = real_result
                            
                            # Store the result in session state
                            if function_name == "get_hubs":
                                st.session_state.current_data["hubs"] = result
                            elif function_name == "get_projects":
                                st.session_state.current_data["projects"] = result
                            elif function_name == "get_items":
                                st.session_state.current_data["items"] = result
                            elif function_name == "get_versions":
                                st.session_state.current_data["versions"] = result
                            
                            # Log the API call
                            log_api_call(function_name, function_args, result)
                            
                            progress_bar.progress(75)
                            
                            # Check if there was an error in the result
                            if "error" in result and not result.get("mock", False):
                                error_message = result["error"]
                                
                                # Check for authentication errors
                                if "401" in error_message or "unauthorized" in error_message.lower() or "invalid" in error_message.lower() and "token" in error_message.lower():
                                    auth_error_msg = "Authentication Error: Your Autodesk Platform Services token is invalid or expired."
                                    log_error(auth_error_msg)
                                    log_error(f"API Error Details: {error_message}")
                                    
                                    # Create a persistent error message display
                                    st.error(auth_error_msg)
                                    st.error("Please update your APS_AUTH_TOKEN environment variable with a valid token.")
                                    
                                    # Suggest enabling mock mode
                                    st.warning("You can enable mock data in the sidebar to continue working without a valid token.")
                                else:
                                    log_error(f"API Error: {error_message}")
                                    st.error(f"API Error: {error_message}")
                                
                                st.warning("The assistant will try to handle this error gracefully.")
                                
                                # For clarity in UI, create an error response object to pass to the assistant
                                if not st.session_state.use_mock_responses:  # Only do this if we're not already using mock data
                                    result = {
                                        "error": error_message,
                                        "function": function_name,
                                        "status": "failed",
                                        "params": function_args
                                    }
                            else:
                                # Show result summary
                                result_type = ""
                                count = result.get("count", 0)
                                
                                if function_name == "get_hubs":
                                    result_type = "hubs"
                                elif function_name == "get_projects":
                                    result_type = "projects"
                                elif function_name == "get_items":
                                    result_type = "items"
                                elif function_name == "get_versions":
                                    result_type = "versions"
                                
                                success_msg = f"Successfully retrieved {count} {result_type}!"
                                if st.session_state.use_mock_responses or result.get("mock", False):
                                    success_msg += " (mock data)"
                                log_debug(success_msg)
                                st.success(success_msg)
                            
                                # Process the function result
                                log_debug(f"Processing API response for {function_name} with assistant")
                                st.info("Processing API response with the assistant...")
                                
                                try:
                                    new_response, st.session_state.chat_history = process_function_result(
                                        st.session_state.chat_history,
                                        function_name,
                                        function_args,
                                        result
                                    )
                                    
                                    progress_bar.progress(100)
                                    
                                    # Update the assistant's response
                                    with st.chat_message("assistant"):
                                        st.markdown(new_response)
                                    
                                    # Replace the last assistant message
                                    st.session_state.messages[-1] = {"role": "assistant", "content": new_response}
                                    
                                    # Check if we should show options
                                    options_info = analyze_response_for_options(new_response)
                                    log_debug(f"Updated assistant response with {function_name} results")
                                except Exception as e:
                                    error_msg = f"Error processing function result: {str(e)}"
                                    log_error(error_msg, e)
                                    st.error(error_msg)
                                    # Create persistent debug info with traceback
                                    with st.expander("Error details", expanded=True):
                                        import traceback
                                        st.code(traceback.format_exc(), language="python")
                        except Exception as e:
                            error_msg = f"Error executing {function_name}: {str(e)}"
                            log_error(error_msg, e)
                            st.error(error_msg)
                            # Create persistent debug info with traceback
                            with st.expander("Error details", expanded=True):
                                import traceback
                                st.code(traceback.format_exc(), language="python")
            
            # Update option display state based on the response
            if options_info and options_info["has_options"]:
                st.session_state.show_options = True
                st.session_state.option_type = options_info["option_type"]
                log_debug(f"Options detected in response: {options_info['option_type']}")
            else:
                st.session_state.show_options = False
                
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            log_error(error_msg, e)
            st.error(error_msg)
            # Ensure chat history doesn't get corrupted
            if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user":
                st.session_state.messages.append({"role": "assistant", 
                                                 "content": f"I'm sorry, I encountered an error: {str(e)}. Please try again."})
                
    # Force a rerun to show the options
    st.rerun()

# Sidebar for info
with st.sidebar:
    st.subheader("About")
    st.markdown("""
    This chat assistant helps you navigate your Autodesk Platform Services resources.
    
    You can:
    * Ask for your available hubs
    * Get projects for a specific hub
    * View items in a project
    * Get version information for items
    
    Try asking questions like:
    * "Show me my hubs"
    * "List projects for hub XYZ"
    * "What items are in project ABC?"
    """)
    
    st.divider()
    
    # Mock data toggle
    st.subheader("Settings")
    mock_data = st.toggle("Use Mock Data", st.session_state.use_mock_responses, 
                       help="When enabled, mock data will be used instead of real API calls. Useful for testing or when you don't have a valid API token.")
    if mock_data != st.session_state.use_mock_responses:
        st.session_state.use_mock_responses = mock_data
        if mock_data:
            st.success("Mock data mode enabled. All API calls will return test data.")
        else:
            st.warning("Mock data mode disabled. Real API calls will be used.")
    
    st.divider()
    
    # Debug section in sidebar (collapsible)
    with st.expander("Debug Information", expanded=False):
        # Create tabs for different types of logs
        debug_tab, error_tab, api_tab = st.tabs(["Debug Logs", "Errors", "API Calls"])
        
        with debug_tab:
            st.subheader("Debug Logs")
            if st.session_state.debug_logs:
                for log in st.session_state.debug_logs[-30:]:  # Show last 30 logs
                    st.text(log)
                if st.button("Clear Debug Logs"):
                    st.session_state.debug_logs = []
                    st.rerun()
            else:
                st.info("No debug logs yet.")
                
        with error_tab:
            st.subheader("Error Logs")
            if st.session_state.error_logs:
                for error in st.session_state.error_logs:
                    st.text(error)
                if st.button("Clear Error Logs"):
                    st.session_state.error_logs = []
                    st.rerun()
            else:
                st.info("No errors logged (that's good!).")
                
        with api_tab:
            st.subheader("API Calls")
            if st.session_state.api_calls:
                for i, call in enumerate(reversed(st.session_state.api_calls)):  # Most recent first
                    # Use a collapsible container with a header instead of an expander
                    st.markdown(f"### {call['timestamp']} - {call['function']} ({call['status']})")
                    st.write(f"**Summary:** {call['summary']}")
                    
                    # Use columns to organize the content
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Arguments:**")
                        st.json(call['args'])
                    with col2:
                        st.write("**Result:**")
                        # Show a simplified view of results to avoid excessive content
                        if "count" in call['details']:
                            st.write(f"Count: {call['details']['count']}")
                            st.write("(Expand below for full details)")
                    
                    # Allow viewing full details with a button
                    if st.button(f"Toggle Full Result Details #{i}", key=f"toggle_details_{i}"):
                        st.json(call['details'])
                    
                    # Add a divider between calls
                    st.divider()
                
                if st.button("Clear API Calls"):
                    st.session_state.api_calls = []
                    st.rerun()
            else:
                st.info("No API calls made yet.")
    
    st.divider()
    
    # Clear conversation button
    if st.button("Clear Conversation"):
        # Clear session state
        for key in list(st.session_state.keys()):
            if key not in ["user_info", "sidebar_state", "debug_logs", "error_logs", "api_calls"]:  # Preserve logs
                del st.session_state[key]
                
        # Re-initialize the state variables
        st.session_state.messages = []
        st.session_state.chat_history = None
        st.session_state.current_data = {
            "hubs": None,
            "projects": None,
            "items": None,
            "versions": None
        }
        st.session_state.show_options = False
        st.session_state.option_type = None
        
        # Display confirmation
        st.success("Conversation cleared successfully! All history and data have been reset.")
        log_debug("Conversation cleared by user")
        
        # Force a rerun to update the UI
        st.rerun() 