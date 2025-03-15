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
        print(f"[MEMORY] ChatMemory.add_interaction: {function_name} with args {function_args}")
        
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
                hub_id = function_args.get("hub_id")
                self.current_state["selected_hub"] = hub_id
                print(f"[MEMORY] ChatMemory: Updated selected_hub to {hub_id}")
            elif function_name == "filter_projects" and function_args:
                hub_id = function_args.get("hub_id")
                self.current_state["selected_hub"] = hub_id
                print(f"[MEMORY] ChatMemory: Updated selected_hub to {hub_id}")
            elif function_name == "get_items" and function_args:
                project_id = function_args.get("project_id")
                self.current_state["selected_project"] = project_id
                print(f"[MEMORY] ChatMemory: Updated selected_project to {project_id}")
            elif function_name == "get_versions" and function_args:
                project_id = function_args.get("project_id")
                item_id = function_args.get("item_id")
                self.current_state["selected_project"] = project_id
                self.current_state["selected_item"] = item_id
                print(f"[MEMORY] ChatMemory: Updated selected_project to {project_id} and selected_item to {item_id}")
    
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
            if "filter_applied" in result:
                return f"Found {result.get('count', 0)} projects starting with '{result.get('filter_applied')}' for hub {result.get('hub_id', 'unknown')}"
            else:
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
    
    def dump_state(self):
        """Dump the current state of the ChatMemory for debugging"""
        print("\n=== ChatMemory State ===")
        print(f"Selected hub: {self.current_state['selected_hub']}")
        print(f"Selected project: {self.current_state['selected_project']}")
        print(f"Selected item: {self.current_state['selected_item']}")
        print(f"Last API call: {self.current_state['last_api_call']}")
        print(f"Recent interactions: {len(self.interactions)}")
        for i, interaction in enumerate(self.interactions[-5:]):
            print(f"  {i+1}. {interaction['function_called']} - {interaction['result_summary']}")
        print("=======================\n")

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
        
        # Simple cache for API responses
        self.cache = {
            "hubs": None,
            "projects": {},  # Dictionary with hub_id as key
            "items": {},     # Dictionary with project_id as key
            "versions": {}   # Dictionary with project_id:item_id as key
        }
    
    def get_hubs(self):
        """
        Retrieve the list of hubs from APS.
        
        Returns:
            dict: Formatted hub information with just id and name
        """
        # Check if we have cached hubs
        if self.cache["hubs"]:
            print("\n[API] Using cached hubs data")
            return self.cache["hubs"]
            
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
                    
                    # Cache the result
                    self.cache["hubs"] = result
                    
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
        # Check if we have cached projects for this hub
        if hub_id in self.cache["projects"]:
            print(f"\n[API] Using cached projects data for hub {hub_id}")
            return self.cache["projects"][hub_id]
            
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
                    
                    # Cache the result
                    self.cache["projects"][hub_id] = result
                    
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

    def filter_projects(self, hub_id: str, prefix: str = None):
        """
        Filter projects for a given hub by name prefix.
        
        Args:
            hub_id (str): The ID of the hub
            prefix (str, optional): Filter projects whose name starts with this prefix
            
        Returns:
            dict: Filtered project information
        """
        # First, ensure we have the projects data
        projects_data = self.get_projects(hub_id)
        
        # If there was an error or no projects, return as is
        if "error" in projects_data or projects_data.get("count", 0) == 0:
            return projects_data
            
        # If no prefix is provided, return all projects
        if not prefix:
            return projects_data
            
        # Filter projects by prefix
        filtered_projects = [
            project for project in projects_data["projects"] 
            if project["name"].startswith(prefix)
        ]
        
        # Create a new result with filtered projects
        result = {
            'hub_id': hub_id,
            'projects': filtered_projects,
            'count': len(filtered_projects),
            'filter_applied': prefix
        }
        
        print(f"[API] Filtered to {len(filtered_projects)} projects starting with '{prefix}'")
        
        return result

    def get_items(self, project_id: str):
        """
        Retrieve the list of items (files) for a given project.
        
        This method:
        1. Gets the top folders for the project
        2. Finds the "Project Files" folder
        3. Recursively retrieves all files in that folder and its subfolders
        
        Args:
            project_id (str): The ID of the project
            
        Returns:
            dict: Formatted item information including id, name, and file type
        """
        # Check if we have cached items for this project
        if project_id in self.cache["items"]:
            print(f"\n[API] Using cached items data for project {project_id}")
            return self.cache["items"][project_id]
        
        print(f"\n[API] Retrieving items for project {project_id}...")
        
        # We need the hub_id for the top folders endpoint
        hub_id = None
        
        # First, try to get hub_id from the global ChatMemory's current_state
        if _chat_memory and hasattr(_chat_memory, 'current_state') and _chat_memory.current_state.get("selected_hub"):
            hub_id = _chat_memory.current_state.get("selected_hub")
            print(f"[API] Using hub_id {hub_id} from chat memory")
        else:
            print("[API] No hub_id found in chat memory")
        
        # If not found in chat memory, try to get it from the cache
        if not hub_id:
            print("[API] Searching for hub_id in projects cache...")
            for hub_id_key, projects_data in self.cache["projects"].items():
                print(f"[API] Checking hub {hub_id_key}...")
                for project in projects_data.get("projects", []):
                    if project.get("id") == project_id:
                        hub_id = hub_id_key
                        print(f"[API] Found hub_id {hub_id} in cache for project {project_id}")
                        break
                if hub_id:
                    break
        
        if not hub_id:
            print("[API] Error: Could not determine hub_id for the project")
            return {"error": "Could not determine hub_id for the project. Please list projects for a hub first."}
        
        print(f"\n[API] Getting top folders for project {project_id} in hub {hub_id}...")
        # Get top folders
        top_folders_url = f"https://developer.api.autodesk.com/project/v1/hubs/{hub_id}/projects/{project_id}/topFolders"
        top_folders_response = requests.get(top_folders_url, headers=self.headers)
        
        if top_folders_response.status_code != 200:
            print(f"[API] Error getting top folders: {top_folders_response.status_code}")
            print(f"[API] Response: {top_folders_response.text}")
            return {"error": f"Failed to get top folders: {top_folders_response.text}"}
        
        top_folders_data = top_folders_response.json()
        project_files_folder = None
        
        # Find the "Project Files" folder
        if 'data' in top_folders_data:
            print(f"[API] Found {len(top_folders_data['data'])} top folders")
            for folder in top_folders_data['data']:
                folder_name = folder.get('attributes', {}).get('name', '').lower()
                print(f"[API] Checking folder: {folder_name}")
                if 'project files' in folder_name:
                    project_files_folder = folder
                    break
        
        if not project_files_folder:
            print("[API] Error: Could not find 'Project Files' folder in the project")
            return {"error": "Could not find 'Project Files' folder in the project"}
        
        folder_id = project_files_folder.get('id')
        print(f"[API] Found Project Files folder with ID: {folder_id}")
        
        # Now recursively get all files in the Project Files folder
        all_items = []
        self._get_folder_contents(project_id, folder_id, all_items)
        
        # Format the result
        result = {
            'project_id': project_id,
            'items': all_items,
            'count': len(all_items)
        }
        
        print(f"[API] Successfully retrieved {len(all_items)} items for project {project_id}")
        
        # Cache the result
        self.cache["items"][project_id] = result
        
        return result
    
    def _get_folder_contents(self, project_id: str, folder_id: str, all_items: list, depth: int = 0):
        """
        Recursively retrieve contents of a folder and its subfolders.
        
        Args:
            project_id (str): The ID of the project
            folder_id (str): The ID of the folder to get contents from
            all_items (list): List to append items to (modified in place)
            depth (int): Current recursion depth (to prevent infinite recursion)
        """
        # Prevent too deep recursion
        if depth > 10:
            print(f"[API] Warning: Maximum folder depth reached for folder {folder_id}")
            return
        
        indent = "  " * depth  # For prettier logging
        print(f"{indent}[API] Getting contents of folder {folder_id} (depth: {depth})...")
        folder_contents_url = f"https://developer.api.autodesk.com/data/v1/projects/{project_id}/folders/{folder_id}/contents"
        folder_contents_response = requests.get(folder_contents_url, headers=self.headers)
        
        if folder_contents_response.status_code != 200:
            print(f"{indent}[API] Error getting folder contents: {folder_contents_response.status_code}")
            print(f"{indent}[API] Response: {folder_contents_response.text}")
            return
        
        folder_contents_data = folder_contents_response.json()
        
        if 'data' in folder_contents_data:
            items_count = len(folder_contents_data['data'])
            print(f"{indent}[API] Found {items_count} items in folder {folder_id}")
            
            folders_count = 0
            files_count = 0
            
            for item in folder_contents_data['data']:
                item_type = item.get('type', '')
                
                # If it's a folder, recursively get its contents
                if item_type == 'folders':
                    folders_count += 1
                    subfolder_id = item.get('id')
                    subfolder_name = item.get('attributes', {}).get('name', 'Unknown Folder')
                    print(f"{indent}[API] Found subfolder: {subfolder_name} (ID: {subfolder_id})")
                    self._get_folder_contents(project_id, subfolder_id, all_items, depth + 1)
                
                # If it's an item (file), add it to our list
                elif item_type == 'items':
                    files_count += 1
                    attributes = item.get('attributes', {})
                    item_name = attributes.get('displayName', 'Unknown Item')
                    
                    # Format last modified date if it exists
                    last_modified = attributes.get('lastModifiedTime', '')
                    if last_modified:
                        try:
                            dt = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
                            last_modified = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            # Keep original if parsing fails
                            pass
                    
                    item_info = {
                        'id': item.get('id', 'Unknown ID'),
                        'name': item_name,
                        'file_type': attributes.get('fileType', 'Unknown'),
                        'last_modified': last_modified,
                        'version_id': attributes.get('versionId', '')
                    }
                    all_items.append(item_info)
            
            print(f"{indent}[API] Processed {folders_count} folders and {files_count} files in folder {folder_id}")
        else:
            print(f"{indent}[API] No data found in folder {folder_id}")
            if 'errors' in folder_contents_data:
                print(f"{indent}[API] Errors: {folder_contents_data['errors']}")

    def get_versions(self, project_id: str, item_id: str):
        """
        Retrieve the versions for a given item in a project.
        
        Args:
            project_id (str): The ID of the project
            item_id (str): The ID of the item
            
        Returns:
            dict: Formatted version information with relevant details
        """
        # Create a composite key for the cache
        cache_key = f"{project_id}:{item_id}"
        
        # Check if we have cached versions for this item
        if cache_key in self.cache["versions"]:
            print(f"\n[API] Using cached versions data for project {project_id}, item {item_id}")
            return self.cache["versions"][cache_key]
            
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
                    
                    # Cache the result
                    self.cache["versions"][cache_key] = result
                    
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

