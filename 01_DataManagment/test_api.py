#!/usr/bin/env python
"""
Test script for Autodesk API Helper functions.
This allows testing individual API functions without running the full Streamlit app.
"""

# Command line arguments:
# --function: "hubs", "projects", "filter", "items", "versions", "all"
# --hub-id: "b.17303213-7d00-46b0-8773-a11ba49dd3ce"
# --project-id: "b.0a202083-0cef-44d6-8c4c-d561853cc403"
# --item-id: "b.0a202083-0cef-44d6-8c4c-d561853cc403"
# --prefix: "KP_ADSK"

# Example:
# python test_api.py --function projects --hub-id b.17303213-7d00-46b0-8773-a11ba49dd3ce
# python test_api.py --function items --hub-id b.17303213-7d00-46b0-8773-a11ba49dd3ce --project-id b.0a202083-0cef-44d6-8c4c-d561853cc403

import os
import json
import sys
from dm_3_helpers import AutodeskAPIHelper, dump_memory_state, add_interaction

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

if __name__ == "__main__":
    # Check if APS_AUTH_TOKEN is set
    if not os.environ.get("APS_AUTH_TOKEN"):
        print("Error: APS_AUTH_TOKEN environment variable is not set.")
        print("Please set it before running this script.")
        sys.exit(1)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Test Autodesk API Helper functions")
    parser.add_argument("--function", choices=["hubs", "projects", "filter", "items", "versions", "all"], 
                        default="items", help="Function to test")
    parser.add_argument("--hub-id", default="b.17303213-7d00-46b0-8773-a11ba49dd3ce", 
                        help="Hub ID to use for testing")
    parser.add_argument("--project-id", default="b.0a202083-0cef-44d6-8c4c-d561853cc403", 
                        help="Project ID to use for testing")
    parser.add_argument("--item-id", default=None, 
                        help="Item ID to use for testing versions")
    parser.add_argument("--prefix", default="KP_ADSK", 
                        help="Prefix to use for filtering projects")
    
    args = parser.parse_args()
    
    # Run the requested test(s)
    if args.function == "hubs" or args.function == "all":
        test_get_hubs()
    
    if args.function == "projects" or args.function == "all":
        test_get_projects(args.hub_id)
    
    if args.function == "filter" or args.function == "all":
        test_filter_projects(args.hub_id, args.prefix)
    
    if args.function == "items" or args.function == "all":
        test_get_items(args.hub_id, args.project_id)
    
    if args.function == "versions" or args.function == "all" and args.item_id:
        test_get_versions(args.project_id, args.item_id) 