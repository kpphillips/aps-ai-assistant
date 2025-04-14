import streamlit as st
import sys
import os
import json
import pandas as pd
from datetime import datetime

# Add the AEC Data Model directory to the path
aec_data_model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "02_AEC_DataModel")
sys.path.append(aec_data_model_path)

# Add the DataManagement directory to the path for accessing the OpenAI service
data_mgmt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "01_DataManagment")
sys.path.append(data_mgmt_path)

# Import the AEC Data Model functions
from gq_main_app_elements import generate_graphql_query, call_aps_api

# Set up page configuration
st.set_page_config(
    page_title="AEC Data Model Schedule Generator",
    page_icon="🏗️",
    layout="wide"
)

def execute_aec_query(query, variables):
    """Execute an AEC Data Model GraphQL query with the given variables."""
    try:
        api_response = call_aps_api(query, variables)
        
        # Enhanced logging of response for debugging
        print("\nAPI Response Summary:")
        if "error" in api_response:
            print(f"Error: {api_response['error']}")
        elif "errors" in api_response:
            print(f"GraphQL Errors: {json.dumps(api_response['errors'], indent=2)}")
        else:
            elements = api_response.get('data', {}).get('elementsByProject', {}).get('results', [])
            element_count = len(elements)
            print(f"Success: {element_count} elements returned")
            
            # Debug the structure of the first element if available
            if element_count > 0:
                first_element = elements[0]
                print("\nFirst Element Structure:")
                print(f"Element Name: {first_element.get('name')}")
                
                properties = first_element.get('properties', {}).get('results', [])
                print(f"Properties Count: {len(properties)}")
                
                # Print a few properties as examples
                if properties:
                    print("\nSample Properties Structure:")
                    for i, prop in enumerate(properties[:3]):  # Show first 3 properties
                        print(f"Property {i+1}: {json.dumps(prop, indent=2)}")
                        
        return api_response
    except Exception as e:
        print(f"\nException in execute_aec_query: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": f"Error executing query: {str(e)}"}

def process_elements_into_dataframe(elements):
    """
    Process the list of elements from the API response into a structured DataFrame.
    
    Args:
        elements (list): List of elements from the API response
        
    Returns:
        pandas.DataFrame: DataFrame containing the processed element data
    """
    if not elements:
        return None
    
    # Extract all unique property names
    all_prop_keys = set()
    for element in elements:
        for prop in element.get('properties', {}).get('results', []):
            prop_name = prop.get('name')
            if prop_name:
                all_prop_keys.add(prop_name)
    
    # Create sorted list of property keys for consistent column order
    sorted_prop_keys = sorted(list(all_prop_keys))
    
    # Process each element
    processed_data = []
    for element in elements:
        row = {
            'Element Name': element.get('name', 'N/A')
        }
        
        # Create a dictionary of properties for this element
        element_props = {}
        for prop in element.get('properties', {}).get('results', []):
            prop_name = prop.get('name')
            if prop_name:
                # Fix: More robust nested property access
                definition = prop.get('definition')
                if definition is not None and isinstance(definition, dict):
                    units = definition.get('units')
                    if units is not None and isinstance(units, dict):
                        unit_name = units.get('name')
                        if unit_name:
                            # Use displayValue if available, otherwise use value
                            if prop.get('displayValue'):
                                element_props[prop_name] = f"{prop.get('displayValue')} {unit_name}"
                            else:
                                element_props[prop_name] = f"{prop.get('value', '')} {unit_name}"
                            continue
                
                # No units or invalid structure, just use the value
                element_props[prop_name] = prop.get('displayValue', prop.get('value', ''))
        
        # Add the properties to the row
        for key in sorted_prop_keys:
            row[key] = element_props.get(key, '')
        
        processed_data.append(row)
    
    return pd.DataFrame(processed_data)

def format_graphql_query(query_string):
    """
    Format a GraphQL query string with proper indentation for readability.
    
    Args:
        query_string (str): Raw GraphQL query string
        
    Returns:
        str: Formatted GraphQL query with proper indentation
    """
    # Remove any existing newlines and extra spaces
    query = query_string.strip()
    
    # Don't try to format if it's not a valid query
    if not query or "{" not in query:
        return query
        
    formatted = ""
    indent_level = 0
    in_string = False
    string_char = None
    
    for char in query:
        # Handle string literals (don't format inside them)
        if char in ['"', "'"]:
            if not in_string:
                in_string = True
                string_char = char
            elif string_char == char:  # Make sure we're closing the same string
                in_string = False
                string_char = None
                
        # Skip formatting if we're inside a string
        if in_string:
            formatted += char
            continue
            
        # Handle formatting
        if char == '{':
            indent_level += 1
            formatted += char
            formatted += '\n' + '  ' * indent_level
        elif char == '}':
            indent_level -= 1
            formatted += '\n' + '  ' * indent_level
            formatted += char
        elif char == '(':
            formatted += char
        elif char == ')':
            formatted += char
        elif char == ',':
            formatted += char
            if not (formatted[-2:] == '})' or formatted[-2:] == '})'):
                formatted += '\n' + '  ' * indent_level
        else:
            formatted += char
            
    return formatted