def filter_projects(hub_id, prefix=None):
    return _api_helper.filter_projects(hub_id, prefix)

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
    print(f"[MEMORY] Adding interaction: {function_name} with args {function_args}")
    
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
                        hub_id = function_args.get("hub_id")
                        _chat_memory.current_state["selected_hub"] = hub_id
                        print(f"[MEMORY] Updated selected_hub to {hub_id}")
                    elif function_name == "filter_projects" and function_args:
                        hub_id = function_args.get("hub_id")
                        _chat_memory.current_state["selected_hub"] = hub_id
                        print(f"[MEMORY] Updated selected_hub to {hub_id}")
                    elif function_name == "get_items" and function_args:
                        project_id = function_args.get("project_id")
                        _chat_memory.current_state["selected_project"] = project_id
                        print(f"[MEMORY] Updated selected_project to {project_id}")
                    elif function_name == "get_versions" and function_args:
                        project_id = function_args.get("project_id")
                        item_id = function_args.get("item_id")
                        _chat_memory.current_state["selected_project"] = project_id
                        _chat_memory.current_state["selected_item"] = item_id
                        print(f"[MEMORY] Updated selected_project to {project_id} and selected_item to {item_id}")
                return
    
    # If no matching entry was found or this is a pre-execution entry, add a new one
    _chat_memory.add_interaction(user_query, intent, function_name, function_args, result)
    
    # If this is a pre-execution entry (no result), update the current state for certain functions
    if result is None and function_name:
        if function_name == "get_projects" and function_args:
            hub_id = function_args.get("hub_id")
            _chat_memory.current_state["selected_hub"] = hub_id
            print(f"[MEMORY] Pre-execution: Updated selected_hub to {hub_id}")
        elif function_name == "filter_projects" and function_args:
            hub_id = function_args.get("hub_id")
            _chat_memory.current_state["selected_hub"] = hub_id
            print(f"[MEMORY] Pre-execution: Updated selected_hub to {hub_id}")
        elif function_name == "get_items" and function_args:
            project_id = function_args.get("project_id")
            _chat_memory.current_state["selected_project"] = project_id
            print(f"[MEMORY] Pre-execution: Updated selected_project to {project_id}")
        elif function_name == "get_versions" and function_args:
            project_id = function_args.get("project_id")
            item_id = function_args.get("item_id")
            _chat_memory.current_state["selected_project"] = project_id
            _chat_memory.current_state["selected_item"] = item_id
            print(f"[MEMORY] Pre-execution: Updated selected_project to {project_id} and selected_item to {item_id}")

def get_recent_interactions(count=5):
    return _chat_memory.get_recent_interactions(count)

def get_current_state():
    return _chat_memory.get_current_state()

def get_state_summary():
    return _chat_memory.get_state_summary()

def dump_memory_state():
    """Dump the current state of the ChatMemory for debugging"""
    _chat_memory.dump_state()
