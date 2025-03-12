''' Business Logic for Data Management APIs '''
import os
import json
from datetime import datetime
import requests
from dotenv import load_dotenv

from openai import OpenAI
from .dm_0_config import MODEL_NAME, MODEL_CONFIG
from .dm_1_prompts import DATA_MANAGEMENT_PROMPT

# Load environment variables
load_dotenv()

class APSManager:
    """Base class for APS API interactions"""
    
    def __init__(self):
        """Initialize with APS token"""
        self.token = os.environ.get("APS_AUTH_TOKEN")
        if not self.token:
            raise ValueError("APS_AUTH_TOKEN environment variable is not set")
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method, url, params=None, data=None):
        """Make an API request to the APS endpoint"""
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data
            )
            
            print(f"{method} {url} - Status: {response.status_code}")
            
            if response.status_code >= 200 and response.status_code < 300:
                return response.json() if response.content else {}
            else:
                print(f"Error response: {response.text}")
                return {"error": f"API request failed with status code {response.status_code}"}
                
        except Exception as e:
            print(f"Request error: {str(e)}")
            return {"error": f"Request error: {str(e)}"}

    @staticmethod
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


class HubManager(APSManager):
    """Class for managing hubs"""
    
    def get_hubs(self):
        """
        Retrieve the list of hubs from APS.
        
        Returns:
            dict: Formatted hub information with just id and name
        """
        url = "https://developer.api.autodesk.com/project/v1/hubs"
        data = self._make_request("GET", url)
        
        if "error" in data:
            return data
        
        try:
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
            return {"error": f"Failed to parse hub data: {str(e)}", "raw_data": data}


class ProjectManager(APSManager):
    """Class for managing projects"""
    
    def get_projects(self, hub_id):
        """
        Retrieve the list of projects for a given hub.
        
        Args:
            hub_id (str): The ID of the hub
            
        Returns:
            dict: Formatted project information with just id and name
        """
        url = f"https://developer.api.autodesk.com/project/v1/hubs/{hub_id}/projects"
        data = self._make_request("GET", url)
        
        if "error" in data:
            return data
        
        try:
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
            return {"error": f"Failed to parse project data: {str(e)}", "raw_data": data}

    def filter_projects(self, projects, criteria):
        """
        Filter projects based on criteria.
        
        Args:
            projects (list): List of project dictionaries
            criteria (str): Text to filter by (searches in name)
            
        Returns:
            list: Filtered list of projects
        """
        if not criteria:
            return projects
            
        return [p for p in projects if criteria.lower() in p.get('name', '').lower()]


class ItemManager(APSManager):
    """Class for managing items"""
    
    def get_items(self, project_id):
        """
        Retrieve the list of items for a given project.
        
        Args:
            project_id (str): The ID of the project
            
        Returns:
            dict: Formatted item information including id, name, and file type
        """
        url = f"https://developer.api.autodesk.com/data/v1/projects/{project_id}/items"
        data = self._make_request("GET", url)
        
        if "error" in data:
            return data
        
        try:
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
            return {"error": f"Failed to parse item data: {str(e)}", "raw_data": data}
    
    def filter_items(self, items, criteria):
        """
        Filter items based on criteria.
        
        Args:
            items (list): List of item dictionaries
            criteria (str): Text to filter by (searches in name and file_type)
            
        Returns:
            list: Filtered list of items
        """
        if not criteria:
            return items
            
        return [i for i in items if (
            criteria.lower() in i.get('name', '').lower() or 
            criteria.lower() in i.get('file_type', '').lower()
        )]


class VersionManager(APSManager):
    """Class for managing versions"""
    
    def get_versions(self, project_id, item_id):
        """
        Retrieve the versions for a given item in a project.
        
        Args:
            project_id (str): The ID of the project
            item_id (str): The ID of the item
            
        Returns:
            dict: Formatted version information with relevant details
        """
        url = f"https://developer.api.autodesk.com/data/v1/projects/{project_id}/items/{item_id}/versions"
        data = self._make_request("GET", url)
        
        if "error" in data:
            return data
        
        try:
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
            return {"error": f"Failed to parse version data: {str(e)}", "raw_data": data}


class AIAssistant:
    """Class for managing AI assistant interactions"""
    
    def __init__(self):
        """Initialize the AI assistant"""
        self.client = OpenAI()
        self.model = MODEL_NAME
        self.config = MODEL_CONFIG
        self.system_prompt = DATA_MANAGEMENT_PROMPT
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
        
    def process_query(self, user_input, chat_history=None):
        """
        Process user input, determine appropriate functions to call, and generate a response.
        
        Args:
            user_input (str): The user's query
            chat_history (list, optional): List of previous messages. Defaults to None.
        
        Returns:
            tuple: (response, updated_chat_history, function_calls)
        """
        # Initialize chat history if None
        if chat_history is None:
            chat_history = [
                {"role": "system", "content": self.system_prompt}
            ]
        
        # Add user message to history
        chat_history.append({"role": "user", "content": user_input})
        
        # Get model response with function calling enabled
        response = self.client.chat.completions.create(
            model=self.model,
            messages=chat_history,
            tools=self.tools,
            **self.config
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
        
    def process_function_response(self, chat_history, function_name, function_args, function_response):
        """
        Process the function response and get the next assistant message.
        
        Args:
            chat_history (list): Current chat history
            function_name (str): Name of the function that was called
            function_args (dict): Arguments of the function
            function_response (dict): Response from the function
            
        Returns:
            tuple: (response, updated_chat_history)
        """
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
        second_response = self.client.chat.completions.create(
            model=self.model,
            messages=chat_history,
            **self.config
        )
        
        # Add the new response to chat history
        assistant_response = second_response.choices[0].message
        chat_history.append(assistant_response)
        
        return assistant_response.content, chat_history
        
    def analyze_response_for_options(self, response):
        """
        Analyze the assistant's response to determine if it contains a list of options
        that should be presented as clickable elements.
        
        Args:
            response (str): The assistant's response
            
        Returns:
            dict: Information about options to display, or None if no options
        """
        # This is a simplistic approach - in a real app, you might want to use 
        # more sophisticated NLP or have the LLM explicitly mark options in its response
        
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


# Create instances of managers for use in the UI
hub_manager = HubManager()
project_manager = ProjectManager()
item_manager = ItemManager()
version_manager = VersionManager()
ai_assistant = AIAssistant()

# Wrapper functions to simplify UI interaction
def get_hubs():
    return hub_manager.get_hubs()

def get_projects(hub_id):
    return project_manager.get_projects(hub_id)

def filter_projects(projects, criteria):
    return project_manager.filter_projects(projects, criteria)

def get_items(project_id):
    return item_manager.get_items(project_id)

def filter_items(items, criteria):
    return item_manager.filter_items(items, criteria)

def get_versions(project_id, item_id):
    return version_manager.get_versions(project_id, item_id)

def process_user_query(user_input, chat_history=None):
    return ai_assistant.process_query(user_input, chat_history)

def process_function_result(chat_history, function_name, function_args, function_response):
    return ai_assistant.process_function_response(chat_history, function_name, function_args, function_response)

def analyze_response_for_options(response):
    return ai_assistant.analyze_response_for_options(response) 