import streamlit as st
import sys
import os
import json
from datetime import datetime
import pandas as pd
import altair as alt

# Add the DataManagement directory to the path
data_mgmt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "01_DataManagment")
sys.path.append(data_mgmt_path)

# Import the Autodesk API helper and OpenAI configuration
from dm_3_helpers import AutodeskAPIHelper, add_interaction, get_state_summary, filter_projects
from dm_0_config import MODEL_NAME, MODEL_CONFIG
from dm_1_prompts import DATA_MANAGEMENT_PROMPT

# Import the schedule creator
from schedule_creator import create_schedule

# Import the OpenAI service wrapper instead of directly initializing the client
from openai_service import get_openai_client

# Initialize OpenAI client using the service wrapper
client = get_openai_client()

# Initialize the Autodesk API Helper
api_helper = AutodeskAPIHelper()

def create_version_graph(versions_data):
    """
    Create a simple bar graph visualization of version sizes using Streamlit's native chart functionality.
    
    Args:
        versions_data (dict): The formatted version data from the API
        
    Returns:
        DataFrame: Data for graphing (returned but displayed directly in calling function)
    """
    if not versions_data or "error" in versions_data or not versions_data.get("versions"):
        return None
    
    # Extract version information
    versions = versions_data["versions"]
    
    # Create data for the graph
    data = {
        'Version': [],
        'Size (MB)': [],
        'Created Date': []
    }
    
    # Process the versions
    for version in versions:
        version_number = version.get("version_number", 0)
        data['Version'].append(f"V{version_number}")
        
        # Extract numeric size from formatted string (e.g. "37.84 MB" -> 37.84)
        size_str = version.get("storage_size", "0 B")
        try:
            size_val = float(size_str.split()[0])
            size_unit = size_str.split()[1]
            # Convert all to MB for consistency if needed
            if size_unit == "GB":
                size_val *= 1024
            elif size_unit == "KB":
                size_val /= 1024
            elif size_unit == "B":
                size_val /= (1024*1024)
        except (ValueError, IndexError):
            size_val = 0
            
        data['Size (MB)'].append(size_val)
        
        # Get the date
        date_str = version.get("created_date", "Unknown")
        if date_str and date_str != "Unknown":
            try:
                # Just get the date part without time
                date_only = date_str.split()[0]
                data['Created Date'].append(date_only)
            except:
                data['Created Date'].append("Unknown")
        else:
            data['Created Date'].append("Unknown")
    
    # Create a DataFrame from the data dictionary
    df = pd.DataFrame(data)
    
    # Return the DataFrame for display in the calling function
    return df

