#!/usr/bin/env python3
"""
Example: Add FQDNs to Container in Cato Networks

This example demonstrates how to add fully qualified domain names (FQDNs)
to an existing FQDN container in your Cato account.

Usage:
    python add_fqdns.py --container "Container Name" --fqdns "domain1.com,domain2.com" [options]

Options:
    --container NAME    Container name to add FQDNs to (required)
    --fqdns FQDNS       Comma-separated FQDNs to add (required)
    --fqdns-file FILE   File with FQDNs, one per line (alternative to --fqdns)
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
    # Add multiple FQDNs from command line
    python add_fqdns.py --container "Blocked Domains" --fqdns "malware.com,phishing.net,spam.org"
    
    # Add multiple subdomains
    python add_fqdns.py --container "Social Media" --fqdns "m.facebook.com,api.twitter.com,cdn.instagram.com"
    
    # Add FQDNs from file
    python add_fqdns.py --container "Corporate Domains" --fqdns-file ./additional_domains.txt
    
    # Add with debug output to troubleshoot
    python add_fqdns.py --container "Test Domains" --fqdns "test1.local,test2.local" --debug
    
    # Override credentials
    python add_fqdns.py --container "External Domains" --fqdns "api.example.com" \
        --key YOUR_KEY --account YOUR_ACCOUNT
    
    # Get JSON output for scripting
    python add_fqdns.py --container "Test" --fqdns "example.com" --format json
"""

import sys
import os
import json
import argparse
from datetime import datetime
import re

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
    
    domain = fqdn
    
    # Basic checks: no spaces, contains dots (except localhost), reasonable length
    if ' ' in domain:
        return False
    if len(fqdn) > 253:  # RFC limit
        return False
    if not '.' in domain and domain != 'localhost':
        return False
    
    # Basic domain name pattern (no wildcards allowed)
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    if not re.match(pattern, fqdn):
        return False
    
    return True


def validate_fqdns(fqdns):
    """Validate a list of FQDNs"""
    if not fqdns:
        return []
    
    errors = []
    for i, fqdn in enumerate(fqdns):
        if not validate_fqdn(fqdn):
            errors.append(f"Invalid FQDN at position {i+1}: '{fqdn}'")
    
    return errors


def print_simple(response, container_name, fqdns):
    """Print FQDN addition result in simple format"""
    if not response or 'data' not in response:
        print("❌ FQDN addition failed - no data in response")
        return False
    
    # Navigate through the response structure
    container_data = response.get('data', {}).get('container', {})
    fqdn_data = container_data.get('fqdn', {})
    add_data = fqdn_data.get('addValues', {})
    container = add_data.get('container', {})
    
    if not container:
        print("❌ FQDN addition failed - no container data returned")
        print("The container may not exist or you may not have permission to modify it.")
        return False
    
    print("\\n✅ FQDNs added successfully!\\n")
    print("-" * 60)
    print(f"Container:   {container.get('name', 'N/A')}")
    print(f"ID:          {container.get('id', 'N/A')}")
    print(f"Description: {container.get('description', 'N/A')}")
    print(f"Size:        {container.get('size', 0)} items")
    print(f"Type:        {container.get('__typename', 'N/A')}")
    
    # Show the FQDNs that were added
    print(f"Added FQDNs: {len(fqdns)} domain(s)")
    for i, fqdn in enumerate(fqdns, 1):
        print(f"  {i:2d}. {fqdn}")
    
    audit = container.get('audit', {})
    if audit:
        print(f"Created:     {format_datetime(audit.get('createdAt'))} by {audit.get('createdBy', 'N/A')}")
        if audit.get('lastModifiedAt'):
            print(f"Modified:    {format_datetime(audit.get('lastModifiedAt'))} by {audit.get('lastModifiedBy', 'N/A')}")
    
    print("-" * 60)
    
    # User info
    if len(fqdns) == 1:
        print(f"\\n💡 Successfully added 1 FQDN to the container.")
    else:
        print(f"\\n💡 Successfully added {len(fqdns)} FQDNs to the container.")
    
    return True


def print_json(response):
    """Print full response as formatted JSON"""
    print(json.dumps(response, indent=2))
    return bool(response and 'data' in response and response['data'])


