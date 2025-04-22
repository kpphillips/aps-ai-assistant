# Autodesk Platform Services Assistant

This project demonstrates various approaches to using AI/LLMs for interacting with Autodesk Platform Services (APS) APIs.

## Features

- Chat interface for querying Autodesk resources
- Function calling to interact with APS APIs
- Schedule creation for model objects
- GraphQL query generation for AEC Data Model
- Detailed logging of OpenAI API calls

## Setup

1. Install the required packages:

```bash
pip install -r requirements.txt
```

2. Ensure your `.env` file is set up correctly by copying the .env.example file and saving it as .env:

## Running the UI

From the root directory, run:

```bash
streamlit run UI/app.py
```

The UI will be available at http://localhost:8501 by default.

## OpenAI API Logging

The project includes a logging system for OpenAI API calls to help debug context length issues and analyze API usage.

### Log Files

- `logs/openai_api.log`: Contains basic log messages
- `logs/openai_api_detailed.jsonl`: Contains detailed JSON logs of each API call

### Log Contents

Each log entry includes:
- Timestamp
- Model name
- Token counts (messages, tools, total)
- Message summaries (with truncated content for system and user messages)
- Tool summaries (if applicable)
- Response usage information

### Controlling Logging

You can control logging behavior using the `OPENAI_LOG_API_REQUESTS` environment variable:
- Set to `true` to enable logging (default)
- Set to `false` to disable logging

### Testing Logging

You can test the logging functionality by running:

```bash
python 01_DataManagment/test_openai_logging.py
```

## Project Structure

- `UI/`: Contains the Streamlit UI code
- `01_DataManagment/`: Contains the Data Management API code
- `02_AEC_DataModel/`: Contains the AEC Data Model GraphQL code
- `logs/`: Contains the OpenAI API logs

## Modules

- `openai_logger.py`: Provides logging functionality for OpenAI API calls
- `openai_service.py`: Provides a wrapper around the OpenAI client with logging
- `dm_3_helpers.py`: Contains helper functions for the Data Management API
- `schedule_creator.py`: Contains functions for creating schedules from model data 

## Disclaimer

This project is an independent demonstration of Autodesk Platform Services (APS) APIs and is not officially endorsed, sponsored, or affiliated with Autodesk, Inc. It is provided "as is" without warranty of any kind, express or implied.

Users are responsible for:
- Obtaining their own valid APS credentials
- Complying with Autodesk's terms of service
- Ensuring proper data security and privacy practices
- Using this code in accordance with applicable laws and regulations

The authors and contributors assume no liability for any damages or losses arising from the use of this software.