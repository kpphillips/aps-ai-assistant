# Data Management and Model Derivative APIs
import os
import requests
import json
from datetime import datetime

# Get the APS_AUTH_TOKEN from environment variables
APS_AUTH_TOKEN = os.environ.get("APS_AUTH_TOKEN")
if not APS_AUTH_TOKEN:
    raise ValueError("APS_AUTH_TOKEN environment variable is not set")

# Common headers for Autodesk API requests
_HEADERS = {
    "Authorization": f"Bearer {APS_AUTH_TOKEN}",
    "Content-Type": "application/json"
}

# Data Management APIs

def get_hubs():
    """
    Retrieve the list of hubs from APS.
    
    Returns:
        dict: Formatted hub information with just id and name
    """
    url = "https://developer.api.autodesk.com/project/v1/hubs"
    response = requests.get(url, headers=_HEADERS)
    print(f"GET Hubs Response: {response.status_code}")
    
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
                
                return {
                    'hubs': formatted_hubs,
                    'count': len(formatted_hubs)
                }
            else:
                return {"error": "No hubs data found in response", "raw_data": data}
        except Exception as e:
            print(f"Error parsing hub data: {str(e)}")
            return {"error": f"Failed to parse hub data: {str(e)}", "raw_data": response.text}
    else:
        print(f"Error response: {response.text}")
        return {"error": f"API request failed with status code {response.status_code}"}

def get_projects(hub_id: str):
    """
    Retrieve the list of projects for a given hub.
    
    Args:
        hub_id (str): The ID of the hub
        
    Returns:
        dict: Formatted project information with just id and name
    """
    url = f"https://developer.api.autodesk.com/project/v1/hubs/{hub_id}/projects"
    response = requests.get(url, headers=_HEADERS)
    print(f"GET Projects Response for hub {hub_id}: {response.status_code}")
    
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
                
                return {
                    'hub_id': hub_id,
                    'projects': formatted_projects,
                    'count': len(formatted_projects)
                }
            else:
                return {"error": "No project data found in response", "raw_data": data}
        except Exception as e:
            print(f"Error parsing project data: {str(e)}")
            return {"error": f"Failed to parse project data: {str(e)}", "raw_data": response.text}
    else:
        print(f"Error response: {response.text}")
        return {"error": f"API request failed with status code {response.status_code}"}

def get_items(project_id: str):
    """
    Retrieve the list of items for a given project.
    
    Args:
        project_id (str): The ID of the project
        
    Returns:
        dict: Formatted item information including id, name, and file type
    """
    url = f"https://developer.api.autodesk.com/data/v1/projects/{project_id}/items"
    response = requests.get(url, headers=_HEADERS)
    print(f"GET Items Response for project {project_id}: {response.status_code}")
    
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
                
                return {
                    'project_id': project_id,
                    'items': formatted_items,
                    'count': len(formatted_items)
                }
            else:
                return {"error": "No item data found in response", "raw_data": data}
        except Exception as e:
            print(f"Error parsing item data: {str(e)}")
            return {"error": f"Failed to parse item data: {str(e)}", "raw_data": response.text}
    else:
        print(f"Error response: {response.text}")
        return {"error": f"API request failed with status code {response.status_code}"}

def get_versions(project_id: str, item_id: str):
    """
    Retrieve the versions for a given item in a project.
    
    Args:
        project_id (str): The ID of the project
        item_id (str): The ID of the item
        
    Returns:
        dict: Formatted version information with relevant details
    """
    url = f"https://developer.api.autodesk.com/data/v1/projects/{project_id}/items/{item_id}/versions"
    response = requests.get(url, headers=_HEADERS)
    print(f"GET Versions Response for project {project_id}, item {item_id}: {response.status_code}")
    
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
                        'storage_size': format_file_size(attributes.get('storageSize', 0))
                    }
                    formatted_versions.append(version_info)
                
                # Sort versions by version number (descending)
                formatted_versions.sort(key=lambda x: x['version_number'], reverse=True)
                
                return {
                    'project_id': project_id,
                    'item_id': item_id,
                    'versions': formatted_versions,
                    'count': len(formatted_versions)
                }
            else:
                return {"error": "No version data found in response", "raw_data": data}
        except Exception as e:
            print(f"Error parsing version data: {str(e)}")
            return {"error": f"Failed to parse version data: {str(e)}", "raw_data": response.text}
    else:
        print(f"Error response: {response.text}")
        return {"error": f"API request failed with status code {response.status_code}"}

def format_file_size(size_in_bytes):
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

# Model Derivative APIs (Stubs, to be implemented later)

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
