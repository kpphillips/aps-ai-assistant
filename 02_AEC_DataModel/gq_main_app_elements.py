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

def generate_graphql_query(natural_language_query: str) -> dict:
    """
    Generate a GraphQL query for element data based on a natural language description.
    Returns both the query and the property filter string.
    """
    client = get_openai_client()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{
            "role": "user", 
            "content": f"{ELEMENTS_BASE_PROMPT}\nNatural Language Query: {natural_language_query}\nPlease return the GraphQL query and property filter as separate sections clearly labeled."
        }],
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
    
    # Parse the response to extract both the query and the property filter
    try:
        query = None
        property_filter = None
        
        # Extract query - look for GraphQL or code blocks
        if "```graphql" in content:
            query_parts = content.split("```graphql")
            if len(query_parts) > 1:
                query_content = query_parts[1].split("```")[0].strip()
                query = query_content
        elif "```" in content:
            # Find all code blocks
            code_blocks = []
            parts = content.split("```")
            for i in range(1, len(parts), 2):
                if i < len(parts):
                    code_blocks.append(parts[i].strip())
            
            # The first code block is likely the query if it contains "elementsByProject"
            for block in code_blocks:
                if "elementsByProject" in block:
                    query = block
                    break
        
        # For property filter, look specifically for sections labeled as such
        property_filter_indicators = [
            "Property Filter:", 
            "propertyFilter:", 
            "Filter String:", 
            "Property Filter String:",
            "### Property Filter:"
        ]
        
        for indicator in property_filter_indicators:
            if indicator in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if indicator in line:
                        # Check if the filter is on this line
                        if ":" in line:
                            # Get everything after the colon
                            filter_value = line.split(":", 1)[1].strip()
                            # Only strip outer double quotes, commas, or other syntax, but preserve single quotes around properties
                            filter_value = filter_value.strip('"').strip(",").strip()
                            if "==" in filter_value or "contains" in filter_value:
                                property_filter = filter_value
                                break
                        
                        # If not on this line, check the next lines
                        # Look at up to 3 lines after the indicator in case there's markdown or code blocks
                        for j in range(1, 4):
                            if i + j < len(lines) and len(lines[i+j].strip()) > 0:
                                filter_value = lines[i+j].strip()
                                # Check if this is a code block starter
                                if filter_value.startswith("```"):
                                    # If it's a code block, look for the next non-empty line
                                    if i + j + 1 < len(lines) and len(lines[i+j+1].strip()) > 0:
                                        filter_value = lines[i+j+1].strip()
                                
                                # Clean up markdown and code blocks but preserve single quotes
                                filter_value = filter_value.strip('"').strip(",").strip()
                                filter_value = filter_value.replace("```plaintext", "").replace("```", "")
                                
                                if "==" in filter_value or "contains" in filter_value:
                                    property_filter = filter_value
                                    break
                        
                        if property_filter:
                            break

        # If still no property filter, try to extract from plain text by looking for pattern
        if property_filter is None:
            # Look for quoted property name patterns - match complete filter expressions with and/or
            pattern = r"'property\.name\.[^']+'.*?==.*?(?:and|or|$)"
            matches = re.findall(pattern, content)
            if matches:
                # Join any matches that look like they should be together
                full_filter = " ".join(matches)
                if "==" in full_filter:
                    property_filter = full_filter
            else:
                # Try looking for individual property expressions
                pattern = r"'property\.name\.[^']+'.+?==.+?'"
                matches = re.findall(pattern, content)
                if matches:
                    for match in matches:
                        if "==" in match:
                            property_filter = match
                            break
        
        # Validate property filter before returning
        if property_filter:
            # Check for invalid content
            if "String" in property_filter or "{" in property_filter:
                # This doesn't look like a valid filter string
                print("WARNING: Extracted property filter appears invalid: " + property_filter)
                property_filter = None
            
            # Check for proper quote format
            elif "'property.name." not in property_filter:
                print("WARNING: Property filter missing proper quotes: " + property_filter)
                # Try to fix missing quotes
                property_filter = property_filter.replace("property.name.", "'property.name.").replace(" == ", "'=='").replace(" and ", "' and ")
                if not property_filter.endswith("'"):
                    property_filter += "'"
                print("FIXED TO: " + property_filter)
        
        return {
            "query": query,
            "property_filter": property_filter,
            "full_response": content
        }
    except Exception as e:
        print(f"Error parsing response: {e}")
        return {
            "query": None,
            "property_filter": None,
            "full_response": content
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
    
    response = requests.post(endpoint, json=payload, headers=headers)
    return response.json()

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
    
    result = generate_graphql_query(natural_language_query)
    
    print("\nGenerated GraphQL Query:")
    print(result["query"])
    
    print("\nGenerated Property Filter:")
    print(result["property_filter"])
        
    # Validate results before calling the API
    valid_query = result["query"] and "elementsByProject" in result["query"]
    valid_filter = result["property_filter"] and ("==" in result["property_filter"] or "contains" in result["property_filter"])
    
    if not valid_query:
        print("\nERROR: Generated query is invalid or missing")
        print("Please try a different natural language query")
        return
        
    if not valid_filter:
        print("\nERROR: Generated property filter is invalid or missing")
        print("Please try a different natural language query")
        return
    
    # If we have both a valid query and property filter, call the API
    variables = {
        "projectId": project_id,
        "propertyFilter": result["property_filter"]
    }
    
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
