# Data Management and Model Derivative APIs
import os
import requests
import json
import base64
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
            "selected_view": None,
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
        elif "views" in result:
            master_view_name = result.get('master_view', {}).get('name', 'unknown')
            return f"Found {result.get('count', 0)} views for version {result.get('version_urn', 'unknown')}, master view: {master_view_name}"
        elif "properties" in result and "collection_count" in result:
            return f"Found {result.get('collection_count', 0)} collections with {result.get('object_count', 0)} objects for view {result.get('view_guid', 'unknown')}"
        
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
        if state["selected_view"]:
            view_name = state["selected_view"].get('name', 'Unknown')
            summary.append(f"Selected view: {view_name}")
        if state["last_api_call"]:
            summary.append(f"Last API call: {state['last_api_call']}")
        
        return " | ".join(summary) if summary else "No state information available"
    
    def dump_state(self):
        """Dump the current state of the ChatMemory for debugging"""
        print("\n=== ChatMemory State ===")
        print(f"Selected hub: {self.current_state['selected_hub']}")
        print(f"Selected project: {self.current_state['selected_project']}")
        print(f"Selected item: {self.current_state['selected_item']}")
        if self.current_state['selected_view']:
            print(f"Selected view: {self.current_state['selected_view'].get('name', 'Unknown')} (GUID: {self.current_state['selected_view'].get('guid', 'Unknown')})")
        else:
            print(f"Selected view: None")
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
            "versions": {},   # Dictionary with project_id:item_id as key
            "views": {},       # Dictionary with encoded_urn as key
            "properties": {},   # Dictionary with version_urn:view_guid as key
            "objects": {}       # Dictionary with encoded_urn:view_guid:objects as key
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

    def get_model_views(self, version_urn: str):
        """
        Retrieve the list of views (metadata) for a given model version.
        
        Args:
            version_urn (str): The URN of the version (e.g., "urn:adsk.wipprod:fs.file:vf.-3ver-faSemSdPmFvD5ZFQ?version=3")
            
        Returns:
            dict: Formatted view information including the master view and all available views
        """
        # Convert the version URN to a Base64 URL-safe encoded string
        try:
            # Encode the full URN including query parameters
            encoded_urn = base64.urlsafe_b64encode(version_urn.encode()).decode().rstrip('=')
            print(f"\n[API] Converted version URN to encoded URN: {encoded_urn}")
            print(f"[API] Full encoded URN for debugging: {encoded_urn}")
            print(f"[API] Original URN: {version_urn}")
        except Exception as e:
            print(f"[API] Error encoding version URN: {str(e)}")
            return {"error": f"Failed to encode version URN: {str(e)}"}
        
        # Check if we have cached views for this encoded URN
        if encoded_urn in self.cache["views"]:
            print(f"\n[API] Using cached views data for encoded URN {encoded_urn}")
            return self.cache["views"][encoded_urn]
            
        print(f"\n[API] Calling get_model_views endpoint for encoded URN {encoded_urn}...")
        url = f"https://developer.api.autodesk.com/modelderivative/v2/designdata/{encoded_urn}/metadata"
        response = requests.get(url, headers=self.headers)
        print(f"[API] GET Model Views Response: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                # Check if 'data' and 'metadata' exist in the response
                if 'data' in data and 'metadata' in data['data']:
                    views = data['data']['metadata']
                    
                    # Find the master view
                    master_view = None
                    for view in views:
                        if view.get('isMasterView', False):
                            master_view = view
                            break
                    
                    # If no master view is found, try to find a 3D view
                    if not master_view:
                        for view in views:
                            if view.get('role') == '3d':
                                master_view = view
                                break
                    
                    # If still no view is found, use the first view
                    if not master_view and views:
                        master_view = views[0]
                    
                    result = {
                        'version_urn': version_urn,
                        'encoded_urn': encoded_urn,
                        'views': views,
                        'master_view': master_view,
                        'count': len(views)
                    }
                    print(f"[API] Successfully retrieved {len(views)} views for model")
                    
                    # Cache the result
                    self.cache["views"][encoded_urn] = result
                    
                    return result
                else:
                    print("[API] Error: No metadata found in response")
                    return {"error": "No metadata found in response", "raw_data": data}
            except Exception as e:
                print(f"[API] Error parsing metadata: {str(e)}")
                return {"error": f"Failed to parse metadata: {str(e)}", "raw_data": response.text}
        else:
            print(f"[API] Error response: {response.text}")
            return {"error": f"API request failed with status code {response.status_code}"}

    def get_view_properties(self, version_urn: str, view_guid: str):
        """
        Retrieve the properties for a specific view of a model.
        
        Args:
            version_urn (str): The URN of the version (e.g., "urn:adsk.wipprod:fs.file:vf.-3ver-faSemSdPmFvD5ZFQ?version=3")
            view_guid (str): The GUID of the view to get properties for
            
        Returns:
            dict: Formatted property information for the view
        """
        # Convert the version URN to a Base64 URL-safe encoded string
        try:
            # Encode the full URN including query parameters
            encoded_urn = base64.urlsafe_b64encode(version_urn.encode()).decode().rstrip('=')
            print(f"\n[API] Using encoded URN: {encoded_urn} for view properties")
            print(f"[API] Original URN: {version_urn}")
        except Exception as e:
            print(f"[API] Error encoding version URN: {str(e)}")
            return {"error": f"Failed to encode version URN: {str(e)}"}
        
        # Create a composite key for the cache
        cache_key = f"{encoded_urn}:{view_guid}"
        
        # Check if we have cached properties for this view
        if "properties" in self.cache and cache_key in self.cache["properties"]:
            print(f"\n[API] Using cached properties data for view {view_guid}")
            return self.cache["properties"][cache_key]
            
        print(f"\n[API] Calling get_view_properties endpoint for view {view_guid}...")
        url = f"https://developer.api.autodesk.com/modelderivative/v2/designdata/{encoded_urn}/metadata/{view_guid}/properties"
        response = requests.get(url, headers=self.headers)
        print(f"[API] GET View Properties Response: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                # Check if 'data' exists in the response
                if 'data' in data:
                    properties_data = data['data']
                    
                    # Extract collection and object counts
                    collection_count = len(properties_data.get('collection', []))
                    object_count = 0
                    for collection in properties_data.get('collection', []):
                        object_count += len(collection.get('objects', []))
                    
                    result = {
                        'version_urn': version_urn,
                        'encoded_urn': encoded_urn,
                        'view_guid': view_guid,
                        'properties': properties_data,
                        'collection_count': collection_count,
                        'object_count': object_count
                    }
                    print(f"[API] Successfully retrieved properties for view {view_guid}")
                    print(f"[API] Found {collection_count} collections with {object_count} total objects")
                    
                    # Ensure the properties cache exists
                    if "properties" not in self.cache:
                        self.cache["properties"] = {}
                    
                    # Cache the result
                    self.cache["properties"][cache_key] = result
                    
                    return result
                else:
                    print("[API] Error: No property data found in response")
                    return {"error": "No property data found in response", "raw_data": data}
            except Exception as e:
                print(f"[API] Error parsing property data: {str(e)}")
                return {"error": f"Failed to parse property data: {str(e)}", "raw_data": response.text}
        else:
            print(f"[API] Error response: {response.text}")
            return {"error": f"API request failed with status code {response.status_code}"}

    def get_view_objects(self, version_urn: str, view_guid: str):
        """
        Retrieve the object hierarchy for a specific view of a model.
        
        Args:
            version_urn (str): The URN of the version (e.g., "urn:adsk.wipprod:fs.file:vf.-3ver-faSemSdPmFvD5ZFQ?version=3")
            view_guid (str): The GUID of the view to get objects for
            
        Returns:
            dict: Formatted object hierarchy information for the view
        """
        # Convert the version URN to a Base64 URL-safe encoded string
        try:
            # Encode the full URN including query parameters
            encoded_urn = base64.urlsafe_b64encode(version_urn.encode()).decode().rstrip('=')
            print(f"\n[API] Using encoded URN: {encoded_urn} for view objects")
            print(f"[API] Original URN: {version_urn}")
        except Exception as e:
            print(f"[API] Error encoding version URN: {str(e)}")
            return {"error": f"Failed to encode version URN: {str(e)}"}
        
        # Create a composite key for the cache
        cache_key = f"{encoded_urn}:{view_guid}:objects"
        
        # Check if we have cached objects for this view
        if "objects" in self.cache and cache_key in self.cache["objects"]:
            print(f"\n[API] Using cached objects data for view {view_guid}")
            return self.cache["objects"][cache_key]
            
        print(f"\n[API] Calling get_view_objects endpoint for view {view_guid}...")
        url = f"https://developer.api.autodesk.com/modelderivative/v2/designdata/{encoded_urn}/metadata/{view_guid}"
        response = requests.get(url, headers=self.headers)
        print(f"[API] GET View Objects Response: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                # Check if 'data' exists in the response
                if 'data' in data:
                    objects_data = data['data']
                    
                    # Count the total number of objects
                    object_count = self._count_objects(objects_data.get('objects', []))
                    
                    result = {
                        'version_urn': version_urn,
                        'encoded_urn': encoded_urn,
                        'view_guid': view_guid,
                        'objects': objects_data,
                        'object_count': object_count
                    }
                    print(f"[API] Successfully retrieved objects for view {view_guid}")
                    print(f"[API] Found {object_count} total objects in the hierarchy")
                    
                    # Ensure the objects cache exists
                    if "objects" not in self.cache:
                        self.cache["objects"] = {}
                    
                    # Cache the result
                    self.cache["objects"][cache_key] = result
                    
                    return result
                else:
                    print("[API] Error: No object data found in response")
                    return {"error": "No object data found in response", "raw_data": data}
            except Exception as e:
                print(f"[API] Error parsing object data: {str(e)}")
                return {"error": f"Failed to parse object data: {str(e)}", "raw_data": response.text}
        else:
            print(f"[API] Error response: {response.text}")
            return {"error": f"API request failed with status code {response.status_code}"}
    
    def _count_objects(self, objects_list):
        """
        Recursively count the total number of objects in the hierarchy.
        
        Args:
            objects_list (list): List of objects to count
            
        Returns:
            int: Total number of objects
        """
        if not objects_list:
            return 0
            
        count = len(objects_list)
        
        # Recursively count nested objects
        for obj in objects_list:
            if isinstance(obj, dict) and 'objects' in obj:
                count += self._count_objects(obj.get('objects', []))
                
        return count

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
def get_model_views(version_urn):
    """
    Retrieve the list of views (metadata) for a given model version.
    
    Args:
        version_urn (str): The URN of the version
        
    Returns:
        dict: Formatted view information including the master view and all available views
    """
    return _api_helper.get_model_views(version_urn)

def get_view_properties(version_urn, view_guid):
    """
    Retrieve the properties for a specific view of a model.
    
    Args:
        version_urn (str): The URN of the version
        view_guid (str): The GUID of the view to get properties for
        
    Returns:
        dict: Formatted property information for the view
    """
    return _api_helper.get_view_properties(version_urn, view_guid)

def get_view_objects(version_urn, view_guid):
    """
    Retrieve the object hierarchy for a specific view of a model.
    
    Args:
        version_urn (str): The URN of the version (e.g., "urn:adsk.wipprod:fs.file:vf.-3ver-faSemSdPmFvD5ZFQ?version=3")
        view_guid (str): The GUID of the view to get objects for
        
    Returns:
        dict: Formatted object hierarchy information for the view
    """
    return _api_helper.get_view_objects(version_urn, view_guid)

# Model Derivative APIs (Stubs for future implementation)


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
                    elif function_name == "get_model_views" and function_args:
                        version_urn = function_args.get("version_urn")
                        if result.get("master_view"):
                            _chat_memory.current_state["selected_view"] = result.get("master_view")
                            print(f"[MEMORY] Updated selected_view to {result.get('master_view').get('name', 'Unknown')}")
                    elif function_name == "get_view_properties" and function_args:
                        version_urn = function_args.get("version_urn")
                        view_guid = function_args.get("view_guid")
                        # We don't update selected_view here as it should already be set by get_model_views
                        print(f"[MEMORY] Retrieved properties for view {view_guid}")
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
        elif function_name == "get_model_views" and function_args:
            version_urn = function_args.get("version_urn")
            print(f"[MEMORY] Pre-execution: Retrieving views for version {version_urn}")
        elif function_name == "get_view_properties" and function_args:
            version_urn = function_args.get("version_urn")
            view_guid = function_args.get("view_guid")
            print(f"[MEMORY] Pre-execution: Retrieving properties for view {view_guid}")

def get_recent_interactions(count=5):
    return _chat_memory.get_recent_interactions(count)

def get_current_state():
    return _chat_memory.get_current_state()

def get_state_summary():
    return _chat_memory.get_state_summary()

def dump_memory_state():
    """Dump the current state of the ChatMemory for debugging"""
    _chat_memory.dump_state()
