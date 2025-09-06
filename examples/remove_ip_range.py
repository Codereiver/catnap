#!/usr/bin/env python3
"""
Example: Remove IP Range from Container in Cato Networks

This example demonstrates how to remove an IP address range from an existing
IP container in your Cato account. It will also remove the range from the
local cache if present.

Usage:
    python remove_ip_range.py --container "Container Name" --from-ip "192.168.1.1" --to-ip "192.168.1.10" [options]

Options:
    --container NAME    Container name to remove IPs from (required)
    --from-ip IP        Starting IP address of the range (required)
    --to-ip IP          Ending IP address of the range (required)
    --key KEY           API key (overrides CATO_API_KEY env var)
    --account ACCOUNT   Account ID (overrides CATO_ACCOUNT_ID env var)  
    --url URL           API URL (overrides CATO_API_URL env var)
    --format FORMAT     Output format: json or simple (default: simple)
    --debug             Enable debug mode to show raw requests/responses
    -h, --help          Show this help message

Environment Variables:
    CATO_API_KEY       Your Cato API key
    CATO_ACCOUNT_ID    Your Cato account ID
    CATO_API_URL       API endpoint URL (optional)
    CATO_DEBUG         Set to 'true' to enable debug mode

Examples:
    # Remove a single IP (from_ip = to_ip)
    python remove_ip_range.py --container "Blocked IPs" --from-ip "192.168.1.100" --to-ip "192.168.1.100"
    
    # Remove an IP range
    python remove_ip_range.py --container "Allowed IPs" --from-ip "10.0.0.1" --to-ip "10.0.0.255"
    
    # Remove with debug output to troubleshoot
    python remove_ip_range.py --container "Test IPs" --from-ip "172.16.1.1" --to-ip "172.16.1.50" --debug
    
    # Override credentials
    python remove_ip_range.py --container "Corporate IPs" --from-ip "203.0.113.1" --to-ip "203.0.113.100" \
        --key YOUR_KEY --account YOUR_ACCOUNT
    
    # Get JSON output for scripting
    python remove_ip_range.py --container "Test" --from-ip "127.0.0.1" --to-ip "127.0.0.1" --format json
"""

import sys
import os
import json
import argparse
from datetime import datetime
import ipaddress

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


def validate_ip_address(ip_str):
    """Validate IP address format"""
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False


def validate_ip_range(from_ip, to_ip):
    """Validate that IP range is logical (from_ip <= to_ip)"""
    try:
        from_addr = ipaddress.ip_address(from_ip)
        to_addr = ipaddress.ip_address(to_ip)
        
        # Must be same IP version (IPv4 or IPv6)
        if from_addr.version != to_addr.version:
            return False, f"IP addresses must be the same version (both IPv4 or both IPv6)"
        
        # from_ip should be <= to_ip
        if from_addr > to_addr:
            return False, f"Starting IP ({from_ip}) must be less than or equal to ending IP ({to_ip})"
        
        return True, None
    except ValueError as e:
        return False, str(e)


def print_simple(response, container_name, from_ip, to_ip, cache_removed):
    """Print IP range removal result in simple format"""
    if not response or 'data' not in response:
        print("❌ IP range removal failed - no data in response")
        return False
    
    # Navigate through the response structure
    container_data = response.get('data', {}).get('container', {})
    ip_data = container_data.get('ipAddressRange', {})
    remove_data = ip_data.get('removeValues', {})
    container = remove_data.get('container', {})
    
    if not container:
        print("❌ IP range removal failed - no container data returned")
        print("The container may not exist or you may not have permission to modify it.")
        print("The IP range may not exist in the container.")
        return False
    
    print("\n✅ IP range removed successfully!\n")
    print("-" * 60)
    print(f"Container:   {container.get('name', 'N/A')}")
    print(f"ID:          {container.get('id', 'N/A')}")
    print(f"Description: {container.get('description', 'N/A')}")
    print(f"Size:        {container.get('size', 0)} items")
    print(f"Type:        {container.get('__typename', 'N/A')}")
    
    # Show the range that was removed
    if from_ip == to_ip:
        print(f"Removed IP:  {from_ip}")
    else:
        print(f"Removed Range: {from_ip} - {to_ip}")
    
    # Show cache status
    if cache_removed:
        print(f"Cache:       ✅ Also removed from local cache")
    else:
        print(f"Cache:       ℹ️  Was not in local cache")
    
    audit = container.get('audit', {})
    if audit:
        print(f"Created:     {format_datetime(audit.get('createdAt'))} by {audit.get('createdBy', 'N/A')}")
        if audit.get('lastModifiedAt'):
            print(f"Modified:    {format_datetime(audit.get('lastModifiedAt'))} by {audit.get('lastModifiedBy', 'N/A')}")
    
    print("-" * 60)
    
    # Calculate range size for user info
    try:
        from_addr = ipaddress.ip_address(from_ip)
        to_addr = ipaddress.ip_address(to_ip)
        range_size = int(to_addr) - int(from_addr) + 1
        if range_size == 1:
            print(f"\n💡 Successfully removed 1 IP address from the container.")
        else:
            print(f"\n💡 Successfully removed a range of {range_size} IP addresses from the container.")
    except:
        print(f"\n💡 Successfully removed IP range {from_ip} - {to_ip} from the container.")
    
    return True


