#!/usr/bin/env python3
"""
Example: Remove FQDNs from Container in Cato Networks

This example demonstrates how to remove fully qualified domain names (FQDNs)
from an existing FQDN container in your Cato account. It will also remove the 
FQDNs from the local cache if present.

Usage:
    python remove_fqdns.py --container "Container Name" --fqdns "domain1.com,domain2.com" [options]

Options:
    --container NAME    Container name to remove FQDNs from (required)
    --fqdns FQDNS       Comma-separated FQDNs to remove (required)
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
    # Remove multiple FQDNs from command line
    python remove_fqdns.py --container "Blocked Domains" --fqdns "malware.com,phishing.net,spam.org"
    
    # Remove multiple subdomains
    python remove_fqdns.py --container "Social Media" --fqdns "m.facebook.com,api.twitter.com,cdn.instagram.com"
    
    # Remove FQDNs from file
    python remove_fqdns.py --container "Corporate Domains" --fqdns-file ./domains_to_remove.txt
    
    # Remove with debug output to troubleshoot
    python remove_fqdns.py --container "Test Domains" --fqdns "test1.local,test2.local" --debug
    
    # Override credentials
    python remove_fqdns.py --container "External Domains" --fqdns "api.example.com" \
        --key YOUR_KEY --account YOUR_ACCOUNT
    
    # Get JSON output for scripting
    python remove_fqdns.py --container "Test" --fqdns "example.com" --format json
"""

import sys
import os
import json
import argparse
from datetime import datetime
import re
from pathlib import Path

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
    """
    Validate FQDN format using basic regex.
    This is a simple validation - not comprehensive.
    """
    if not fqdn or not isinstance(fqdn, str):
        return False
    
    # Remove leading/trailing whitespace
    fqdn = fqdn.strip()
    
    # Basic length check
    if len(fqdn) < 1 or len(fqdn) > 253:
        return False
    
    # Basic pattern: letters, numbers, dots, hyphens
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*\.?$'
    
    return bool(re.match(pattern, fqdn))


def read_fqdns_from_file(file_path):
    """Read FQDNs from a file, one per line"""
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        fqdns = []
        with open(path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):  # Skip empty lines and comments
                    if validate_fqdn(line):
                        fqdns.append(line)
                    else:
                        print(f"Warning: Invalid FQDN on line {line_num}: '{line}' - skipping", file=sys.stderr)
        
        return fqdns
    except Exception as e:
        raise ValueError(f"Error reading FQDNs file: {e}")


def parse_fqdns(fqdns_str, fqdns_file):
    """Parse FQDNs from string or file"""
    fqdns = []
    
    if fqdns_file:
        fqdns.extend(read_fqdns_from_file(fqdns_file))
    
    if fqdns_str:
        for fqdn in fqdns_str.split(','):
            fqdn = fqdn.strip()
            if fqdn:
                if validate_fqdn(fqdn):
                    fqdns.append(fqdn)
                else:
                    raise ValueError(f"Invalid FQDN: '{fqdn}'")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_fqdns = []
    for fqdn in fqdns:
        if fqdn.lower() not in seen:
            seen.add(fqdn.lower())
            unique_fqdns.append(fqdn)
    
    return unique_fqdns


def print_simple(response, container_name, fqdns, cache_removed_count):
    """Print FQDN removal result in simple format"""
    if not response or 'data' not in response:
        print("❌ FQDN removal failed - no data in response")
        return False
    
    # Navigate through the response structure
    container_data = response.get('data', {}).get('container', {})
    fqdn_data = container_data.get('fqdn', {})
    remove_data = fqdn_data.get('removeValues', {})
    container = remove_data.get('container', {})
    
    if not container:
        print("❌ FQDN removal failed - no container data returned")
        print("The container may not exist or you may not have permission to modify it.")
        print("The FQDNs may not exist in the container.")
        return False
    
    print("\n✅ FQDNs removed successfully!\n")
    print("-" * 60)
    print(f"Container:   {container.get('name', 'N/A')}")
    print(f"ID:          {container.get('id', 'N/A')}")
    print(f"Description: {container.get('description', 'N/A')}")
    print(f"Size:        {container.get('size', 0)} items")
    print(f"Type:        {container.get('__typename', 'N/A')}")
    
    # Show the FQDNs that were removed
    print(f"Removed FQDNs ({len(fqdns)}):")
    for i, fqdn in enumerate(fqdns, 1):
        print(f"  {i:2d}. {fqdn}")
    
    # Show cache status
    if cache_removed_count > 0:
        print(f"Cache:       ✅ Removed {cache_removed_count} items from local cache")
    else:
        print(f"Cache:       ℹ️  None of these FQDNs were in local cache")
    
    audit = container.get('audit', {})
    if audit:
        print(f"Created:     {format_datetime(audit.get('createdAt'))} by {audit.get('createdBy', 'N/A')}")
        if audit.get('lastModifiedAt'):
            print(f"Modified:    {format_datetime(audit.get('lastModifiedAt'))} by {audit.get('lastModifiedBy', 'N/A')}")
    
    print("-" * 60)
    print(f"\n💡 Successfully removed {len(fqdns)} FQDN(s) from the container.")
    
    return True


