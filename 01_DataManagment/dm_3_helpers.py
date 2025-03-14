# Data Management and Model Derivative APIs
import os
import requests
import json
from datetime import datetime

class ChatMemory:
    """
    Simple class for storing minimal chat history and state.
    Maintains a record of interactions and API call results.
    """
    
    def __init__(self):
        """Initialize an empty chat memory"""
        self.interactions = []
        self.current_state = {
            "selected_hub": None,
            "selected_project": None,
            "selected_item": None,
            "last_api_call": None,
            "last_api_result": None
        }
    
    def add_interaction(self, user_query, intent, function_name=None, function_args=None, result=None):
        """
        Add a new interaction to the memory
        
        Args:
            user_query (str): The user's original query
            intent (str): A short description of what the assistant understood
            function_name (str, optional): The name of the function called
            function_args (dict, optional): The arguments passed to the function
            result (dict, optional): The result of the function call
        """
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "user_query": user_query,
            "intent": intent,
            "function_called": function_name,
            "function_args": function_args,
            "result_summary": self._summarize_result(result) if result else None
        }
        
        self.interactions.append(interaction)
        
        # Update current state based on function call
        if function_name and result and (not isinstance(result, dict) or not result.get("error")):
            self.current_state["last_api_call"] = function_name
            self.current_state["last_api_result"] = result
            
            # Update state based on specific function calls
            if function_name == "get_projects" and function_args:
                self.current_state["selected_hub"] = function_args.get("hub_id")
            elif function_name == "get_items" and function_args:
                self.current_state["selected_project"] = function_args.get("project_id")
            elif function_name == "get_versions" and function_args:
                self.current_state["selected_project"] = function_args.get("project_id")
                self.current_state["selected_item"] = function_args.get("item_id")
    
    def _summarize_result(self, result):
        """Create a minimal summary of an API result"""
        if not result or not isinstance(result, dict):
            return "No result or invalid result format"
        
        # Check for error
        if "error" in result:
            return f"Error: {result['error']}"
        
        # Summarize based on result type
        if "hubs" in result:
            return f"Found {result.get('count', 0)} hubs"
        elif "projects" in result:
            return f"Found {result.get('count', 0)} projects for hub {result.get('hub_id', 'unknown')}"
        elif "items" in result:
            return f"Found {result.get('count', 0)} items for project {result.get('project_id', 'unknown')}"
        elif "versions" in result:
            return f"Found {result.get('count', 0)} versions for item {result.get('item_id', 'unknown')}"
        
        return "Result received but format unknown"
    
    def get_recent_interactions(self, count=5):
        """Get the most recent interactions"""
        return self.interactions[-count:] if self.interactions else []
    
    def get_current_state(self):
        """Get the current state"""
        return self.current_state
    
    def get_state_summary(self):
        """Get a text summary of the current state"""
        state = self.current_state
        summary = []
        
        if state["selected_hub"]:
            summary.append(f"Selected hub: {state['selected_hub']}")
        if state["selected_project"]:
            summary.append(f"Selected project: {state['selected_project']}")
        if state["selected_item"]:
            summary.append(f"Selected item: {state['selected_item']}")
        if state["last_api_call"]:
            summary.append(f"Last API call: {state['last_api_call']}")
        
        return " | ".join(summary) if summary else "No state information available"

