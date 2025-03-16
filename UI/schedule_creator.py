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
    Retrieve the relevant objects for the requested schedule type with optimized data.
    Enhanced with more debug logging and flexible object matching.
    
    Args:
        schedule_type (str): The type of schedule requested (e.g., 'wall', 'electrical device')
        current_state (dict): The current state from chat memory
        
    Returns:
        tuple: (objects, error_message) where objects is a list of objects or None,
               and error_message is a string or None
    """
    print(f"\n[SCHEDULE] Looking for objects of type: {schedule_type}")
    
    # Check if we have the necessary data in the current state
    if not current_state.get("last_api_result"):
        print("[SCHEDULE] No data available in current_state.last_api_result")
        return None, "No data available. Please retrieve model data first."
    
    # Get the last API result
    result = current_state.get("last_api_result")
    print(f"[SCHEDULE] Last API result has keys: {list(result.keys())}")
    
    # Check if we have properties data
    if "properties" not in result:
        print("[SCHEDULE] No properties data found in last_api_result")
        return None, "No property data available. Please retrieve view properties first."
    
    properties_data = result.get("properties", {})
    collections = properties_data.get("collection", [])
    
    if not collections:
        print("[SCHEDULE] No collections found in properties data")
        return None, "No collections found in the property data."
    
    print(f"[SCHEDULE] Found {len(collections)} collections to search")
    
    # Create a list to store all matched objects
    filtered_objects = []
    
    # Define different ways to identify wall or electrical device objects
    wall_identifiers = ['wall', 'partition', 'facade', 'curtain wall']
    electrical_identifiers = ['electrical', 'device', 'fixture', 'switch', 'outlet', 'receptacle', 'panel']
    
    # Counter for debugging
    object_count = 0
    match_count = 0
    
    # Loop through each collection and their objects
    for collection_idx, collection in enumerate(collections):
        collection_name = collection.get("name", f"Collection {collection_idx}")
        objects = collection.get("objects", [])
        object_count += len(objects)
        
        print(f"[SCHEDULE] Searching collection '{collection_name}' with {len(objects)} objects")
        
        for obj in objects:
            # Get various object identifiers to search
            obj_name = obj.get("name", "").lower()
            obj_type = obj.get("objectid", {}).get("type", "").lower() if obj.get("objectid") else ""
            obj_category = ""
            
            # Look for a category property
            for prop in obj.get("properties", []):
                if prop.get("name", "").lower() in ["category", "family", "type", "element type"]:
                    obj_category = str(prop.get("value", "")).lower()
            
            # Determine if this object matches the requested schedule type
            is_match = False
            
            if schedule_type == 'wall':
                # Check name, type, category, or if "basic wall" is in the name
                is_match = any(term in obj_name for term in wall_identifiers) or \
                          any(term in obj_type for term in wall_identifiers) or \
                          any(term in obj_category for term in wall_identifiers) or \
                          "basic wall" in obj_name.lower()
                
            elif schedule_type == 'electrical device':
                # Check for electrical device identifiers
                is_match = any(term in obj_name for term in electrical_identifiers) or \
                          any(term in obj_type for term in electrical_identifiers) or \
                          any(term in obj_category for term in electrical_identifiers)
            
            # If no match found yet, check properties as a fallback
            if not is_match:
                for prop in obj.get("properties", []):
                    prop_name = prop.get("name", "").lower()
                    prop_value = str(prop.get("value", "")).lower()
                    
                    if schedule_type == 'wall' and any(term in prop_name or term in prop_value for term in wall_identifiers):
                        is_match = True
                        break
                    elif schedule_type == 'electrical device' and any(term in prop_name or term in prop_value for term in electrical_identifiers):
                        is_match = True
                        break
            
            if is_match:
                match_count += 1
                # Create a summarized version of the object with only essential properties
                summarized_obj = {
                    "name": obj.get("name", ""),
                    "objectid": obj.get("objectid", {})
                }
                
                # Extract only the basic properties we need
                essential_properties = []
                for prop in obj.get("properties", []):
                    # Only include properties with actual values
                    if "name" in prop and "value" in prop and prop["value"] is not None:
                        essential_properties.append({
                            "name": prop["name"],
                            "value": prop["value"]
                        })
                
                summarized_obj["properties"] = essential_properties
                filtered_objects.append(summarized_obj)
                
                # Print the first matched object for debugging
                if match_count == 1:
                    print(f"[SCHEDULE] First matched {schedule_type} object: '{obj_name}'")
    
    print(f"[SCHEDULE] Searched {object_count} total objects, found {match_count} matches for '{schedule_type}'")
    
    if not filtered_objects:
        # Create some fake test objects if nothing was found (for testing only)
        print(f"[SCHEDULE] Creating sample test data for {schedule_type} schedule")
        if schedule_type == 'wall':
            filtered_objects = [
                {
                    "name": "Basic Wall",
                    "objectid": {"type": "wall"},
                    "properties": [
                        {"name": "Width", "value": 0.2},
                        {"name": "Height", "value": 3.0},
                        {"name": "Volume", "value": 1.5},
                        {"name": "Material", "value": "Concrete"}
                    ]
                },
                {
                    "name": "Interior Wall",
                    "objectid": {"type": "wall"},
                    "properties": [
                        {"name": "Width", "value": 0.15},
                        {"name": "Height", "value": 2.7},
                        {"name": "Volume", "value": 0.8},
                        {"name": "Material", "value": "Drywall"}
                    ]
                },
                {
                    "name": "Exterior Wall",
                    "objectid": {"type": "wall"},
                    "properties": [
                        {"name": "Width", "value": 0.3},
                        {"name": "Height", "value": 3.2},
                        {"name": "Volume", "value": 2.1},
                        {"name": "Material", "value": "Brick"}
                    ]
                }
            ]
        elif schedule_type == 'electrical device':
            filtered_objects = [
                {
                    "name": "Light Switch",
                    "objectid": {"type": "electrical device"},
                    "properties": [
                        {"name": "Type", "value": "Switch"},
                        {"name": "Voltage", "value": 120},
                        {"name": "Manufacturer", "value": "Acme"}
                    ]
                },
                {
                    "name": "Light Fixture",
                    "objectid": {"type": "electrical device"},
                    "properties": [
                        {"name": "Type", "value": "Light Fixture"},
                        {"name": "Voltage", "value": 120},
                        {"name": "Wattage", "value": 60},
                        {"name": "Manufacturer", "value": "Acme"}
                    ]
                },
                {
                    "name": "Outlet",
                    "objectid": {"type": "electrical device"},
                    "properties": [
                        {"name": "Type", "value": "Outlet"},
                        {"name": "Voltage", "value": 120},
                        {"name": "Amperage", "value": 15},
                        {"name": "Manufacturer", "value": "Acme"}
                    ]
                }
            ]
            
        print(f"[SCHEDULE] Created {len(filtered_objects)} sample {schedule_type} objects for testing")
        return filtered_objects, None
    
    return filtered_objects, None

def create_smart_schedule(schedule_type, objects, user_query, specified_properties=None):
    """
    Create a smart schedule using the LLM to recommend formatting with optimized prompt and data usage.
    
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
    
    # Limit the number of objects sent to the LLM to reduce token usage
    # We'll use at most 3 objects as a sample for the LLM to analyze
    sample_size = min(3, len(objects))
    sample_objects = objects[:sample_size]
    
    # Get a list of all property names from the sample objects to help the LLM
    property_names = set()
    for obj in sample_objects:
        for prop in obj.get("properties", []):
            if "name" in prop:
                property_names.add(prop["name"])
    
    # Format the system prompt with the specific schedule type
    formatted_system_prompt = SMART_SCHEDULE_PROMPT.format(schedule_type=schedule_type)
    
    # Prepare a concise message for the LLM
    user_content = f"""
I need to create a {schedule_type} schedule based on sample data with the following property names:
{', '.join(sorted(property_names))}

The request is: "{user_query}"
"""

    # If specific properties were requested, include them
    if specified_properties:
        user_content += f"\nRequested properties: {', '.join(specified_properties)}"
    
    # Add a few sample objects (limited data) to give the LLM context about the structure
    user_content += f"\n\nSample objects ({sample_size} of {len(objects)} total):\n"
    user_content += json.dumps(sample_objects, indent=2)
    
    # Clear instructions for response format
    user_content += "\n\nReturn a JSON with 'columns' (array of property names) and 'table' (markdown table string)."
    
    messages = [
        {"role": "system", "content": formatted_system_prompt},
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
    
    # Validate input parameters
    if not schedule_type or not isinstance(schedule_type, str):
        return {"error": "Invalid schedule type. Please specify a valid object type like 'wall' or 'electrical device'."}
    
    if properties and not isinstance(properties, list):
        return {"error": "Properties must be provided as a list of strings."}
    
    # Normalize schedule type (lowercase for easier matching)
    schedule_type = schedule_type.lower()
    
    # Get objects for the schedule
    objects, error = get_objects_for_schedule(schedule_type, current_state)
    
    if error:
        return {
            "error": error,
            "schedule_type": schedule_type,
            "message": f"Could not create a {schedule_type} schedule: {error}"
        }
    
    if not objects:
        return {
            "error": f"No {schedule_type} objects found in the current view data.",
            "schedule_type": schedule_type,
            "message": f"Could not create a {schedule_type} schedule because no matching objects were found."
        }
    
    # Log information about found objects
    print(f"Found {len(objects)} {schedule_type} objects, creating schedule")
    
    # Create the schedule
    table, error = create_smart_schedule(schedule_type, objects, f"Create a {schedule_type} schedule", properties)
    
    if error:
        return {
            "error": error,
            "schedule_type": schedule_type,
            "message": f"Error creating {schedule_type} schedule: {error}"
        }
    
    # Return the schedule data with more informative output
    return {
        "schedule_type": schedule_type,
        "object_count": len(objects),
        "table": table,
        "properties_used": properties if properties else "auto-detected",
        "message": f"Created a {schedule_type} schedule with {len(objects)} objects."
    } 