def validate_inputs(container_name, fqdns):
    """Validate required inputs"""
    errors = []
    
    if not container_name or not container_name.strip():
        errors.append("Container name is required and cannot be empty")
    elif len(container_name) > 255:
        errors.append("Container name must be 255 characters or less")
    
    if not fqdns or len(fqdns) == 0:
        errors.append("At least one FQDN is required")
    else:
        # Validate individual FQDNs
        fqdn_errors = validate_fqdns(fqdns)
        errors.extend(fqdn_errors)
        
        # Check for duplicates
        seen_fqdns = set()
        for i, fqdn in enumerate(fqdns):
            if fqdn in seen_fqdns:
                errors.append(f"Duplicate FQDN at position {i+1}: '{fqdn}'")
            seen_fqdns.add(fqdn)
    
    return errors


def main():
    parser = argparse.ArgumentParser(
        description='Add FQDNs to an existing FQDN container in Cato Networks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This adds fully qualified domain names (FQDNs) to an existing FQDN container.
Environment variables can be set in a .env file in the parent directory.
See .env.example for a template.

⚠️  WARNING: This will modify an existing container in your Cato account.
Make sure you have the necessary permissions before running this command.

FQDN Examples:
  - Standard domains: example.com, subdomain.example.com
  - Subdomains: mail.example.com, api.example.com
  - Local domains: test.local, dev.internal
  - API endpoints: api.github.com, api.example.org

Note: Wildcards (e.g., *.example.com) are not supported by the Cato API
        """
    )
    
    parser.add_argument('--container', required=True, help='Container name to add FQDNs to (required)')
    
    # FQDN input options (mutually exclusive)
    fqdn_group = parser.add_mutually_exclusive_group(required=True)
    fqdn_group.add_argument('--fqdns', help='Comma-separated FQDNs to add (required)')
    fqdn_group.add_argument('--fqdns-file', help='File with FQDNs, one per line')
    
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
    
    # Process FQDNs
    fqdns = None
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
    
    # Validate inputs
    validation_errors = validate_inputs(args.container, fqdns)
    if validation_errors:
        print("❌ Validation errors:", file=sys.stderr)
        for error in validation_errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)
    
    # Clean up inputs
    container_name = args.container.strip()
    
    try:
        # Initialize API with CLI args taking precedence over env vars
        api = API(
            key=args.key,
            account_id=args.account,
            url=args.url,
            debug=args.debug
        )
        
        if len(fqdns) == 1:
            print(f"Adding FQDN '{fqdns[0]}' to container '{container_name}'...")
        else:
            print(f"Adding {len(fqdns)} FQDNs to container '{container_name}'...")
        
        # Add the FQDNs to the container
        response = api.container_add_fqdns(
            container_name=container_name,
            fqdns=fqdns
        )
        
        # Format and print output
        if args.format == 'json':
            success = print_json(response)
        else:
            success = print_simple(response, container_name, fqdns)
        
        if not success:
            sys.exit(1)
            
    except ValueError as e:
        print(f"❌ Configuration error: {e}", file=sys.stderr)
        print("\\nPlease ensure you have set the required environment variables or provided CLI parameters.")
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
                    elif 'permission' in message.lower() or 'denied' in message.lower():
                        print(f"  ℹ️  You don't have permission to modify this container", file=sys.stderr)
                    elif 'duplicate' in message.lower() or 'already exists' in message.lower():
                        print(f"  ℹ️  Some FQDNs may already exist in this container", file=sys.stderr)
                    elif 'invalid' in message.lower():
                        print(f"  ℹ️  One or more FQDNs may be invalid or malformed", file=sys.stderr)
                    else:
                        print(f"  - {message}", file=sys.stderr)
                else:
                    print(f"  - {error}", file=sys.stderr)
        sys.exit(1)
        
    except CatoNetworkError as e:
        print(f"❌ Network error: {e}", file=sys.stderr)
        print("\\nPlease check your network connection and API endpoint URL.")
        sys.exit(1)
        
    except KeyboardInterrupt:
        print("\\n\\n❌ Operation cancelled by user (Ctrl+C)")
        sys.exit(130)
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()