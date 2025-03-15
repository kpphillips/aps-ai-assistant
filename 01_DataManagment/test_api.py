#!/usr/bin/env python
"""
Test script for Autodesk API Helper functions.
This allows testing individual API functions without running the full Streamlit app.
"""

# Command line arguments:
# --function: "hubs", "projects", "filter", "items", "versions", "views", "properties", "all"
# --hub-id: "b.17303213-7d00-46b0-8773-a11ba49dd3ce"
# --project-id: "b.0a202083-0cef-44d6-8c4c-d561853cc403"
# --item-id: "b.0a202083-0cef-44d6-8c4c-d561853cc403"
# --version-urn: "urn:adsk.wipprod:fs.file:vf.-3ver-faSemSdPmFvD5ZFQ?version=3"
# --view-guid: "6fefaf79-aaf2-15d2-1b5d-dadb137c1549"
# --prefix: "KP_ADSK"

# Example:
# python test_api.py --function projects --hub-id b.17303213-7d00-46b0-8773-a11ba49dd3ce
# python test_api.py --function items --hub-id b.17303213-7d00-46b0-8773-a11ba49dd3ce --project-id b.0a202083-0cef-44d6-8c4c-d561853cc403
# python test_api.py --function views --version-urn urn:adsk.wipprod:fs.file:vf.-3ver-faSemSdPmFvD5ZFQ?version=3
# python test_api.py --function properties --version-urn urn:adsk.wipprod:fs.file:vf.-3ver-faSemSdPmFvD5ZFQ?version=3 --view-guid 6fefaf79-aaf2-15d2-1b5d-dadb137c1549

import os
import json
import sys
from dm_3_helpers import AutodeskAPIHelper, dump_memory_state, add_interaction
import base64

def print_json(data):
    """Print JSON data in a readable format"""
    print(json.dumps(data, indent=2))

def test_get_hubs():
    """Test the get_hubs function"""
    print("\n=== Testing get_hubs ===")
    api_helper = AutodeskAPIHelper()
    result = api_helper.get_hubs()
    print_json(result)
    return result

def test_get_projects(hub_id):
    """Test the get_projects function for a specific hub"""
    print(f"\n=== Testing get_projects for hub {hub_id} ===")
    api_helper = AutodeskAPIHelper()
    
    # Add to memory
    add_interaction("List projects", "Getting projects", "get_projects", {"hub_id": hub_id})
    
    result = api_helper.get_projects(hub_id)
    
    # Update memory with result
    add_interaction("List projects", "Getting projects", "get_projects", {"hub_id": hub_id}, result)
    
    print_json(result)
    return result

def test_filter_projects(hub_id, prefix):
    """Test the filter_projects function for a specific hub and prefix"""
    print(f"\n=== Testing filter_projects for hub {hub_id} with prefix '{prefix}' ===")
    api_helper = AutodeskAPIHelper()
    
    # Add to memory
    add_interaction(f"List projects with prefix {prefix}", "Filtering projects", 
                   "filter_projects", {"hub_id": hub_id, "prefix": prefix})
    
    result = api_helper.filter_projects(hub_id, prefix)
    
    # Update memory with result
    add_interaction(f"List projects with prefix {prefix}", "Filtering projects", 
                   "filter_projects", {"hub_id": hub_id, "prefix": prefix}, result)
    
    print_json(result)
    return result

def test_get_items(hub_id, project_id):
    """Test the get_items function for a specific project"""
    print(f"\n=== Testing get_items for project {project_id} ===")
    api_helper = AutodeskAPIHelper()
    
    # First, make sure we have the project in the cache and memory
    add_interaction("List projects", "Getting projects", "get_projects", {"hub_id": hub_id})
    projects_result = api_helper.get_projects(hub_id)
    add_interaction("List projects", "Getting projects", "get_projects", {"hub_id": hub_id}, projects_result)
    
    # Dump memory state before get_items
    print("\nMemory state before get_items:")
    dump_memory_state()
    
    # Add to memory
    add_interaction(f"List items in project {project_id}", "Getting items", 
                   "get_items", {"project_id": project_id})
    
    # Now get the items
    result = api_helper.get_items(project_id)
    
    # Update memory with result
    add_interaction(f"List items in project {project_id}", "Getting items", 
                   "get_items", {"project_id": project_id}, result)
    
    # Dump memory state after get_items
    print("\nMemory state after get_items:")
    dump_memory_state()
    
    print_json(result)
    return result

def test_get_versions(project_id, item_id):
    """Test the get_versions function for a specific item"""
    print(f"\n=== Testing get_versions for item {item_id} in project {project_id} ===")
    api_helper = AutodeskAPIHelper()
    
    # Add to memory
    add_interaction(f"Get versions for item {item_id}", "Getting versions", 
                   "get_versions", {"project_id": project_id, "item_id": item_id})
    
    result = api_helper.get_versions(project_id, item_id)
    
    # Update memory with result
    add_interaction(f"Get versions for item {item_id}", "Getting versions", 
                   "get_versions", {"project_id": project_id, "item_id": item_id}, result)
    
    print_json(result)
    return result