class AutodeskAPIHelper:
    """
    Class for handling Autodesk Platform Services (APS) API calls.
    Provides methods for working with Data Management and Model Derivative APIs.
    """
    
    def __init__(self):
        """Initialize with APS token from environment variable"""
        self.token = os.environ.get("APS_AUTH_TOKEN")
        if not self.token:
            raise ValueError("APS_AUTH_TOKEN environment variable is not set")
        
        # Common headers for Autodesk API requests
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def get_hubs(self):
        """
        Retrieve the list of hubs from APS.
        
        Returns:
            dict: Formatted hub information with just id and name
        """
        print("\n[API] Calling get_hubs endpoint...")
        url = "https://developer.api.autodesk.com/project/v1/hubs"
        response = requests.get(url, headers=self.headers)
        print(f"[API] GET Hubs Response: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                formatted_hubs = []
                
                # Check if 'data' exists in the response
                if 'data' in data:
                    for hub in data['data']:
                        hub_info = {
                            'id': hub.get('id', 'Unknown ID'),
                            'name': hub.get('attributes', {}).get('name', 'Unknown Hub')
                        }
                        formatted_hubs.append(hub_info)
                    
                    result = {
                        'hubs': formatted_hubs,
                        'count': len(formatted_hubs)
                    }
                    print(f"[API] Successfully retrieved {len(formatted_hubs)} hubs")
                    return result
                else:
                    print("[API] Error: No hubs data found in response")
                    return {"error": "No hubs data found in response", "raw_data": data}
            except Exception as e:
                print(f"[API] Error parsing hub data: {str(e)}")
                return {"error": f"Failed to parse hub data: {str(e)}", "raw_data": response.text}
        else:
            print(f"[API] Error response: {response.text}")
            return {"error": f"API request failed with status code {response.status_code}"}

    def get_projects(self, hub_id: str):
        """
        Retrieve the list of projects for a given hub.
        
        Args:
            hub_id (str): The ID of the hub
            
        Returns:
            dict: Formatted project information with just id and name
        """
        print(f"\n[API] Calling get_projects endpoint for hub {hub_id}...")
        url = f"https://developer.api.autodesk.com/project/v1/hubs/{hub_id}/projects"
        response = requests.get(url, headers=self.headers)
        print(f"[API] GET Projects Response for hub {hub_id}: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                formatted_projects = []
                
                # Check if 'data' exists in the response
                if 'data' in data:
                    for project in data['data']:
                        project_info = {
                            'id': project.get('id', 'Unknown ID'),
                            'name': project.get('attributes', {}).get('name', 'Unknown Project')
                        }
                        formatted_projects.append(project_info)
                    
                    result = {
                        'hub_id': hub_id,
                        'projects': formatted_projects,
                        'count': len(formatted_projects)
                    }
                    print(f"[API] Successfully retrieved {len(formatted_projects)} projects for hub {hub_id}")
                    return result
                else:
                    print("[API] Error: No project data found in response")
                    return {"error": "No project data found in response", "raw_data": data}
            except Exception as e:
                print(f"[API] Error parsing project data: {str(e)}")
                return {"error": f"Failed to parse project data: {str(e)}", "raw_data": response.text}
        else:
            print(f"[API] Error response: {response.text}")
            return {"error": f"API request failed with status code {response.status_code}"}

    def get_items(self, project_id: str):
        """
        Retrieve the list of items for a given project.
        
        Args:
            project_id (str): The ID of the project
            
        Returns:
            dict: Formatted item information including id, name, and file type
        """
        print(f"\n[API] Calling get_items endpoint for project {project_id}...")
        url = f"https://developer.api.autodesk.com/data/v1/projects/{project_id}/items"
        response = requests.get(url, headers=self.headers)
        print(f"[API] GET Items Response for project {project_id}: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                formatted_items = []
                
                # Check if 'data' exists in the response
                if 'data' in data:
                    for item in data['data']:
                        # Extract file type and additional attributes if available
                        attributes = item.get('attributes', {})
                        file_type = attributes.get('fileType', 'Unknown')
                        last_modified = attributes.get('lastModifiedTime', '')
                        
                        # Format datetime if it exists
                        if last_modified:
                            try:
                                dt = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
                                last_modified = dt.strftime('%Y-%m-%d %H:%M:%S')
                            except:
                                # Keep original if parsing fails
                                pass
                        
                        item_info = {
                            'id': item.get('id', 'Unknown ID'),
                            'name': attributes.get('displayName', 'Unknown Item'),
                            'file_type': file_type,
                            'last_modified': last_modified,
                            'version_id': attributes.get('versionId', '')
                        }
                        formatted_items.append(item_info)
                    
                    result = {
                        'project_id': project_id,
                        'items': formatted_items,
                        'count': len(formatted_items)
                    }
                    print(f"[API] Successfully retrieved {len(formatted_items)} items for project {project_id}")
                    return result
                else:
                    print("[API] Error: No item data found in response")
                    return {"error": "No item data found in response", "raw_data": data}
            except Exception as e:
                print(f"[API] Error parsing item data: {str(e)}")
                return {"error": f"Failed to parse item data: {str(e)}", "raw_data": response.text}
        else:
            print(f"[API] Error response: {response.text}")
            return {"error": f"API request failed with status code {response.status_code}"}

    def get_versions(self, project_id: str, item_id: str):
        """
        Retrieve the versions for a given item in a project.
        
        Args:
            project_id (str): The ID of the project
            item_id (str): The ID of the item
            
        Returns:
            dict: Formatted version information with relevant details
        """
        print(f"\n[API] Calling get_versions endpoint for project {project_id}, item {item_id}...")
        url = f"https://developer.api.autodesk.com/data/v1/projects/{project_id}/items/{item_id}/versions"
        response = requests.get(url, headers=self.headers)
        print(f"[API] GET Versions Response for project {project_id}, item {item_id}: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                formatted_versions = []
                
                # Check if 'data' exists in the response
                if 'data' in data:
                    for version in data['data']:
                        attributes = version.get('attributes', {})
                        
                        # Format creation date if it exists
                        created_date = attributes.get('createTime', '')
                        if created_date:
                            try:
                                dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                                created_date = dt.strftime('%Y-%m-%d %H:%M:%S')
                            except:
                                # Keep original if parsing fails
                                pass
                        
                        version_info = {
                            'id': version.get('id', 'Unknown ID'),
                            'version_number': attributes.get('versionNumber', 0),
                            'name': attributes.get('displayName', 'Unknown Version'),
                            'created_by': attributes.get('createUserName', 'Unknown User'),
                            'created_date': created_date,
                            'file_type': attributes.get('fileType', 'Unknown'),
                            'storage_size': self.format_file_size(attributes.get('storageSize', 0))
                        }
                        formatted_versions.append(version_info)
                    
                    # Sort versions by version number (descending)
                    formatted_versions.sort(key=lambda x: x['version_number'], reverse=True)
                    
                    result = {
                        'project_id': project_id,
                        'item_id': item_id,
                        'versions': formatted_versions,
                        'count': len(formatted_versions)
                    }
                    print(f"[API] Successfully retrieved {len(formatted_versions)} versions for item {item_id}")
                    return result
                else:
                    print("[API] Error: No version data found in response")
                    return {"error": "No version data found in response", "raw_data": data}
            except Exception as e:
                print(f"[API] Error parsing version data: {str(e)}")
                return {"error": f"Failed to parse version data: {str(e)}", "raw_data": response.text}
        else:
            print(f"[API] Error response: {response.text}")
            return {"error": f"API request failed with status code {response.status_code}"}

    def format_file_size(self, size_in_bytes):
        """Format file size from bytes to a human-readable format"""
        if not isinstance(size_in_bytes, (int, float)):
            return "Unknown size"
        
        # Convert to float and handle zero size
        size = float(size_in_bytes)
        if size == 0:
            return "0 B"
        
        # Define size units and their corresponding thresholds
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        
        # Calculate the appropriate unit
        i = 0
        while size >= 1024 and i < len(units) - 1:
            size /= 1024
            i += 1
        
        # Return formatted string with up to 2 decimal places
        return f"{size:.2f} {units[i]}"


# Create a global instance of the helper class for backward compatibility
# with code that uses the module-level functions
_api_helper = AutodeskAPIHelper()

# For backward compatibility, expose the methods as module-level functions
def get_hubs():
    return _api_helper.get_hubs()

def get_projects(hub_id):
    return _api_helper.get_projects(hub_id)

def get_items(project_id):
    return _api_helper.get_items(project_id)

def get_versions(project_id, item_id):
    return _api_helper.get_versions(project_id, item_id)

def format_file_size(size_in_bytes):
    return _api_helper.format_file_size(size_in_bytes)

# Model Derivative APIs (Stubs for future implementation)
def get_Model_Views(urn: str):
    """Retrieve the viewables (model views) available for a model."""
    # To be implemented in the future
    return

def get_view_objects(urn: str, model_view_id: str):
    """Retrieve object data for a specific view of a model."""
    # To be implemented in the future
    return

def get_view_object_properties(urn: str, model_view_id: str):
    """Retrieve properties for objects in a specific view of a model."""
    # To be implemented in the future
    return

# Create a global instance of the ChatMemory class
_chat_memory = ChatMemory()

# Expose the chat memory instance through functions
def get_chat_memory():
    return _chat_memory

def add_interaction(user_query, intent, function_name=None, function_args=None, result=None):
    """
    Add an interaction to the chat memory.
    If result is None, this is considered a "pre-execution" entry.
    If result is provided, this updates the existing entry or creates a new one.
    """
    # If we have a result, try to update an existing entry first
    if result is not None and _chat_memory.interactions:
        # Look for a matching pre-execution entry (same function, args, no result)
        for interaction in reversed(_chat_memory.interactions):
            if (interaction["function_called"] == function_name and 
                interaction["function_args"] == function_args and
                interaction["result_summary"] is None):
                # Update this entry instead of creating a new one
                interaction["result_summary"] = _chat_memory._summarize_result(result)
                # Update the current state
                if function_name and (not isinstance(result, dict) or not result.get("error")):
                    _chat_memory.current_state["last_api_call"] = function_name
                    _chat_memory.current_state["last_api_result"] = result
                    
                    # Update state based on specific function calls
                    if function_name == "get_projects" and function_args:
                        _chat_memory.current_state["selected_hub"] = function_args.get("hub_id")
                    elif function_name == "get_items" and function_args:
                        _chat_memory.current_state["selected_project"] = function_args.get("project_id")
                    elif function_name == "get_versions" and function_args:
                        _chat_memory.current_state["selected_project"] = function_args.get("project_id")
                        _chat_memory.current_state["selected_item"] = function_args.get("item_id")
                return
    
    # If no matching entry was found or this is a pre-execution entry, add a new one
    _chat_memory.add_interaction(user_query, intent, function_name, function_args, result)

def get_recent_interactions(count=5):
    return _chat_memory.get_recent_interactions(count)

def get_current_state():
    return _chat_memory.get_current_state()

def get_state_summary():
    return _chat_memory.get_state_summary()