def create_object_hierarchy_graph(objects_data):
    """
    Create a visualization of object hierarchy from a model view.
    
    Args:
        objects_data (dict): The formatted object data from the API
        
    Returns:
        DataFrame: Data for graphing (returned but displayed directly in calling function)
    """
    if not objects_data or "error" in objects_data:
        return None
    
    # Extract the object hierarchy - check both the new format and old format
    # The structure could be either directly in objects_data["objects"] 
    # or in objects_data["objects"]["data"]["objects"]
    object_hierarchy = None
    
    if "objects" in objects_data:
        if isinstance(objects_data["objects"], dict) and "data" in objects_data["objects"]:
            # New format: {"objects": {"data": {"type": "objects", "objects": [...]}}}
            object_hierarchy = objects_data["objects"]["data"]
        else:
            # Old format: {"objects": {...}}
            object_hierarchy = objects_data["objects"]
    
    if not object_hierarchy or "objects" not in object_hierarchy:
        return None
    
    # This will store our processed data
    categories = []
    parents = []
    types = []
    counts = []
    
    # Process the hierarchy recursively
    def process_hierarchy(node, category=None, parent=None, depth=0):
        if not node:
            return
            
        # Process a dictionary
        if isinstance(node, dict):
            # Get the name of current node, strip any IDs that might be in the name
            current_name = node.get('name', 'Unknown')
            
            # Remove IDs from names like "Basic Wall [1200268]"
            if '[' in current_name and ']' in current_name:
                clean_name = current_name.split('[')[0].strip()
                current_name = clean_name
            
            # If this is a top-level category (depth=0)
            if depth == 0:
                category = current_name
                # Process children
                for child in node.get('objects', []):
                    process_hierarchy(child, category, None, depth+1)
            
            # Second level - typically a parent type like "Basic Wall" or "Pipe Types"
            elif depth == 1:
                parent = current_name
                # Process children
                for child in node.get('objects', []):
                    process_hierarchy(child, category, parent, depth+1)
            
            # Third level - typically a specific type
            elif depth == 2:
                type_name = current_name
                
                # Get all leaf objects (actual final nodes)
                leaf_objects = []
                
                # Function to recursively collect all leaf objects
                def collect_leaf_objects(obj_list):
                    leaf_count = 0
                    for item in obj_list:
                        if isinstance(item, dict):
                            # If this is a node with name that looks like "Basic Wall [1200268]"
                            # it's a leaf node regardless of whether it has objects
                            # Note: We look for IDs in brackets to identify but don't expose them
                            if 'name' in item and '[' in item.get('name', ''):
                                leaf_count += 1
                            # Otherwise, if it has objects, process them recursively
                            elif 'objects' in item and item['objects']:
                                leaf_count += collect_leaf_objects(item['objects'])
                            # If it has a name but no objects, it might still be a leaf node
                            elif 'name' in item and 'objects' not in item:
                                leaf_count += 1
                    return leaf_count
                
                leaf_count = collect_leaf_objects(node.get('objects', []))
                
                if leaf_count > 0:
                    categories.append(category)
                    parents.append(parent)
                    types.append(type_name)
                    counts.append(leaf_count)
        
        # If we have a list of objects
        elif isinstance(node, list):
            for item in node:
                process_hierarchy(item, category, parent, depth)
    
    # Start processing from the root of the hierarchy
    # The JSON structure is: {"data":{"type":"objects","objects":[{"objectid":1,"objects":[...]}]}}
    root_objects = object_hierarchy.get('objects', [])
    if len(root_objects) > 0:
        for root_obj in root_objects:
            process_hierarchy(root_obj, None, None, 0)
    
    # Create a DataFrame
    if categories:
        df = pd.DataFrame({
            'Category': categories,
            'Parent': parents,
            'Type': types,
            'Count': counts
        })
        
        # Sort by Category and Count (descending)
        df = df.sort_values(['Category', 'Count'], ascending=[True, False])
        
        return df
    
    return None

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
                    "name": "filter_projects",
                    "description": "Filters projects from a specified hub by name prefix",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hub_id": {
                                "type": "string",
                                "description": "The ID of the hub to filter projects from"
                            },
                            "prefix": {
                                "type": "string",
                                "description": "The prefix to filter project names by"
                            }
                        },
                        "required": ["hub_id", "prefix"]
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
            },
            {
                "type": "function",
                "function": {
                    "name": "get_model_views",
                    "description": "Retrieves the list of views (metadata) for a given model version",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "version_urn": {
                                "type": "string",
                                "description": "The URN of the version to retrieve views for"
                            }
                        },
                        "required": ["version_urn"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_view_properties",
                    "description": "Retrieves properties for a specific view of a model",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "version_urn": {
                                "type": "string",
                                "description": "The URN of the version containing the view"
                            },
                            "view_guid": {
                                "type": "string",
                                "description": "The GUID of the view to retrieve properties for"
                            }
                        },
                        "required": ["version_urn", "view_guid"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_view_objects",
                    "description": "Retrieves the object hierarchy for a specific view of a model",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "version_urn": {
                                "type": "string",
                                "description": "The URN of the version containing the view"
                            },
                            "view_guid": {
                                "type": "string",
                                "description": "The GUID of the view to retrieve objects for"
                            }
                        },
                        "required": ["version_urn", "view_guid"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_schedule",
                    "description": "Creates a formatted schedule/table of objects with their properties",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "schedule_type": {
                                "type": "string",
                                "description": "The type of objects to include in the schedule (e.g., 'wall', 'electrical device')"
                            },
                            "properties": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "Optional list of specific properties to include in the schedule. If not provided, common properties will be determined automatically."
                            }
                        },
                        "required": ["schedule_type"]
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
        
        # Check if the assistant wants to call a function
        if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
            # Create a proper assistant message with tool_calls for the chat history
            assistant_dict = {
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    } for tool_call in assistant_message.tool_calls
                ]
            }
            
            # Add the assistant's message to chat history
            chat_history.append(assistant_dict)
            
            # Process each tool call
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Extract a short intent from the assistant's message
                intent = self._extract_short_intent(assistant_message.content, function_name)
                
                # Store the interaction in memory before executing
                add_interaction(user_input, intent, function_name, function_args)
                
                # Execute the function
                function_result = self.execute_function(function_name, function_args)
                
                # Update the interaction with the result
                add_interaction(user_input, intent, function_name, function_args, function_result)
                
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
            
            # Get the assistant's message and convert to dictionary
            assistant_response = second_response.choices[0].message
            assistant_response_dict = {
                "role": "assistant",
                "content": assistant_response.content or ""
            }
            
            # Add the new response to chat history
            chat_history.append(assistant_response_dict)
            
            # Return both the intent and the final response
            return intent, assistant_response.content, chat_history
        else:
            # If no function call, just add the assistant's message as a dictionary
            assistant_dict = {
                "role": "assistant",
                "content": assistant_message.content or ""
            }
            
            # Add the assistant's message to chat history
            chat_history.append(assistant_dict)
            
            # Return the assistant's message
            return None, assistant_message.content, chat_history
    
    def _extract_short_intent(self, message, function_name):
        """Extract a short intent from the assistant's message"""
        # Default intent based on function name
        default_intents = {
            "get_hubs": "Fetching your hubs...",
            "get_projects": "Retrieving projects...",
            "filter_projects": "Filtering projects...",
            "get_items": "Getting items from project...",
            "get_versions": "Fetching version history...",
            "get_model_views": "Retrieving model views...",
            "get_view_properties": "Fetching view properties...",
            "get_view_objects": "Retrieving object hierarchy...",
            "create_schedule": "Creating schedule..."
        }
        
        # Try to extract a short intent from the message
        if message and "<request_breakdown>" in message and "</request_breakdown>" in message:
            # Extract the breakdown section
            breakdown_start = message.find("<request_breakdown>") + len("<request_breakdown>")
            breakdown_end = message.find("</request_breakdown>")
            breakdown = message[breakdown_start:breakdown_end].strip()
            
            # Get the first sentence or first 100 characters
            sentences = breakdown.split('.')
            if sentences:
                short_intent = sentences[0].strip()
                if len(short_intent) > 100:
                    short_intent = short_intent[:97] + "..."
                return short_intent
        
        # If we couldn't extract a good intent, use the default
        return default_intents.get(function_name, "Processing your request...")
    
    def execute_function(self, function_name, function_args):
        """Execute a function and return the result"""
        try:
            # Store the function name being executed
            st.session_state.last_function_called = function_name
            
            if function_name == "get_hubs":
                return self.api_helper.get_hubs()
            elif function_name == "get_projects":
                hub_id = function_args["hub_id"]
                return self.api_helper.get_projects(hub_id)
            elif function_name == "filter_projects":
                hub_id = function_args["hub_id"]
                prefix = function_args["prefix"]
                return self.api_helper.filter_projects(hub_id, prefix)
            elif function_name == "get_items":
                project_id = function_args["project_id"]
                return self.api_helper.get_items(project_id)
            elif function_name == "get_versions":
                project_id = function_args["project_id"]
                item_id = function_args["item_id"]
                result = self.api_helper.get_versions(project_id, item_id)
                
                # Store the version result for potential graphing
                if "error" not in result and result.get("versions"):
                    # Store in session state for later use
                    st.session_state.last_versions_data = result
                
                return result
            elif function_name == "get_model_views":
                version_urn = function_args["version_urn"]
                return self.api_helper.get_model_views(version_urn)
            elif function_name == "get_view_properties":
                version_urn = function_args["version_urn"]
                view_guid = function_args["view_guid"]
                return self.api_helper.get_view_properties(version_urn, view_guid)
            elif function_name == "get_view_objects":
                version_urn = function_args["version_urn"]
                view_guid = function_args["view_guid"]
                result = self.api_helper.get_view_objects(version_urn, view_guid)
                
                # Store the objects result for visualization
                if "error" not in result and result.get("objects"):
                    # Store in session state for later use
                    st.session_state.last_objects_data = result
                
                return result
            elif function_name == "create_schedule":
                schedule_type = function_args["schedule_type"]
                properties = function_args.get("properties")
                return create_schedule(schedule_type, properties)
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
    
