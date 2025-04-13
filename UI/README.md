# Autodesk Platform Services Assistant UI

This is a Streamlit-based chat UI for interacting with Autodesk Platform Services APIs.

## Features

- Chat interface for querying Autodesk resources
- Dynamic clickable options for selecting hubs, projects, items, and versions
- Filtering capabilities for long lists of projects and items
- Maintains conversation context across interactions

## Requirements

- Python 3.9 or higher
- Streamlit 1.20.0 or higher
- OpenAI API key
- Autodesk Platform Services authentication token

## Setup

1. Install the required packages:

```bash
pip install -r requirements.txt
```

2. Ensure your `.env` file is set up correctly in the parent directory with the following variables:

```
OPENAI_API_KEY=your_openai_api_key
APS_AUTH_TOKEN=your_aps_auth_token
```

## Running the UI

From the UI directory, run:

```bash
streamlit run app.py
```

Or from the root directory:

```bash
streamlit run UI/app.py
```

The UI will be available at http://localhost:8501 by default.

## Usage

1. Type natural language queries in the chat input
2. The assistant will analyze your query and call the appropriate APIs
3. If selection is required (e.g., choosing a hub), clickable options will appear
4. Continue the conversation naturally with follow-up questions or selections

## Example Queries

- "Show me my available hubs"
- "List all projects in hub XYZ"
- "What items are in project ABC?"
- "Show me versions of file DEF" 