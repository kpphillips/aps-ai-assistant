''' Test script for Data Management API functions '''
import os
from dotenv import load_dotenv
from dm_3_helpers import get_hubs, get_projects, get_items, get_versions

def main():
    """Main function to test Data Management API functions"""
    # Load environment variables to get the APS_AUTH_TOKEN
    load_dotenv()
    
    # Ensure the auth token is available
    if not os.environ.get("APS_AUTH_TOKEN"):
        print("Error: APS_AUTH_TOKEN environment variable is not set.")
        print("Please set this variable in your .env file or environment.")
        return
    
    print("\n========== TESTING DATA MANAGEMENT API FUNCTIONS ==========\n")
    
    # Test 1: Get Hubs
    print("TEST 1: Retrieving Hubs")
    print("-----------------------")
    
    hubs_result = get_hubs()
    if "error" in hubs_result:
        print(f"Error: {hubs_result['error']}")
    else:
        print(f"Found {hubs_result.get('count', 0)} hubs:")
        for i, hub in enumerate(hubs_result.get('hubs', []), 1):
            print(f"{i}. {hub.get('name')} (ID: {hub.get('id')})")
    
    # After getting hubs, ask user if they want to continue with a specific hub
    if hubs_result.get('count', 0) > 0:
        print("\nDo you want to test retrieving projects for a specific hub?")
        response = input("Enter a hub number from the list above, or 'n' to skip: ")
        
        if response.lower() != 'n' and response.isdigit():
            hub_index = int(response) - 1
            if 0 <= hub_index < len(hubs_result.get('hubs', [])):
                selected_hub = hubs_result['hubs'][hub_index]
                hub_id = selected_hub['id']
                
                # Test 2: Get Projects for the selected hub
                print("\nTEST 2: Retrieving Projects")
                print("--------------------------")
                print(f"Using Hub: {selected_hub['name']} (ID: {hub_id})")
                
                projects_result = get_projects(hub_id)
                if "error" in projects_result:
                    print(f"Error: {projects_result['error']}")
                else:
                    print(f"Found {projects_result.get('count', 0)} projects:")
                    for i, project in enumerate(projects_result.get('projects', []), 1):
                        print(f"{i}. {project.get('name')} (ID: {project.get('id')})")
                
                # After getting projects, ask user if they want to continue with a specific project
                if projects_result.get('count', 0) > 0:
                    print("\nDo you want to test retrieving items for a specific project?")
                    response = input("Enter a project number from the list above, or 'n' to skip: ")
                    
                    if response.lower() != 'n' and response.isdigit():
                        project_index = int(response) - 1
                        if 0 <= project_index < len(projects_result.get('projects', [])):
                            selected_project = projects_result['projects'][project_index]
                            project_id = selected_project['id']
                            
                            # Test 3: Get Items for the selected project
                            print("\nTEST 3: Retrieving Items")
                            print("----------------------")
                            print(f"Using Project: {selected_project['name']} (ID: {project_id})")
                            
                            items_result = get_items(project_id)
                            if "error" in items_result:
                                print(f"Error: {items_result['error']}")
                            else:
                                print(f"Found {items_result.get('count', 0)} items:")
                                for i, item in enumerate(items_result.get('items', []), 1):
                                    print(f"{i}. {item.get('name')} (Type: {item.get('file_type')})")
                                    print(f"   Last Modified: {item.get('last_modified', 'Unknown')}")
                                    print(f"   ID: {item.get('id')}")
                            
                            # After getting items, ask user if they want to continue with a specific item
                            if items_result.get('count', 0) > 0:
                                print("\nDo you want to test retrieving versions for a specific item?")
                                response = input("Enter an item number from the list above, or 'n' to skip: ")
                                
                                if response.lower() != 'n' and response.isdigit():
                                    item_index = int(response) - 1
                                    if 0 <= item_index < len(items_result.get('items', [])):
                                        selected_item = items_result['items'][item_index]
                                        item_id = selected_item['id']
                                        
                                        # Test 4: Get Versions for the selected item
                                        print("\nTEST 4: Retrieving Versions")
                                        print("--------------------------")
                                        print(f"Using Item: {selected_item['name']} (ID: {item_id})")
                                        
                                        versions_result = get_versions(project_id, item_id)
                                        if "error" in versions_result:
                                            print(f"Error: {versions_result['error']}")
                                        else:
                                            print(f"Found {versions_result.get('count', 0)} versions:")
                                            for i, version in enumerate(versions_result.get('versions', []), 1):
                                                print(f"{i}. Version {version.get('version_number')} - {version.get('name')}")
                                                print(f"   Created by: {version.get('created_by')} on {version.get('created_date', 'Unknown')}")
                                                print(f"   Type: {version.get('file_type')}, Size: {version.get('storage_size', 'Unknown')}")
                                                print(f"   ID: {version.get('id')}")

    print("\nTests completed.")

if __name__ == "__main__":
    main() 