import json
import re
import sys
import os

# Add the DataManagement directory to the path
data_mgmt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "01_DataManagment")
sys.path.append(data_mgmt_path)

# Import the necessary modules
from dm_1_prompts import SMART_SCHEDULE_PROMPT
from dm_0_config import MODEL_NAME, MODEL_CONFIG
from dm_3_helpers import get_current_state
from openai_service import get_openai_client

# Initialize OpenAI client using the service wrapper
client = get_openai_client()

def get_objects_for_schedule(schedule_type, current_state):
    """
    Retrieve the relevant objects for the requested schedule type.
    
    Args:
        schedule_type (str): The type of schedule requested (e.g., 'wall', 'electrical device')
        current_state (dict): The current state from chat memory
        
    Returns:
        tuple: (objects, error_message) where objects is a list of objects or None,
               and error_message is a string or None
    """
    # Check if we have the necessary data in the current state
    if not current_state.get("last_api_result"):
        return None, "No data available. Please retrieve model data first."
    
    # Get the last API result
    result = current_state.get("last_api_result")
    
    # Check if we have properties data
    if "properties" not in result:
        return None, "No property data available. Please retrieve view properties first."
    
    properties_data = result.get("properties", {})
    collections = properties_data.get("collection", [])
    
    if not collections:
        return None, "No collections found in the property data."
    
    # Filter objects based on schedule type
    filtered_objects = []
    
    for collection in collections:
        objects = collection.get("objects", [])
        for obj in objects:
            # Get the object name or type
            obj_name = obj.get("name", "").lower()
            obj_type = obj.get("objectid", {}).get("type", "").lower()
            
            # Filter based on schedule type
            if schedule_type == 'wall' and ('wall' in obj_name or 'wall' in obj_type):
                filtered_objects.append(obj)
            elif schedule_type == 'electrical device' and any(term in obj_name or term in obj_type for term in ['electrical', 'device', 'fixture']):
                filtered_objects.append(obj)
            # Add more filters as needed
    
    if not filtered_objects:
        # If no specific objects found, try to find objects with properties matching the schedule type
        for collection in collections:
            objects = collection.get("objects", [])
            for obj in objects:
                properties = obj.get("properties", [])
                for prop in properties:
                    prop_name = prop.get("name", "").lower()
                    prop_value = str(prop.get("value", "")).lower()
                    
                    if schedule_type == 'wall' and ('wall' in prop_name or 'wall' in prop_value):
                        filtered_objects.append(obj)
                        break
                    elif schedule_type == 'electrical device' and any(term in prop_name or term in prop_value for term in ['electrical', 'device', 'fixture']):
                        filtered_objects.append(obj)
                        break
                    # Add more filters as needed
    
    if not filtered_objects:
        return None, f"No {schedule_type} objects found in the data."
    
    return filtered_objects, None

def create_smart_schedule(schedule_type, objects, user_query, specified_properties=None):
    """
    Create a smart schedule using the LLM to recommend formatting.
    
    Args:
        schedule_type (str): The type of schedule requested
        objects (list): List of objects to include in the schedule
        user_query (str): The original user query
        specified_properties (list, optional): List of specific properties to include
        
    Returns:
        tuple: (markdown_table, error_message) where markdown_table is a string or None,
               and error_message is a string or None
    """
    if not objects:
        return None, "No objects provided for schedule creation."
    
    # Limit to a sample of objects for the LLM call (to avoid token limits)
    sample_objects = objects[:5]
    
    # Prepare the message for the LLM
    user_content = f"""
I need to create a {schedule_type} schedule based on the following sample data:
{json.dumps(sample_objects, indent=2)}

The user requested: "{user_query}"
"""

    # If specific properties were requested, include them
    if specified_properties:
        user_content += f"\nThe user specifically requested these properties: {', '.join(specified_properties)}"
    
    user_content += "\nPlease analyze this data and recommend the best properties to include in the schedule.\nReturn your response in JSON format with \"columns\" and \"table\" keys."
    
    messages = [
        {"role": "system", "content": SMART_SCHEDULE_PROMPT},
        {"role": "user", "content": user_content}
    ]
    
    try:
        # Call the LLM for formatting recommendations
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            response_format={"type": "json_object"},
            **MODEL_CONFIG
        )
        
        # Extract the response content
        content = response.choices[0].message.content
        
        # Parse the JSON response
        try:
            schedule_data = json.loads(content)
            
            # Check if the response has the expected format
            if "table" in schedule_data:
                return schedule_data["table"], None
            elif "columns" in schedule_data:
                # If only columns are provided, build the table ourselves
                columns_to_use = specified_properties if specified_properties else schedule_data["columns"]
                return build_markdown_table(objects, columns_to_use), None
            else:
                return None, "Invalid response format from LLM."
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract a markdown table directly
            table_match = re.search(r'```markdown\s*((?:\|.*\|(?:\r?\n|$))+)```', content)
            if table_match:
                return table_match.group(1), None
            else:
                return None, "Failed to parse LLM response."
    except Exception as e:
        return None, f"Error calling LLM: {str(e)}"

def build_markdown_table(objects, columns):
    """
    Build a markdown table from objects using the specified columns.
    
    Args:
        objects (list): List of objects to include in the table
        columns (list): List of column names to include
        
    Returns:
        str: Markdown formatted table
    """
    if not objects or not columns:
        return "No data available for table."
    
    # Start building the table
    table = "| " + " | ".join(columns) + " |\n"
    table += "| " + " | ".join(["---"] * len(columns)) + " |\n"
    
    # Add rows
    for obj in objects:
        row = []
        for col in columns:
            # Try to find the property in the object
            value = "N/A"
            
            # Check in top-level properties
            if col in obj:
                value = str(obj[col])
            
            # Check in nested properties array
            elif "properties" in obj:
                for prop in obj.get("properties", []):
                    if prop.get("name") == col:
                        value = str(prop.get("value", "N/A"))
                        break
            
            row.append(value)
        
        table += "| " + " | ".join(row) + " |\n"
    
    return table

def create_schedule(schedule_type, properties=None):
    """
    Main function to create a schedule, to be called by the execute_function method.
    
    Args:
        schedule_type (str): The type of schedule to create (e.g., 'wall', 'electrical device')
        properties (list, optional): List of specific properties to include
        
    Returns:
        dict: A dictionary with the schedule data or an error message
    """
    # Get the current state
    current_state = get_current_state()
    
    # Get objects for the schedule
    objects, error = get_objects_for_schedule(schedule_type, current_state)
    
    if error:
        return {"error": error}
    
    # Create the schedule
    table, error = create_smart_schedule(schedule_type, objects, f"Create a {schedule_type} schedule", properties)
    
    if error:
        return {"error": error}
    
    # Return the schedule data
    return {
        "schedule_type": schedule_type,
        "object_count": len(objects),
        "table": table,
        "properties_used": properties if properties else "auto-detected"
    } 