if "last_versions_data" not in st.session_state:
    st.session_state.last_versions_data = None
    
if "last_function_called" not in st.session_state:
    st.session_state.last_function_called = None

# Set up the Streamlit UI
st.title("Autodesk Data Management Assistant")
st.markdown("""
This assistant can help you navigate your Autodesk Platform Services (APS) data. 
Ask questions about your hubs, projects, items, and file versions.
""")

# Display current state if available
state_summary = get_state_summary()
if state_summary != "No state information available":
    st.info(f"Current context: {state_summary}")

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
            intent, response, st.session_state.chat_history = assistant.process_message(
                prompt, st.session_state.chat_history
            )
            
            # If we have an intent (function was called), show it briefly
            if intent:
                message_placeholder.markdown(f"_{intent}_")
            else:
                # If no function was called, still record the interaction in memory
                add_interaction(prompt, "General question (no function call)", None, None, None)
            
            # Update the placeholder with the final response
            message_placeholder.markdown(response)
            
            # If versions data is available and get_versions was the last function called, display the graph
            if (st.session_state.get("last_versions_data") and 
                st.session_state.get("last_function_called") == "get_versions"):
                with st.expander("Version Size and Timeline Visualization", expanded=True):
                    df = create_version_graph(st.session_state.last_versions_data)
                    if df is not None:
                        # Display the size data as a bar chart
                        st.subheader("File Sizes by Version")
                        # Set the Version column as index for the chart
                        chart_df = df.set_index('Version')
                        st.bar_chart(chart_df['Size (MB)'])
                        
                        # Show the version timeline as a simple table
                        st.subheader("Version Timeline")
                        st.dataframe(df[['Version', 'Created Date']], hide_index=True)
                    else:
                        st.warning("No version data available to display in the graph.")
            
            # If objects data is available and get_view_objects was the last function called, display the visualization
            if (st.session_state.get("last_objects_data") and 
                st.session_state.get("last_function_called") == "get_view_objects"):
                with st.expander("Object Hierarchy Visualization", expanded=True):
                    df = create_object_hierarchy_graph(st.session_state.last_objects_data)
                    if df is not None:
                        # Display summary info
                        total_objects = st.session_state.last_objects_data.get("object_count", 0)
                        if total_objects == 0 and df is not None:
                            # Calculate total from the dataframe if object_count is missing
                            total_objects = df['Count'].sum()
                        
                        st.subheader(f"Object Counts by Type (Total: {total_objects})")
                        
                        # Create a more advanced chart with hover functionality
                        # First, determine if we need to facet by category based on number of types
                        unique_categories = df['Category'].nunique()
                        
                        if unique_categories > 1:
                            # Create a faceted chart grouped by Category
                            chart = alt.Chart(df).mark_bar().encode(
                                x=alt.X('Type:N', sort='-y', title="Object Type", axis=alt.Axis(labelLimit=150, labelAngle=45)),
                                y=alt.Y('Count:Q', title="Number of Objects"),
                                color=alt.Color('Parent:N', title="Parent Type"),
                                tooltip=['Category', 'Parent', 'Type', 'Count']
                            ).properties(
                                height=300,
                                title="Number of Objects by Type"
                            ).facet(
                                facet='Category:N',
                                columns=1
                            )
                        else:
                            # Simple chart for a single category
                            chart = alt.Chart(df).mark_bar().encode(
                                x=alt.X('Type:N', sort='-y', title="Object Type", axis=alt.Axis(labelLimit=150, labelAngle=45)),
                                y=alt.Y('Count:Q', title="Number of Objects"),
                                color=alt.Color('Parent:N', title="Parent Type"),
                                tooltip=['Category', 'Parent', 'Type', 'Count']
                            ).properties(
                                height=400,
                                title="Number of Objects by Type"
                            )
                        
                        # Display the chart
                        st.altair_chart(chart, use_container_width=True)
                        
                        # Show the detailed breakdown as a table
                        st.subheader("Detailed Object Breakdown")
                        st.dataframe(df, hide_index=True)
                    else:
                        st.warning("No object data available to display in the visualization.")
            
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
    - List projects in a specific hub
    - Get items in a project
    - Show versions of a specific file
    - Get model views for a file version
    - Show properties for a specific view in a version
    - Get object hierarchy for a specific view
    
    You can also create schedules:
    - Create a wall schedule
    - Show me a schedule of electrical devices
    - Make a table of walls with their properties
    """) 