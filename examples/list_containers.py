#!/usr/bin/env python3
"""
Example: List Containers from Cato Networks API

This example demonstrates how to use the Cato API wrapper to retrieve
a list of containers from your Cato account.

Usage:
    python list_containers.py [options]

Options:
    --key KEY           API key (overrides CATO_API_KEY env var)
    --account ACCOUNT   Account ID (overrides CATO_ACCOUNT_ID env var)  
    --url URL          API URL (overrides CATO_API_URL env var)
    --format FORMAT    Output format: json, table, or simple (default: simple)
    --no-cache         Disable cache functionality (cache enabled by default)
    --debug            Enable debug mode
    -h, --help         Show this help message

Environment Variables:
    CATO_API_KEY       Your Cato API key
    CATO_ACCOUNT_ID    Your Cato account ID
    CATO_API_URL       API endpoint URL (optional)
    CATO_CACHE_ENABLED Enable/disable cache (default: true)
    CATO_CACHE_PATH    Custom cache file path (optional)

Examples:
    # Use environment variables (from .env file or exported)
    python list_containers.py
    
    # Override with CLI parameters
    python list_containers.py --key YOUR_KEY --account YOUR_ACCOUNT
    
    # Use table format to see cache information at a glance
    python list_containers.py --format table
    
    # Disable cache to see containers without cache information
    python list_containers.py --no-cache
    
    # Use JSON output format to see full response including cache data
    python list_containers.py --format json
"""

import sys
import os
import json
import argparse
from datetime import datetime

# Add parent directory to path to import cato module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cato import API, CatoNetworkError, CatoGraphQLError


def format_datetime(iso_string):
    """Convert ISO datetime string to readable format"""
    if not iso_string:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return iso_string


def print_simple(containers):
    """Print containers in simple format"""
    if not containers:
        print("No containers found.")
        return
    
    print(f"\nFound {len(containers)} container(s):\n")
    print("-" * 80)
    
    for container in containers:
        print(f"ID:          {container.get('id', 'N/A')}")
        print(f"Name:        {container.get('name', 'N/A')}")
        print(f"Description: {container.get('description', 'N/A')}")
        print(f"Size:        {container.get('size', 'N/A')}")
        
        # Display cache information if available
        cache_info = container.get('cache')
        if cache_info:
            cached_status = "Yes" if cache_info.get('cached', False) else "No"
            print(f"Cached:      {cached_status}")
            
            if cache_info.get('cached', False):
                total_cached = cache_info.get('total_cached', 0)
                cached_ips = cache_info.get('cached_ip_ranges', 0)
                cached_fqdns = cache_info.get('cached_fqdns', 0)
                
                print(f"Cache:       {total_cached} entries ({cached_ips} IP ranges, {cached_fqdns} FQDNs)")
                
                if 'last_sync' in cache_info:
                    print(f"Last Sync:   {format_datetime(cache_info['last_sync'])}")
        
        audit = container.get('audit', {})
        if audit:
            print(f"Created:     {format_datetime(audit.get('createdAt'))} by {audit.get('createdBy', 'N/A')}")
            print(f"Modified:    {format_datetime(audit.get('lastModifiedAt'))} by {audit.get('lastModifiedBy', 'N/A')}")
        
        print("-" * 80)


def print_table(containers):
    """Print containers in table format"""
    if not containers:
        print("No containers found.")
        return
    
    # Calculate column widths
    id_width = max(len(str(c.get('id', ''))) for c in containers)
    name_width = max(len(str(c.get('name', ''))) for c in containers)
    desc_width = min(25, max(len(str(c.get('description', ''))) for c in containers))
    
    # Ensure minimum widths
    id_width = max(8, id_width)
    name_width = max(12, name_width)
    
    # Check if any containers have cache info
    has_cache_info = any(c.get('cache') for c in containers)
    
    # Print header
    if has_cache_info:
        print(f"\n{'ID':<{id_width}} {'Name':<{name_width}} {'Description':<{desc_width}} {'Size':<6} {'Cached':<7} {'Cache':<12} {'Modified':<20}")
        print("-" * (id_width + name_width + desc_width + 6 + 7 + 12 + 20 + 7))
    else:
        print(f"\n{'ID':<{id_width}} {'Name':<{name_width}} {'Description':<{desc_width}} {'Size':<10} {'Modified':<20}")
        print("-" * (id_width + name_width + desc_width + 10 + 20 + 4))
    
    # Print rows
    for container in containers:
        container_id = str(container.get('id', 'N/A'))[:id_width]
        name = str(container.get('name', 'N/A'))[:name_width]
        description = str(container.get('description', 'N/A'))[:desc_width]
        size = str(container.get('size', 'N/A'))[:6]
        
        audit = container.get('audit', {})
        modified = format_datetime(audit.get('lastModifiedAt'))[:20] if audit else 'N/A'
        
        if has_cache_info:
            cache_info = container.get('cache', {})
            cached_status = "Yes" if cache_info.get('cached', False) else "No"
            
            if cache_info.get('cached', False):
                total_cached = cache_info.get('total_cached', 0)
                cached_ips = cache_info.get('cached_ip_ranges', 0)
                cached_fqdns = cache_info.get('cached_fqdns', 0)
                cache_summary = f"{cached_ips}ip,{cached_fqdns}fq"[:12]
            else:
                cache_summary = "-"[:12]
            
            print(f"{container_id:<{id_width}} {name:<{name_width}} {description:<{desc_width}} {size:<6} {cached_status:<7} {cache_summary:<12} {modified:<20}")
        else:
            print(f"{container_id:<{id_width}} {name:<{name_width}} {description:<{desc_width}} {size:<10} {modified:<20}")


def print_json(response):
    """Print full response as formatted JSON"""
    print(json.dumps(response, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description='List containers from Cato Networks API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment variables can be set in a .env file in the parent directory.
See .env.example for a template.
        """
    )
    
    parser.add_argument('--key', help='API key (overrides CATO_API_KEY env var)')
    parser.add_argument('--account', help='Account ID (overrides CATO_ACCOUNT_ID env var)')
    parser.add_argument('--url', help='API URL (overrides CATO_API_URL env var)')
    parser.add_argument(
        '--format',
        choices=['json', 'table', 'simple'],
        default='simple',
        help='Output format (default: simple)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode to show raw requests and responses'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable cache functionality (cache is enabled by default)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize API with CLI args taking precedence over env vars
        api = API(
            key=args.key,
            account_id=args.account,
            url=args.url,
            debug=args.debug,
            cache_enabled=not args.no_cache
        )
        
        print("Connecting to Cato API...")
        
        # Retrieve containers
        response = api.container_list()
        
        # Extract containers from response
        containers = []
        if response and 'data' in response:
            container_data = response.get('data', {}).get('container', {})
            list_data = container_data.get('list', {})
            containers = list_data.get('containers', [])
        
        # Format and print output
        if args.format == 'json':
            print_json(response)
        elif args.format == 'table':
            print_table(containers)
        else:
            print_simple(containers)
            
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        print("\nPlease ensure you have set the required environment variables or provided CLI parameters.")
        print("See --help for more information.")
        sys.exit(1)
        
    except CatoGraphQLError as e:
        print(f"GraphQL error from API: {e}", file=sys.stderr)
        if hasattr(e, 'errors'):
            for error in e.errors:
                print(f"  - {error}", file=sys.stderr)
        sys.exit(1)
        
    except CatoNetworkError as e:
        print(f"Network error: {e}", file=sys.stderr)
        print("\nPlease check your network connection and API endpoint URL.")
        sys.exit(1)
        
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()