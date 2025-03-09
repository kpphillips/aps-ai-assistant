# Data Management and Model Derivative APIs
import os
import requests

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
    """Retrieve the list of hubs from APS."""
    url = "https://developer.api.autodesk.com/hubs"
    response = requests.get(url, headers=_HEADERS)
    print(f"GET Hubs Response: {response.status_code}\n{response.text}")
    return response.json()

def get_projects(hub_id: str):
    """Retrieve the list of projects for a given hub."""
    url = f"https://developer.api.autodesk.com/hubs/{hub_id}/projects"
    response = requests.get(url, headers=_HEADERS)
    print(f"GET Projects Response for hub {hub_id}: {response.status_code}\n{response.text}")
    return response.json()

def get_items(project_id: str):
    """Retrieve the list of items for a given project."""
    url = f"https://developer.api.autodesk.com/projects/{project_id}/items"
    response = requests.get(url, headers=_HEADERS)
    print(f"GET Items Response for project {project_id}: {response.status_code}\n{response.text}")
    return response.json()

def get_versions(project_id: str, item_id: str):
    """Retrieve the versions for a given item in a project."""
    url = f"https://developer.api.autodesk.com/projects/{project_id}/items/{item_id}/versions"
    response = requests.get(url, headers=_HEADERS)
    print(f"GET Versions Response for project {project_id}, item {item_id}: {response.status_code}\n{response.text}")
    return response.json()


# Model Derivative APIs (Stubs, to be implemented later)

def get_Model_Views(urn: str):
    # To be implemented in the future
    return

def get_view_objects(urn: str, model_view_id: str):
    # To be implemented in the future
    return

def get_view_object_properties(urn: str, model_view_id: str):
    # To be implemented in the future
    return
