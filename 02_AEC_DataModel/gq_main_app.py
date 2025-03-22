



''' Main script for GraphQL queries '''
import os
import requests
from dotenv import load_dotenv

from gq_1_prompts import HUBS_BASE_PROMPT
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

def generate_graphql_query(natural_language_query: str) -> str:
    client = get_openai_client()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{
            "role": "user", 
            "content": f"{HUBS_BASE_PROMPT}\nNatural Language Query: {natural_language_query}\nGraphQL Query:"
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
    return response.choices[0].message.content.strip()

def main():
    natural_language_query = '''find me the projects in this hub: 
    urn:adsk.ace:prod.scope:ca33a0c0-9108-4ed9-a15f-3f86de705f15'''
    graphql_query = generate_graphql_query(natural_language_query)
    
    print(f"\nGenerated GraphQL Query:\n{graphql_query}")

if __name__ == "__main__":
    main()
