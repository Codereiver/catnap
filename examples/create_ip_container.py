#!/usr/bin/env python3
"""
Example: Create IP Address Container in Cato Networks

This example demonstrates how to create an IP address container,
optionally with initial IP addresses or ranges.

Usage:
    python create_ip_container.py --name "Container Name" --description "Description" [options]

Options:
    --name NAME         Container name (required)
    --description DESC  Container description (required)
    --ips IPS          Comma-separated IP addresses/ranges (optional)
    --ips-file FILE    File with IP addresses/ranges, one per line (optional)
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

Examples:
    # Create an empty container
    python create_ip_container.py --name "Blocked IPs" --description "IP addresses to block"
    
    # Create container with initial IPs
    python create_ip_container.py --name "Allowed IPs" --description "Whitelisted IPs" \\
        --ips "192.168.1.0/24,10.0.0.1,172.16.0.0/16"
    
    # Create container with IPs from file
    python create_ip_container.py --name "Corporate IPs" --description "Corporate network" \\
        --ips-file ./ip_list.txt
    
    # Get JSON output for scripting
    python create_ip_container.py --name "Test" --description "Test container" --format json
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


def print_simple(response):
    """Print container creation result in simple format"""
    if not response or 'data' not in response:
        print("❌ Container creation failed - no data in response")
        return
    
    # Navigate through the response structure
    container_data = response.get('data', {}).get('container', {})
    ip_range_data = container_data.get('ipAddressRange', {})
    create_data = ip_range_data.get('createFromFile', {})
    container = create_data.get('container', {})
    
    if not container:
        print("❌ Container creation failed - no container data returned")
        return
    
    print("\n✅ Container created successfully!\n")
    print("-" * 60)
    print(f"ID:          {container.get('id', 'N/A')}")
    print(f"Name:        {container.get('name', 'N/A')}")
    print(f"Description: {container.get('description', 'N/A')}")
    print(f"Size:        {container.get('size', 0)} items")
    print(f"Type:        {container.get('__typename', 'N/A')}")
    
    audit = container.get('audit', {})
    if audit:
        print(f"Created:     {format_datetime(audit.get('createdAt'))} by {audit.get('createdBy', 'N/A')}")
        if audit.get('lastModifiedAt'):
            print(f"Modified:    {format_datetime(audit.get('lastModifiedAt'))} by {audit.get('lastModifiedBy', 'N/A')}")
    
    print("-" * 60)
    
    size = container.get('size', 0)
    if size > 0:
        print(f"\n✅ Successfully added {size} IP address(es) to the container.")
    else:
        print("\n💡 Tip: You can now add IP addresses to this container using the Cato API or UI.")


def print_json(response):
    """Print full response as formatted JSON"""
    print(json.dumps(response, indent=2))


def validate_inputs(name, description):
    """Validate required inputs"""
    errors = []
    
    if not name or not name.strip():
        errors.append("Container name is required and cannot be empty")
    elif len(name) > 255:
        errors.append("Container name must be 255 characters or less")
    
    if not description or not description.strip():
        errors.append("Container description is required and cannot be empty")
    elif len(description) > 1000:
        errors.append("Container description must be 1000 characters or less")
    
    return errors


def main():
    parser = argparse.ArgumentParser(
        description='Create an IP address container in Cato Networks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This creates an IP address container, optionally with initial IP addresses.
Environment variables can be set in a .env file in the parent directory.
See .env.example for a template.

⚠️  WARNING: This will create a new container in your Cato account.
Make sure you have the necessary permissions before running this command.
        """
    )
    
    parser.add_argument('--name', required=True, help='Container name (required)')
    parser.add_argument('--description', required=True, help='Container description (required)')
    parser.add_argument('--ips', help='Comma-separated IP addresses/ranges')
    parser.add_argument('--ips-file', help='File with IP addresses/ranges, one per line')
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
    validation_errors = validate_inputs(args.name, args.description)
    if validation_errors:
        print("❌ Validation errors:", file=sys.stderr)
        for error in validation_errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)
    
    # Process IP addresses if provided
    ip_addresses = None
    if args.ips_file and args.ips:
        print("❌ Error: Cannot specify both --ips and --ips-file", file=sys.stderr)
        sys.exit(1)
    
    if args.ips_file:
        try:
            with open(args.ips_file, 'r') as f:
                ip_addresses = [line.strip() for line in f if line.strip()]
            print(f"Loaded {len(ip_addresses)} IP addresses from {args.ips_file}")
        except FileNotFoundError:
            print(f"❌ Error: File '{args.ips_file}' not found", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.ips:
        # Parse comma-separated IPs
        ip_addresses = [ip.strip() for ip in args.ips.split(',') if ip.strip()]
        print(f"Processing {len(ip_addresses)} IP addresses from command line")
    
    try:
        # Initialize API with CLI args taking precedence over env vars
        api = API(
            key=args.key,
            account_id=args.account,
            url=args.url,
            debug=args.debug
        )
        
        if ip_addresses:
            print(f"Creating IP address container '{args.name}' with {len(ip_addresses)} initial IP(s)...")
        else:
            print(f"Creating empty IP address container '{args.name}'...")
        
        # Create the container
        response = api.container_create_ip(
            name=args.name.strip(),
            description=args.description.strip(),
            ip_addresses=ip_addresses
        )
        
        # Format and print output
        if args.format == 'json':
            print_json(response)
        else:
            print_simple(response)
            
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
                    print(f"  - {message}", file=sys.stderr)
                else:
                    print(f"  - {error}", file=sys.stderr)
        sys.exit(1)
        
    except CatoNetworkError as e:
        print(f"❌ Network error: {e}", file=sys.stderr)
        print("\nPlease check your network connection and API endpoint URL.")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()