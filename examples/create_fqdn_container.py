#!/usr/bin/env python3
"""
Example: Create FQDN Container in Cato Networks

This example demonstrates how to create an FQDN container,
optionally with initial fully qualified domain names.

Usage:
    python create_fqdn_container.py --name "Container Name" --description "Description" [options]

Options:
    --name NAME         Container name (required)
    --description DESC  Container description (required)
    --fqdns FQDNS       Comma-separated FQDNs (optional)
    --fqdns-file FILE   File with FQDNs, one per line (optional)
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
    # Create an empty container
    python create_fqdn_container.py --name "Blocked Domains" --description "Domain names to block"
    
    # Create container with initial FQDNs
    python create_fqdn_container.py --name "Allowed Domains" --description "Whitelisted domains" \\
        --fqdns "example.com,mail.google.com,api.github.com"
    
    # Create container with FQDNs from file
    python create_fqdn_container.py --name "Corporate Domains" --description "Internal domains" \\
        --fqdns-file ./domain_list.txt
    
    # Get JSON output for scripting
    python create_fqdn_container.py --name "Test" --description "Test container" --format json
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


def validate_fqdn(fqdn):
    """Basic FQDN validation"""
    if not fqdn or not isinstance(fqdn, str):
        return False
    
    # Wildcards are not allowed in Cato API
    if fqdn.startswith('*.'):
        return False
    
    # Basic checks: no spaces, contains dots, reasonable length
    if ' ' in fqdn:
        return False
    if len(fqdn) > 253:  # RFC limit
        return False
    if not '.' in fqdn and fqdn != 'localhost':
        return False
    
    return True


def print_simple(response):
    """Print container creation result in simple format"""
    if not response or 'data' not in response:
        print("❌ Container creation failed - no data in response")
        return
    
    # Navigate through the response structure
    container_data = response.get('data', {}).get('container', {})
    fqdn_data = container_data.get('fqdn', {})
    create_data = fqdn_data.get('createFromFile', {})
    container = create_data.get('container', {})
    
    if not container:
        print("❌ Container creation failed - no container data returned")
        return
    
    print("\n✅ FQDN Container created successfully!\n")
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
        print(f"\n✅ Successfully added {size} FQDN(s) to the container.")
    else:
        print("\n💡 Tip: You can now add FQDNs to this container using the Cato API or UI.")


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


def validate_fqdns(fqdns):
    """Validate a list of FQDNs"""
    if not fqdns:
        return []
    
    errors = []
    for i, fqdn in enumerate(fqdns):
        if not validate_fqdn(fqdn):
            errors.append(f"Invalid FQDN at position {i+1}: '{fqdn}'")
    
    return errors


def main():
    parser = argparse.ArgumentParser(
        description='Create an FQDN container in Cato Networks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This creates an FQDN container, optionally with initial domain names.
Environment variables can be set in a .env file in the parent directory.
See .env.example for a template.

⚠️  WARNING: This will create a new container in your Cato account.
Make sure you have the necessary permissions before running this command.

FQDN Examples:
  - example.com
  - subdomain.example.com  
  - api.github.com
  - mail.server.com
        """
    )
    
    parser.add_argument('--name', required=True, help='Container name (required)')
    parser.add_argument('--description', required=True, help='Container description (required)')
    parser.add_argument('--fqdns', help='Comma-separated FQDNs')
    parser.add_argument('--fqdns-file', help='File with FQDNs, one per line')
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
    
    # Process FQDNs if provided
    fqdns = None
    if args.fqdns_file and args.fqdns:
        print("❌ Error: Cannot specify both --fqdns and --fqdns-file", file=sys.stderr)
        sys.exit(1)
    
    if args.fqdns_file:
        try:
            with open(args.fqdns_file, 'r') as f:
                fqdns = [line.strip() for line in f if line.strip()]
            print(f"Loaded {len(fqdns)} FQDNs from {args.fqdns_file}")
        except FileNotFoundError:
            print(f"❌ Error: File '{args.fqdns_file}' not found", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.fqdns:
        # Parse comma-separated FQDNs
        fqdns = [fqdn.strip() for fqdn in args.fqdns.split(',') if fqdn.strip()]
        print(f"Processing {len(fqdns)} FQDNs from command line")
    
    # Validate FQDNs if provided
    if fqdns:
        fqdn_errors = validate_fqdns(fqdns)
        if fqdn_errors:
            print("❌ FQDN validation errors:", file=sys.stderr)
            for error in fqdn_errors:
                print(f"  - {error}", file=sys.stderr)
            sys.exit(1)
    
    try:
        # Initialize API with CLI args taking precedence over env vars
        api = API(
            key=args.key,
            account_id=args.account,
            url=args.url,
            debug=args.debug
        )
        
        if fqdns:
            print(f"Creating FQDN container '{args.name}' with {len(fqdns)} initial FQDN(s)...")
        else:
            print(f"Creating empty FQDN container '{args.name}'...")
        
        # Create the container
        response = api.container_create_fqdn(
            name=args.name.strip(),
            description=args.description.strip(),
            fqdns=fqdns
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