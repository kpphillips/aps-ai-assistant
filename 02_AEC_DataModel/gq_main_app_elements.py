''' Main script for GraphQL queries for Elements
    https://aecdatamodel-explorer.autodesk.io/
'''
import os
import requests
import json
from dotenv import load_dotenv
import re

from gq_1_prompts import ELEMENTS_BASE_PROMPT
from gq_0_config import MODEL_NAME, MODEL_CONFIG

# Add the DataManagement directory to the path to access the OpenAI service
import sys

# region Load environment variables
data_mgmt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "01_DataManagment")
sys.path.append(data_mgmt_path)
from openai_service import get_openai_client

load_dotenv()
APS_AUTH_TOKEN = os.environ.get("APS_AUTH_TOKEN")

if not APS_AUTH_TOKEN:
    print("APS_AUTH_TOKEN not set in .env")
    exit(1)
# endregion

def generate_graphql_query(natural_language_query: str, project_id: str = None) -> dict:
    """
    Generate a GraphQL query for element data based on a natural language description.
    Returns the query, variables dictionary, and property filter string.
    
    Args:
        natural_language_query (str): Natural language description of the elements to query
        project_id (str, optional): Project ID to include in the query or prompt. Defaults to None.
    
    Returns:
        dict: Dictionary containing the generated query, variables dictionary, property filter, and full response
    """
    # Use the project ID in the prompt if provided
    if project_id:
        prompt = f"{ELEMENTS_BASE_PROMPT}\nNatural Language Query: {natural_language_query}\nProject ID: {project_id}"
    else:
        prompt = f"{ELEMENTS_BASE_PROMPT}\nNatural Language Query: {natural_language_query}"
    
    client = get_openai_client()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{
            "role": "user", 
            "content": prompt
        }],
        response_format={"type": "json_object"},
        **MODEL_CONFIG
    )
    
    # region Print Outputs
    print("\nDebug Response Info:")
    print(f"Response Model: {response.model}")
    print(f"Response ID: {response.id}")
    print(f"Response Created: {response.created}")
    print(f"Response Usage: {response.usage}")
    # endregion
    
    content = response.choices[0].message.content.strip()
    
    # Print full response for debugging
    print("\nFull LLM Response:")
    print(content)
    
    # Parse the JSON response
    try:
        data = json.loads(content)
        
        # Extract the query and variables
        query = data.get("query")
        variables = data.get("variables", {})
        property_filter = variables.get("propertyFilter")
        
        # If the project_id was provided, update it in the variables
        if project_id and "projectId" in variables:
            variables["projectId"] = project_id
        
        return {
            "query": query,
            "variables": variables,
            "property_filter": property_filter,
            "full_response": content
        }
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        return {
            "query": None,
            "variables": {},
            "property_filter": None,
            "full_response": content,
            "error": f"Failed to parse JSON response: {str(e)}"
        }
    except Exception as e:
        print(f"Unexpected error processing response: {e}")
        return {
            "query": None,
            "variables": {},
            "property_filter": None,
            "full_response": content,
            "error": f"Unexpected error: {str(e)}"
        }

def call_aps_api(query: str, variables: dict) -> dict:
    """Call the Autodesk AEC Data Model GraphQL API."""
    endpoint = "https://developer.api.autodesk.com/aec/graphql"
    headers = {
        "Authorization": f"Bearer {APS_AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "query": query,
        "variables": variables
    }
    
    print("\nCalling APS API with payload:")
    print(json.dumps(payload, indent=2))
    
    try:
        response = requests.post(endpoint, json=payload, headers=headers)
        
        # Log the status code
        print(f"\nAPI Response Status: {response.status_code}")
        
        # Check for authentication errors
        if response.status_code == 401:
            error_msg = "Authentication Error: Invalid or expired token"
            print(f"\n{error_msg}")
            return {"error": error_msg, "status_code": 401}
        
        # Check for other error status codes
        elif response.status_code != 200:
            error_msg = f"API Error: {response.status_code} - {response.text}"
            print(f"\n{error_msg}")
            return {"error": error_msg, "status_code": response.status_code}
        
        # Parse JSON response
        json_response = response.json()
        
        # Check for GraphQL errors
        if "errors" in json_response:
            print("\nGraphQL Errors:")
            print(json.dumps(json_response["errors"], indent=2))
        
        return json_response
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Request Error: {str(e)}"
        print(f"\n{error_msg}")
        return {"error": error_msg}
    except json.JSONDecodeError as e:
        error_msg = f"JSON Decode Error: {str(e)}"
        print(f"\n{error_msg}")
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected Error: {str(e)}"
        print(f"\n{error_msg}")
        return {"error": error_msg}

def main():
    # Get project ID from environment variables
    project_id = os.environ.get("APS_GQ_SAMPLE_PROJECT_ID")
    if not project_id:
        print("WARNING: APS_GQ_SAMPLE_PROJECT_ID not set in .env")
        project_id = "PLACEHOLDER_PROJECT_ID"
    
    # Example natural language query requesting a wall schedule
    natural_language_query = f"""Create a schedule of the Pipes and the Pipe Fittings 
    in project {project_id}.
    """
    
    result = generate_graphql_query(natural_language_query, project_id)
    
    print("\nGenerated GraphQL Query:")
    print(result["query"])
    
    print("\nGenerated Variables:")
    print(json.dumps(result["variables"], indent=2))
    
    print("\nGenerated Property Filter:")
    print(result["property_filter"])
        
    # Validate results before calling the API
    valid_query = result["query"] and "elementsByProject" in result["query"]
    valid_filter = result["property_filter"] and ("==" in result["property_filter"] or "contains" in result["property_filter"])
    
    if "error" in result:
        print("\nERROR:", result["error"])
        return
    
    if not valid_query:
        print("\nERROR: Generated query is invalid or missing")
        print("Please try a different natural language query")
        return
        
    if not valid_filter:
        print("\nERROR: Generated property filter is invalid or missing")
        print("Please try a different natural language query")
        return
    
    # Directly use the variables dictionary from the result
    variables = result["variables"]
    
    print("\nVariables:")
    print(json.dumps(variables, indent=2))
    
    # Let user confirm before making the API call
    confirm = input("\nDoes this query look correct? (y/n): ")
    if confirm.lower() == 'y':
        print("\nCalling Autodesk APS API...")
        api_response = call_aps_api(result["query"], variables)
        print("\nAPI Response:")
        print(json.dumps(api_response, indent=2))
    else:
        print("API call cancelled.")

if __name__ == "__main__":
    main()