def test_get_model_views(version_urn):
    """Test the get_model_views function for a specific version"""
    print(f"\n=== Testing get_model_views for version {version_urn} ===")
    api_helper = AutodeskAPIHelper()
    
    # Dump memory state before get_model_views
    print("\nMemory state before get_model_views:")
    dump_memory_state()
    
    # Add to memory
    add_interaction(f"Get views for version {version_urn}", "Getting model views", 
                   "get_model_views", {"version_urn": version_urn})
    
    result = api_helper.get_model_views(version_urn)
    
    # Update memory with result
    add_interaction(f"Get views for version {version_urn}", "Getting model views", 
                   "get_model_views", {"version_urn": version_urn}, result)
    
    # Dump memory state after get_model_views
    print("\nMemory state after get_model_views:")
    dump_memory_state()
    
    print_json(result)
    return result

def test_get_view_properties(version_urn, view_guid):
    """Test the get_view_properties function for a specific view"""
    print(f"\n=== Testing get_view_properties for view {view_guid} in version {version_urn} ===")
    api_helper = AutodeskAPIHelper()
    
    # First, check if we need to get the views or if they're already in the cache
    views_result = None
    
    # Check if the encoded URN is already in the cache
    try:
        # Encode the full URN including query parameters
        encoded_urn = base64.urlsafe_b64encode(version_urn.encode()).decode().rstrip('=')
        print(f"[TEST] Checking cache for encoded URN: {encoded_urn}")
        print(f"[TEST] Original URN: {version_urn}")
        
        if encoded_urn in api_helper.cache["views"]:
            print(f"[TEST] Using cached views for encoded URN: {encoded_urn}")
            views_result = api_helper.cache["views"][encoded_urn]
        else:
            print(f"[TEST] Views not found in cache, getting views for version: {version_urn}")
            # Add to memory
            add_interaction(f"Get views for version {version_urn}", "Getting model views", 
                           "get_model_views", {"version_urn": version_urn})
            
            # Get the views
            views_result = api_helper.get_model_views(version_urn)
            
            # Update memory with result
            add_interaction(f"Get views for version {version_urn}", "Getting model views", 
                           "get_model_views", {"version_urn": version_urn}, views_result)
    except Exception as e:
        print(f"[TEST] Error checking cache: {str(e)}")
        views_result = api_helper.get_model_views(version_urn)
    
    # If there was an error or no views, return as is
    if not views_result or "error" in views_result:
        print(f"[TEST] Error getting views: {views_result.get('error', 'Unknown error')}")
        return views_result
    
    # If no view_guid is provided, use the master view
    if not view_guid and views_result.get('master_view'):
        view_guid = views_result['master_view'].get('guid')
        print(f"[TEST] Using master view GUID: {view_guid}")
    
    if not view_guid:
        print("[TEST] Error: No view GUID provided and no master view found")
        return {"error": "No view GUID provided and no master view found"}
    
    # Dump memory state before get_view_properties
    print("\nMemory state before get_view_properties:")
    dump_memory_state()
    
    # Add to memory
    add_interaction(f"Get properties for view {view_guid}", "Getting view properties", 
                   "get_view_properties", {"version_urn": version_urn, "view_guid": view_guid})
    
    result = api_helper.get_view_properties(version_urn, view_guid)
    
    # Update memory with result
    add_interaction(f"Get properties for view {view_guid}", "Getting view properties", 
                   "get_view_properties", {"version_urn": version_urn, "view_guid": view_guid}, result)
    
    # Dump memory state after get_view_properties
    print("\nMemory state after get_view_properties:")
    dump_memory_state()
    
    # For properties, we'll just print a summary rather than the full JSON
    if "error" not in result:
        print(f"\n[TEST] Successfully retrieved properties for view {view_guid}")
        print(f"[TEST] Found {result.get('collection_count', 0)} collections with {result.get('object_count', 0)} total objects")
        
        # Print the first few collection names
        collections = result.get('properties', {}).get('collection', [])
        if collections:
            print("\n[TEST] Collections:")
            for i, collection in enumerate(collections[:5]):  # Show first 5 collections
                print(f"  {i+1}. {collection.get('name', 'Unknown')} ({len(collection.get('objects', []))} objects)")
            
            if len(collections) > 5:
                print(f"  ... and {len(collections) - 5} more collections")
    else:
        print_json(result)
    
    return result

