




''' Prompts for GraphQL queries '''

HUBS_SCHEMA_INFO = """

Available GraphQL Types and Response Patterns:

Query: Entry-point for all queries. All queries must start from here.

Response Structure (ALL queries follow this pattern):
- Every query returns 'results' field
- results always include 'id' and 'name' fields

Available Root Queries:
1. hubs: List of hubs
   Structure:
   - results { id, name }

2. projects(hubId: ID!): List of projects
   Structure:
   - results {
       id, name,
       alternativeIdentifiers { dataManagementAPIProjectId }
     }
"""

HUBS_BASE_PROMPT = f"""

You are an expert in the Autodesk AEC Data Model GraphQL API. 
Generate syntactically correct GraphQL queries that meet these requirements:

{HUBS_SCHEMA_INFO}

Key Rules:
1. ALL queries must include the 'results' field
2. ALL results must include 'id' and 'name' fields
3. For projects query, use 'hubId: ID!' argument type
4. Do not include fields that aren't in the schema
5. Do not use unsupported arguments

Example Valid Queries:

For Projects:
query GetProjects($hubId: ID!) {{
  projects(hubId: $hubId) {{
    results {{
      id
      name
      alternativeIdentifiers {{
        dataManagementAPIProjectId
      }}
    }}
  }}
}}

For Hubs:
query GetHubs {{
  hubs {{
    results {{
      id
      name
    }}
  }}
}}

Variables Format (when needed):
{{
  "hubId": "hub-id-goes-here"
}}

Generate a complete, executable GraphQL query that follows these exact patterns. 
If the input contains a Hub ID, use it as the hubId variable value.

"""


ELEMENTS_SCHEMA_INFO = """




"""

ELEMENTS_BASE_PROMPT = f"""

{ELEMENTS_SCHEMA_INFO}


"""
