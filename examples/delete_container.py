#!/usr/bin/env python3
"""
Example: Delete a Container from Cato Networks

This example demonstrates how to delete an existing container
from your Cato account by name.

Usage:
    python delete_container.py --name "Container Name" [options]

Options:
    --name NAME        Container name to delete (required)
    --force            Skip confirmation prompt
    --key KEY          API key (overrides CATO_API_KEY env var)
    --account ACCOUNT  Account ID (overrides CATO_ACCOUNT_ID env var)  
    --url URL          API URL (overrides CATO_API_URL env var)
    --format FORMAT    Output format: json or simple (default: simple)
    --debug            Enable debug mode to show raw requests/responses
    -h, --help         Show this help message

Environment Variables:
    CATO_API_KEY       Your Cato API key
    CATO_ACCOUNT_ID    Your Cato account ID
    CATO_API_URL       API endpoint URL (optional)
    CATO_DEBUG         Set to 'true' to enable debug mode

Examples:
    # Delete a container with confirmation
    python delete_container.py --name "Test Container"
    
    # Delete without confirmation prompt
    python delete_container.py --name "Test Container" --force
    
    # Delete with debug output
    python delete_container.py --name "Test Container" --debug
    
    # Override credentials
    python delete_container.py --name "Test" --key YOUR_KEY --account YOUR_ACCOUNT
"""

import sys
import os
import json
import argparse
from datetime import datetime

# Add parent directory to path to import cato module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cato import API, CatoNetworkError, CatoGraphQLError


def get_container_type(container):
    """Extract container type from __typename field"""
    typename = container.get('__typename', '')
    if typename == 'IpAddressRangeContainer':
        return 'IP'
    elif typename == 'FqdnContainer':
        return 'FQDN'
    else:
        return 'Unknown'


def format_datetime(iso_string):
    """Convert ISO datetime string to readable format"""
    if not iso_string:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return iso_string


def print_simple(response):
    """Print deletion result in simple format"""
    if not response or 'data' not in response:
        print("❌ Container deletion failed - no data in response")
        return False
    
    # Navigate through the response structure
    container_data = response.get('data', {}).get('container', {})
    delete_data = container_data.get('delete', {})
    container = delete_data.get('container', {})
    
    if not container:
        print("❌ Container deletion failed - no container data returned")
        print("The container may not exist or you may not have permission to delete it.")
        return False
    
    print("\n✅ Container deleted successfully!\n")
    print("-" * 60)
    print(f"ID:          {container.get('id', 'N/A')}")
    print(f"Name:        {container.get('name', 'N/A')}")
    print(f"Type:        {get_container_type(container)}")
    print(f"Description: {container.get('description', 'N/A')}")
    print(f"Size:        {container.get('size', 0)} items (before deletion)")
    
    audit = container.get('audit', {})
    if audit:
        print(f"Created:     {format_datetime(audit.get('createdAt'))} by {audit.get('createdBy', 'N/A')}")
        if audit.get('lastModifiedAt'):
            print(f"Modified:    {format_datetime(audit.get('lastModifiedAt'))} by {audit.get('lastModifiedBy', 'N/A')}")
    
    print("-" * 60)
    print("\n⚠️  This container and all its contents have been permanently deleted.")
    return True


def print_json(response):
    """Print full response as formatted JSON"""
    print(json.dumps(response, indent=2))
    return bool(response and 'data' in response and response['data'])


def confirm_deletion(name):
    """Ask user to confirm deletion"""
    print(f"\n⚠️  WARNING: You are about to delete the container '{name}'")
    print("This action cannot be undone and will permanently remove:")
    print("  - The container")
    print("  - All IP addresses/data within the container")
    print("\nAre you sure you want to continue?")
    
    while True:
        response = input("Type 'yes' to confirm deletion or 'no' to cancel: ").strip().lower()
        if response == 'yes':
            return True
        elif response == 'no':
            return False
        else:
            print("Please type 'yes' or 'no'")


def main():
    parser = argparse.ArgumentParser(
        description='Delete a container from Cato Networks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
⚠️  WARNING: This will permanently delete a container and all its contents.
This action cannot be undone. Use with caution.

Environment variables can be set in a .env file in the parent directory.
See .env.example for a template.
        """
    )
    
    parser.add_argument('--name', required=True, help='Container name to delete (required)')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')
    parser.add_argument('--key', help='API key (overrides CATO_API_KEY env var)')
    parser.add_argument('--account', help='Account ID (overrides CATO_ACCOUNT_ID env var)')
    parser.add_argument('--url', help='API URL (overrides CATO_API_URL env var)')
    parser.add_argument(
        '--format',
        choices=['json', 'simple'],
        default='simple',
        help='Output format (default: simple)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode to show raw requests and responses'
    )
    
    args = parser.parse_args()
    
    # Validate container name
    if not args.name or not args.name.strip():
        print("❌ Error: Container name cannot be empty", file=sys.stderr)
        sys.exit(1)
    
    # Confirm deletion unless --force is used
    if not args.force:
        if not confirm_deletion(args.name):
            print("\n❌ Deletion cancelled by user.")
            sys.exit(0)
    
    try:
        # Initialize API with CLI args taking precedence over env vars
        api = API(
            key=args.key,
            account_id=args.account,
            url=args.url,
            debug=args.debug
        )
        
        print(f"\n🗑️  Deleting container '{args.name}'...")
        
        # Delete the container
        response = api.container_delete(name=args.name.strip())
        
        # Format and print output
        if args.format == 'json':
            success = print_json(response)
        else:
            success = print_simple(response)
        
        if not success:
            sys.exit(1)
            
    except ValueError as e:
        print(f"❌ Configuration error: {e}", file=sys.stderr)
        print("\nPlease ensure you have set the required environment variables or provided CLI parameters.")
        print("See --help for more information.")
        sys.exit(1)
        
    except CatoGraphQLError as e:
        print(f"❌ GraphQL error from API: {e}", file=sys.stderr)
        if hasattr(e, 'errors'):
            for error in e.errors:
                if isinstance(error, dict):
                    message = error.get('message', str(error))
                    # Check for common error patterns
                    if 'not found' in message.lower():
                        print(f"  ℹ️  Container '{args.name}' may not exist or you don't have access to it", file=sys.stderr)
                    elif 'permission' in message.lower() or 'denied' in message.lower():
                        print(f"  ℹ️  You don't have permission to delete this container", file=sys.stderr)
                    else:
                        print(f"  - {message}", file=sys.stderr)
                else:
                    print(f"  - {error}", file=sys.stderr)
        sys.exit(1)
        
    except CatoNetworkError as e:
        print(f"❌ Network error: {e}", file=sys.stderr)
        print("\nPlease check your network connection and API endpoint URL.")
        sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\n❌ Deletion cancelled by user (Ctrl+C)")
        sys.exit(130)
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()