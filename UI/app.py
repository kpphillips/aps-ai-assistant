import streamlit as st
import sys
import os
import json
import importlib.util

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
        for message in chat_history:
            if message.get('role') == 'assistant' and hasattr(message, 'tool_calls'):
                for tool_call in message.tool_calls:
                    if tool_call.function.name == function_name:
                        # Match args to be sure
                        if json.loads(tool_call.function.arguments) == function_args:
                            tool_call_id = tool_call.id
                            break
        
        if not tool_call_id:
            print("Warning: Could not find matching tool call ID")
            tool_call_id = "unknown"
        
        # Add the function response to chat history
        chat_history.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
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
                for call in function_calls:
                    function_name = call["name"]
                    function_args = call["args"]
                    
                    with st.spinner(f"Executing {function_name}..."):
                        try:
                            # Execute the appropriate function based on name
                            if function_name == "get_hubs":
                                result = get_hubs()
                                st.session_state.current_data["hubs"] = result
                            elif function_name == "get_projects" and "hub_id" in function_args:
                                result = get_projects(function_args["hub_id"])
                                st.session_state.current_data["projects"] = result
                            elif function_name == "get_items" and "project_id" in function_args:
                                result = get_items(function_args["project_id"])
                                st.session_state.current_data["items"] = result
                            elif function_name == "get_versions" and "project_id" in function_args and "item_id" in function_args:
                                result = get_versions(function_args["project_id"], function_args["item_id"])
                                st.session_state.current_data["versions"] = result
                            else:
                                st.error(f"Unknown function: {function_name} or missing required arguments")
                                continue
                            
                            # Check if there was an error in the result
                            if "error" in result:
                                st.error(f"API Error: {result['error']}")
                            
                            # Process the function result
                            new_response, st.session_state.chat_history = process_function_result(
                                st.session_state.chat_history,
                                function_name,
                                function_args,
                                result
                            )
                            
                            # Update the assistant's response
                            with st.chat_message("assistant"):
                                st.markdown(new_response)
                            
                            # Replace the last assistant message
                            st.session_state.messages[-1] = {"role": "assistant", "content": new_response}
                            
                            # Check if we should show options
                            options_info = analyze_response_for_options(new_response)
                        except Exception as e:
                            st.error(f"Error executing {function_name}: {str(e)}")
            
            # Update option display state based on the response
            if options_info and options_info["has_options"]:
                st.session_state.show_options = True
                st.session_state.option_type = options_info["option_type"]
            else:
                st.session_state.show_options = False
                
        except Exception as e:
            st.error(f"Error processing query: {str(e)}")
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
    
    # Clear conversation button
    if st.button("Clear Conversation"):
        # Clear session state
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
        st.success("Conversation cleared!")
        
        # Force a rerun to update the UI
        st.rerun() 