def print_json(response, cache_removed):
    """Print full response as formatted JSON with cache info"""
    output = {
        "api_response": response,
        "cache_removed": cache_removed
    }
    print(json.dumps(output, indent=2))
    return bool(response and 'data' in response and response['data'])


def validate_inputs(container_name, from_ip, to_ip):
    """Validate required inputs"""
    errors = []
    
    if not container_name or not container_name.strip():
        errors.append("Container name is required and cannot be empty")
    elif len(container_name) > 255:
        errors.append("Container name must be 255 characters or less")
    
    if not from_ip or not from_ip.strip():
        errors.append("Starting IP address is required")
    elif not validate_ip_address(from_ip.strip()):
        errors.append(f"Invalid starting IP address: '{from_ip}'")
    
    if not to_ip or not to_ip.strip():
        errors.append("Ending IP address is required")
    elif not validate_ip_address(to_ip.strip()):
        errors.append(f"Invalid ending IP address: '{to_ip}'")
    
    # Validate IP range if both IPs are valid
    if not errors or len([e for e in errors if 'IP address' in e]) == 0:
        valid_range, range_error = validate_ip_range(from_ip.strip(), to_ip.strip())
        if not valid_range:
            errors.append(range_error)
    
    return errors


def main():
    parser = argparse.ArgumentParser(
        description='Remove an IP range from an existing container in Cato Networks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This removes an IP address range from an existing IP container in your Cato account.
It will also remove the range from the local cache if present.
Environment variables can be set in a .env file in the parent directory.
See .env.example for a template.

⚠️  WARNING: This will modify an existing container in your Cato account.
Make sure you have the necessary permissions before running this command.

IP Address Examples:
  - Single IP: --from-ip "192.168.1.100" --to-ip "192.168.1.100"
  - IP Range:  --from-ip "10.0.0.1" --to-ip "10.0.0.255"
  - IPv6:      --from-ip "2001:db8::1" --to-ip "2001:db8::100"
        """
    )
    
    parser.add_argument('--container', required=True, help='Container name to remove IPs from (required)')
    parser.add_argument('--from-ip', required=True, help='Starting IP address of the range (required)')
    parser.add_argument('--to-ip', required=True, help='Ending IP address of the range (required)')
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
    
    # Validate inputs
    validation_errors = validate_inputs(args.container, args.from_ip, args.to_ip)
    if validation_errors:
        print("❌ Validation errors:", file=sys.stderr)
        for error in validation_errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)
    
    # Clean up IP addresses
    from_ip = args.from_ip.strip()
    to_ip = args.to_ip.strip()
    container_name = args.container.strip()
    
    try:
        # Initialize API with CLI args taking precedence over env vars
        api = API(
            key=args.key,
            account_id=args.account,
            url=args.url,
            debug=args.debug
        )
        
        # Check if the IP range is in cache before removal
        cache_had_range = False
        if api._cache:
            cache_had_range = api._cache.has_ip_range(container_name, from_ip, to_ip)
        
        if from_ip == to_ip:
            print(f"Removing IP address '{from_ip}' from container '{container_name}'...")
        else:
            print(f"Removing IP range '{from_ip}' - '{to_ip}' from container '{container_name}'...")
        
        # Remove the IP range from the container (API call also removes from cache)
        response = api.container_remove_ip_range(
            container_name=container_name,
            from_ip=from_ip,
            to_ip=to_ip
        )
        
        # Format and print output
        if args.format == 'json':
            success = print_json(response, cache_had_range)
        else:
            success = print_simple(response, container_name, from_ip, to_ip, cache_had_range)
        
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
                        print(f"  ℹ️  Container '{container_name}' may not exist or you don't have access to it", file=sys.stderr)
                        print(f"  ℹ️  Or the IP range may not exist in the container", file=sys.stderr)
                    elif 'permission' in message.lower() or 'denied' in message.lower():
                        print(f"  ℹ️  You don't have permission to modify this container", file=sys.stderr)
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
        print("\n\n❌ Operation cancelled by user (Ctrl+C)")
        sys.exit(130)
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()