def test_get_view_objects(version_urn, view_guid=None):
    """Test the get_view_objects function."""
    print(f"\n=== Testing get_view_objects for version {version_urn} ===")
    api_helper = AutodeskAPIHelper()
    
    # First, get the views for this version to ensure we have a valid view GUID
    encoded_urn = base64.urlsafe_b64encode(version_urn.encode()).decode().rstrip('=')
    print(f"[TEST] Checking cache for encoded URN: {encoded_urn}")
    print(f"[TEST] Original URN: {version_urn}")
    
    # Check if views are already in cache
    if "views" in api_helper.cache and encoded_urn in api_helper.cache["views"]:
        print(f"[TEST] Views found in cache for version: {version_urn}")
        views = api_helper.cache["views"][encoded_urn]
    else:
        print(f"[TEST] Views not found in cache, getting views for version: {version_urn}")
        views = api_helper.get_model_views(version_urn)
        if "error" in views:
            print(f"[TEST] Error getting views: {views['error']}")
            return
    
    # If no view GUID is provided, use the master view
    if view_guid is None:
        master_view = views.get("master_view", {})
        if not master_view:
            print("[TEST] No master view found and no view GUID provided")
            return
        view_guid = master_view.get("guid")
        print(f"[TEST] Using master view: {master_view.get('name')} (GUID: {view_guid})")
    
    # Print memory state before get_view_objects
    print("\nMemory state before get_view_objects:\n")
    dump_memory_state()
    
    # Add interaction for get_view_objects
    add_interaction("get_view_objects", {"version_urn": version_urn, "view_guid": view_guid}, 
                   "Pre-execution: Retrieving objects for view " + view_guid)
    
    # Get objects for the view
    objects_result = api_helper.get_view_objects(version_urn, view_guid)
    
    # Add interaction for get_view_objects with result
    if "error" in objects_result:
        add_interaction("get_view_objects", {"version_urn": version_urn, "view_guid": view_guid}, 
                       f"Error retrieving objects: {objects_result['error']}")
        print(f"[TEST] Error getting objects: {objects_result['error']}")
        return
    else:
        object_count = objects_result.get("object_count", 0)
        add_interaction("get_view_objects", {"version_urn": version_urn, "view_guid": view_guid}, 
                       f"Retrieved {object_count} objects for view {view_guid}")
    
    # Print memory state after get_view_objects
    print("\nMemory state after get_view_objects:\n")
    dump_memory_state()
    
    print(f"\n[TEST] Successfully retrieved objects for view {view_guid}")
    print(f"[TEST] Found {objects_result.get('object_count', 0)} total objects in the hierarchy")
    
    # Print a sample of the object hierarchy (top level)
    if "objects" in objects_result and "objects" in objects_result["objects"]:
        top_level_objects = objects_result["objects"]["objects"]
        print("\n[TEST] Top-level object hierarchy:")
        for i, obj in enumerate(top_level_objects, 1):
            print(f"  {i}. {obj.get('name', 'Unnamed')} (ID: {obj.get('objectid', 'N/A')})")
            
            # Print second level if available
            if "objects" in obj:
                for j, sub_obj in enumerate(obj["objects"], 1):
                    print(f"    {i}.{j}. {sub_obj.get('name', 'Unnamed')} (ID: {sub_obj.get('objectid', 'N/A')})")
    
    return objects_result

if __name__ == "__main__":
    # Check if APS_AUTH_TOKEN is set
    if not os.environ.get("APS_AUTH_TOKEN"):
        print("Error: APS_AUTH_TOKEN environment variable is not set.")
        print("Please set it before running this script.")
        sys.exit(1)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Test Autodesk API functions")
    parser.add_argument("--function", choices=["hubs", "projects", "filter", "items", "versions", "views", "properties", "objects"], 
                        help="Function to test")
    parser.add_argument("--hub-id", help="Hub ID for testing")
    parser.add_argument("--project-id", help="Project ID for testing")
    parser.add_argument("--item-id", help="Item ID for testing")
    parser.add_argument("--version-urn", help="Version URN for testing")
    parser.add_argument("--view-guid", help="View GUID for testing")
    parser.add_argument("--prefix", help="Prefix for filtering projects")
    
    args = parser.parse_args()
    
    # Run the requested test(s)
    if args.function == "hubs":
        test_get_hubs()
    elif args.function == "projects":
        if args.hub_id:
            test_get_projects(args.hub_id)
        else:
            print("Hub ID is required for testing get_projects")
    elif args.function == "filter":
        if args.hub_id and args.prefix:
            test_filter_projects(args.hub_id, args.prefix)
        else:
            print("Hub ID and prefix are required for testing filter_projects")
    elif args.function == "items":
        if args.hub_id and args.project_id:
            test_get_items(args.hub_id, args.project_id)
        else:
            print("Hub ID and Project ID are required for testing get_items")
    elif args.function == "versions":
        if args.item_id:
            test_get_versions(args.project_id, args.item_id)
        else:
            print("Item ID is required for testing get_versions")
    elif args.function == "views":
        if args.version_urn:
            test_get_model_views(args.version_urn)
        else:
            print("Version URN is required for testing get_model_views")
    elif args.function == "properties":
        if args.version_urn:
            test_get_view_properties(args.version_urn, args.view_guid)
        else:
            print("Version URN is required for testing get_view_properties")
    elif args.function == "objects":
        if args.version_urn:
            test_get_view_objects(args.version_urn, args.view_guid)
        else:
            print("Version URN is required for testing get_view_objects")
    else:
        print("Please specify a function to test")
        print("Available functions: hubs, projects, filter, items, versions, views, properties, objects") 