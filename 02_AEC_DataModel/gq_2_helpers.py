

def call_aps_api(graphql_query: str, variables: dict = None) -> dict:
    endpoint = "https://developer.api.autodesk.com/aec/graphql"
    headers = {
        "Authorization": f"Bearer {APS_AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "query": graphql_query,
        "variables": variables or {}
    }
    response = requests.post(endpoint, json=payload, headers=headers)
    return response.json()