def main():
    # Set up the sidebar
    st.sidebar.title("Smart Schedule")
    
    st.sidebar.markdown("""
    This tool generates schedules from Autodesk AEC Data Model using natural language descriptions.
    Simply describe the elements you want to include in your schedule, and the app will generate 
    the appropriate query and display the results.
    """)
    
    # Project ID input in sidebar
    project_id = st.sidebar.text_input(
        "Project ID", 
        value=os.environ.get("APS_GQ_SAMPLE_PROJECT_ID", ""),
        help="The ID of the project to query elements from"
    )
    
    # Main area title
    st.title("AEC Data Model Schedule Generator")
    
    # Natural language input in main area
    user_nl_input = st.text_area(
        "Describe the elements for your schedule",
        placeholder="Examples: 'all doors with 2-hour fire rating', 'pipe fittings in assembly A-01', 'BIMrx_Points on level 2'",
        height=100
    )
    
    if st.button("Generate and Run Query"):
        if not project_id:
            st.error("Please enter a Project ID in the sidebar.")
        elif not user_nl_input:
            st.warning("Please enter a description for the query.")
        else:
            with st.spinner("Generating query..."):
                # Generate the GraphQL query and property filter
                result = generate_graphql_query(user_nl_input, project_id)
                
                # Check for errors in the result
                if "error" in result:
                    st.error(f"Error generating query: {result['error']}")
                    st.markdown("### LLM Response")
                    st.markdown(result["full_response"])
                    return
                
                if not result["property_filter"]:
                    st.error("Failed to generate a property filter. Please try a different description.")
                    st.markdown("### Generated Response")
                    st.markdown(result["full_response"])
                    return
                
                # Display the property filter in sidebar
                with st.sidebar.expander("Generated Property Filter", expanded=True):
                    if result["property_filter"]:
                        # Show the filter string in a code block - for display only
                        st.code(result["property_filter"], language="plaintext")
                        
                        # Show a visual representation of what it will do
                        filter_explanation = result["property_filter"].replace("'property.name.", "").replace("'==", " equals ").replace("' and ", " AND ")
                        st.caption(f"This will filter for: {filter_explanation}")
                    else:
                        st.warning("No property filter was generated.")
                
                # Display example of the actual JSON payload in sidebar
                with st.sidebar.expander("View API Payload"):
                    st.code(json.dumps(result["variables"], indent=2), language="json")
                
                # Display the GraphQL query in sidebar
                with st.sidebar.expander("View GraphQL Query"):
                    if result["query"]:
                        # Format the GraphQL query for better readability
                        formatted_query = format_graphql_query(result["query"])
                        st.code(formatted_query, language="graphql")
                    else:
                        st.warning("No query generated.")
                
                # Execute the query
                with st.spinner("Executing query..."):
                    api_response = execute_aec_query(result["query"], result["variables"])
                
                # Check for errors
                if "error" in api_response:
                    error_message = api_response["error"]
                    
                    # Add special handling for common errors
                    if "Authentication Error" in error_message:
                        st.error("⚠️ Authentication Failed: Your APS token is invalid or has expired. Please update your token.")
                        st.info("💡 Tip: Check your .env file and ensure APS_AUTH_TOKEN is set with a valid token.")
                    elif "status_code" in api_response and api_response["status_code"] == 401:
                        st.error("⚠️ Authentication Failed: Your APS token is invalid or has expired. Please update your token.")
                        st.info("💡 Tip: Check your .env file and ensure APS_AUTH_TOKEN is set with a valid token.")
                    else:
                        st.error(f"API Error: {error_message}")
                    
                    # Show technical details in an expander
                    with st.expander("Technical Details"):
                        st.code(json.dumps(api_response, indent=2), language="json")
                    return
                
                if "errors" in api_response:
                    st.error("GraphQL Error")
                    # Format the errors for better display
                    graphql_errors = api_response.get("errors", [])
                    for i, error in enumerate(graphql_errors):
                        st.warning(f"Error {i+1}: {error.get('message', 'Unknown error')}")
                    
                    # Show full details in an expander
                    with st.expander("Full Error Details"):
                        st.code(json.dumps(api_response["errors"], indent=2), language="json")
                    return
                
                # Extract the elements from the response
                elements = api_response.get('data', {}).get('elementsByProject', {}).get('results', [])
                
                if not elements:
                    st.info("Query executed successfully, but no elements matched your criteria.")
                    return
                
                # Process the elements into a DataFrame
                st.subheader(f"Schedule Results ({len(elements)} elements)")
                
                try:
                    df = process_elements_into_dataframe(elements)
                    
                    if df is not None:
                        # Display the interactive table (not in an expander)
                        st.dataframe(df)
                        
                        # Add download button for CSV
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download Schedule as CSV",
                            data=csv,
                            file_name=f'aec_schedule_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                            mime='text/csv',
                        )
                    else:
                        st.warning("Failed to process elements into a table format.")
                
                except Exception as e:
                    st.error(f"Error processing data: {str(e)}")
                    import traceback
                    error_details = traceback.format_exc()
                    
                    with st.expander("Technical Error Details"):
                        st.code(error_details)
                        
                    # Display raw data as fallback
                    with st.expander("View Raw Element Data"):
                        st.json(elements[:5])  # Show first 5 elements to avoid overwhelming the UI

if __name__ == "__main__":
    main() 