def print_json(response, fqdns, cache_removed_count):
    """Print full response as formatted JSON with cache info"""
    output = {
        "api_response": response,
        "removed_fqdns": fqdns,
        "removed_count": len(fqdns),
        "cache_removed_count": cache_removed_count
    }
    print(json.dumps(output, indent=2))
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
    elif len(fqdns) > 1000:
        errors.append("Maximum 1000 FQDNs allowed per request")
    
    return errors


def main():
    parser = argparse.ArgumentParser(
        description='Remove FQDNs from an existing container in Cato Networks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This removes FQDNs from an existing FQDN container in your Cato account.
It will also remove the FQDNs from the local cache if present.
Environment variables can be set in a .env file in the parent directory.
See .env.example for a template.

⚠️  WARNING: This will modify an existing container in your Cato account.
Make sure you have the necessary permissions before running this command.

FQDN Examples:
  - Single domain:    --fqdns "example.com"
  - Multiple domains: --fqdns "site1.com,site2.net,blog.example.org"
  - From file:        --fqdns-file ./domains_to_remove.txt
  
File Format (one FQDN per line):
  example.com
  subdomain.example.org
  # Comments start with # and are ignored
  api.service.com
        """
    )
    
    parser.add_argument('--container', required=True, help='Container name to remove FQDNs from (required)')
    
    # Mutually exclusive group for FQDN input
    fqdn_group = parser.add_mutually_exclusive_group(required=True)
    fqdn_group.add_argument('--fqdns', help='Comma-separated FQDNs to remove')
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
    
    container_name = args.container.strip()
    
    try:
        # Parse FQDNs from input
        fqdns = parse_fqdns(args.fqdns, args.fqdns_file)
        
        # Validate inputs
        validation_errors = validate_inputs(container_name, fqdns)
        if validation_errors:
            print("❌ Validation errors:", file=sys.stderr)
            for error in validation_errors:
                print(f"  - {error}", file=sys.stderr)
            sys.exit(1)
        
        print(f"Parsed {len(fqdns)} unique FQDN(s) to remove:")
        for i, fqdn in enumerate(fqdns, 1):
            print(f"  {i:2d}. {fqdn}")
        print()
        
        # Initialize API with CLI args taking precedence over env vars
        api = API(
            key=args.key,
            account_id=args.account,
            url=args.url,
            debug=args.debug
        )
        
        # Check which FQDNs are in cache before removal
        cache_fqdns_present = 0
        if api._cache:
            for fqdn in fqdns:
                if api._cache.has_fqdn(container_name, fqdn):
                    cache_fqdns_present += 1
        
        print(f"Removing {len(fqdns)} FQDN(s) from container '{container_name}'...")
        
        # Remove the FQDNs from the container (API call also removes from cache)
        response = api.container_remove_fqdns(
            container_name=container_name,
            fqdns=fqdns
        )
        
        # Format and print output
        if args.format == 'json':
            success = print_json(response, fqdns, cache_fqdns_present)
        else:
            success = print_simple(response, container_name, fqdns, cache_fqdns_present)
        
        if not success:
            sys.exit(1)
            
    except ValueError as e:
        print(f"❌ Input error: {e}", file=sys.stderr)
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
                        print(f"  ℹ️  Or some FQDNs may not exist in the container", file=sys.stderr)
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