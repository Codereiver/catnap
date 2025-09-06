#!/usr/bin/env python3
"""
list_container.py

List the contents of a specific Cato Networks container, showing each item
and whether it exists in the cache with timestamps.

This script shows the individual IP ranges or FQDNs within a container,
along with their cache status and last seen timestamps.

Usage:
    python list_container.py --name "Container Name" [options]

Examples:
    # List contents of an IP container
    python list_container.py --name "Blocked IPs"
    
    # List contents with JSON output
    python list_container.py --name "Malicious Domains" --format json
    
    # List with debug information
    python list_container.py --name "Corporate IPs" --debug
    
    # Override environment variables
    python list_container.py --name "Test Container" --key YOUR_KEY --account YOUR_ACCOUNT

Arguments:
    --name NAME         Container name to list contents of (required)
    --format FORMAT     Output format: json, table, or simple (default: simple)
    --no-cache         Disable cache functionality (cache enabled by default)
    --debug            Enable debug mode
    -h, --help         Show this help message

Environment Variables:
    CATO_API_KEY       Your Cato API key
    CATO_ACCOUNT_ID    Your Cato account ID
    CATO_API_URL       API endpoint URL (optional)
    CATO_CACHE_ENABLED Enable/disable cache (default: true)
    CATO_CACHE_PATH    Custom cache database path (optional)
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
        return 'N/A'
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return iso_string


def find_container_by_name(api, container_name):
    """Find a container by name and return its details"""
    try:
        response = api.container_list()
        
        if not response.get('data', {}).get('container', {}).get('list', {}).get('containers'):
            return None
        
        containers = response['data']['container']['list']['containers']
        
        for container in containers:
            if container.get('name') == container_name:
                return container
        
        return None
        
    except Exception as e:
        print(f"Error finding container: {e}", file=sys.stderr)
        return None


def get_cached_items(api, container_name):
    """Get cached items for the container"""
    if not api._cache:
        return {"ip_ranges": [], "fqdns": []}
    
    try:
        return api.container_list_cached_values(container_name)
    except Exception:
        return {"ip_ranges": [], "fqdns": []}


def print_simple(container, cached_items, show_cache=True):
    """Print container contents in simple format"""
    container_name = container.get('name', 'Unknown')
    container_type = get_container_type(container)
    container_size = container.get('size', 0)
    
    print(f"\n=== Container: {container_name} ===")
    print(f"Type:        {container_type}")
    print(f"Total Items: {container_size}")
    print(f"Description: {container.get('description', 'N/A')}")
    
    if container_size == 0:
        print("\nContainer is empty - no items to display.")
        return
    
    print(f"\n⚠️  Note: This container has {container_size} items, but the Cato API doesn't")
    print("    provide a way to retrieve the actual list of items from the server.")
    print("    The information below shows only items that exist in the local cache.")
    
    if not show_cache:
        print("\n(Cache functionality disabled - no cached items available)")
        return
    
    # Show cached IP ranges
    ip_ranges = cached_items.get("ip_ranges", [])
    if ip_ranges:
        print(f"\n--- Cached IP Ranges ({len(ip_ranges)} items) ---")
        for i, ip_range in enumerate(ip_ranges, 1):
            from_ip = ip_range.get('from_ip', 'N/A')
            to_ip = ip_range.get('to_ip', 'N/A')
            added = format_datetime(ip_range.get('added'))
            last_seen = format_datetime(ip_range.get('last_seen'))
            
            if from_ip == to_ip:
                print(f"{i:3d}. {from_ip}")
            else:
                print(f"{i:3d}. {from_ip} - {to_ip}")
            
            print(f"     Added:     {added}")
            print(f"     Last Seen: {last_seen}")
            if i < len(ip_ranges):
                print()
    
    # Show cached FQDNs
    fqdns = cached_items.get("fqdns", [])
    if fqdns:
        print(f"\n--- Cached FQDNs ({len(fqdns)} items) ---")
        for i, fqdn_item in enumerate(fqdns, 1):
            fqdn = fqdn_item.get('fqdn', 'N/A')
            added = format_datetime(fqdn_item.get('added'))
            last_seen = format_datetime(fqdn_item.get('last_seen'))
            
            print(f"{i:3d}. {fqdn}")
            print(f"     Added:     {added}")
            print(f"     Last Seen: {last_seen}")
            if i < len(fqdns):
                print()
    
    # Show summary
    total_cached = len(ip_ranges) + len(fqdns)
    if total_cached == 0:
        print(f"\n📭 No cached items found (0 of {container_size} items cached)")
        print("   Items will be cached when you add/interact with them using this tool.")
    elif total_cached < container_size:
        print(f"\n📊 Showing {total_cached} of {container_size} items (only cached items shown)")
        print(f"   {container_size - total_cached} items exist in the container but are not cached.")
    else:
        print(f"\n✅ All {total_cached} items are cached")


def print_table(container, cached_items, show_cache=True):
    """Print container contents in table format"""
    container_name = container.get('name', 'Unknown')
    container_type = get_container_type(container)
    container_size = container.get('size', 0)
    
    print(f"\n=== Container: {container_name} ({container_type}) ===")
    print(f"Total Items: {container_size}")
    
    if container_size == 0:
        print("\nContainer is empty.")
        return
    
    if not show_cache:
        print("\n(Cache functionality disabled)")
        return
    
    ip_ranges = cached_items.get("ip_ranges", [])
    fqdns = cached_items.get("fqdns", [])
    total_cached = len(ip_ranges) + len(fqdns)
    
    if total_cached == 0:
        print(f"\nNo cached items (0 of {container_size} items cached)")
        return
    
    print(f"\nShowing {total_cached} of {container_size} cached items:")
    
    if ip_ranges:
        print(f"\n{'#':<3} {'From IP':<15} {'To IP':<15} {'Added':<19} {'Last Seen':<19}")
        print("-" * 75)
        
        for i, ip_range in enumerate(ip_ranges, 1):
            from_ip = ip_range.get('from_ip', 'N/A')[:15]
            to_ip = ip_range.get('to_ip', 'N/A')[:15]
            added = format_datetime(ip_range.get('added'))[:19]
            last_seen = format_datetime(ip_range.get('last_seen'))[:19]
            
            print(f"{i:<3} {from_ip:<15} {to_ip:<15} {added:<19} {last_seen:<19}")
    
    if fqdns:
        print(f"\n{'#':<3} {'FQDN':<40} {'Added':<19} {'Last Seen':<19}")
        print("-" * 85)
        
        for i, fqdn_item in enumerate(fqdns, 1):
            fqdn = fqdn_item.get('fqdn', 'N/A')[:40]
            added = format_datetime(fqdn_item.get('added'))[:19]
            last_seen = format_datetime(fqdn_item.get('last_seen'))[:19]
            
            print(f"{i:<3} {fqdn:<40} {added:<19} {last_seen:<19}")


def print_json(container, cached_items, show_cache=True):
    """Print container contents as JSON"""
    result = {
        "container": {
            "name": container.get('name'),
            "type": get_container_type(container),
            "typename": container.get('__typename'),
            "description": container.get('description'),
            "size": container.get('size', 0),
            "id": container.get('id')
        }
    }
    
    if show_cache:
        result["cached_items"] = cached_items
        result["cache_summary"] = {
            "total_cached": len(cached_items.get("ip_ranges", [])) + len(cached_items.get("fqdns", [])),
            "cached_ip_ranges": len(cached_items.get("ip_ranges", [])),
            "cached_fqdns": len(cached_items.get("fqdns", [])),
            "container_size": container.get('size', 0)
        }
    else:
        result["note"] = "Cache functionality disabled"
    
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="List contents of a Cato Networks container with cache information",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List contents of an IP container
  python list_container.py --name "Blocked IPs"
  
  # List contents with table format
  python list_container.py --name "Malicious Domains" --format table
  
  # List with JSON output
  python list_container.py --name "Corporate IPs" --format json
  
  # Disable cache to see container info only
  python list_container.py --name "Test Container" --no-cache
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--name',
        required=True,
        help='Container name to list contents of (required)'
    )
    
    # Optional arguments
    parser.add_argument(
        '--format',
        choices=['json', 'table', 'simple'],
        default='simple',
        help='Output format (default: simple)'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable cache functionality (cache enabled by default)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode to show raw requests and responses'
    )
    
    # API configuration (optional - can use environment variables)
    parser.add_argument('--key', help='API key (overrides CATO_API_KEY env var)')
    parser.add_argument('--account', help='Account ID (overrides CATO_ACCOUNT_ID env var)')
    parser.add_argument('--url', help='API URL (overrides CATO_API_URL env var)')
    parser.add_argument('--cache-path', help='Cache file path (overrides CATO_CACHE_PATH env var)')
    
    args = parser.parse_args()
    
    # Validate container name
    container_name = args.name.strip()
    if not container_name:
        print("Error: Container name cannot be empty", file=sys.stderr)
        return 1
    
    try:
        print("Connecting to Cato API...")
        
        # Initialize API
        api = API(
            key=args.key,
            account_id=args.account,
            url=args.url,
            debug=args.debug,
            cache_enabled=not args.no_cache,
            cache_path=args.cache_path
        )
        
        # Find the container
        print(f"Looking for container '{container_name}'...")
        container = find_container_by_name(api, container_name)
        
        if not container:
            print(f"\n❌ Container '{container_name}' not found.", file=sys.stderr)
            print("\nAvailable containers:", file=sys.stderr)
            
            try:
                response = api.container_list()
                containers = response.get('data', {}).get('container', {}).get('list', {}).get('containers', [])
                if containers:
                    for c in containers:
                        print(f"  - {c.get('name', 'N/A')} ({get_container_type(c)})", file=sys.stderr)
                else:
                    print("  (No containers found)", file=sys.stderr)
            except Exception:
                pass
            
            return 1
        
        # Get cached items if cache is enabled
        cached_items = {"ip_ranges": [], "fqdns": []}
        if not args.no_cache:
            cached_items = get_cached_items(api, container_name)
        
        # Print results based on format
        if args.format == 'json':
            print_json(container, cached_items, not args.no_cache)
        elif args.format == 'table':
            print_table(container, cached_items, not args.no_cache)
        else:  # simple
            print_simple(container, cached_items, not args.no_cache)
        
        return 0
        
    except CatoNetworkError as e:
        print(f"\n❌ Network error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
        
    except CatoGraphQLError as e:
        print(f"\n❌ API error: {e}", file=sys.stderr)
        
        # Check for specific error types
        for error in e.errors:
            if isinstance(error, dict):
                message = error.get('message', '')
                if 'permission' in message.lower() or 'denied' in message.lower():
                    print(f"  ℹ️  Check that your API key has sufficient permissions", file=sys.stderr)
                elif 'not found' in message.lower():
                    print(f"  ℹ️  Container '{container_name}' may not exist or you don't have access to it", file=sys.stderr)
        
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())