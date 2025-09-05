#!/usr/bin/env python3
"""
cache_maintenance.py

Utility script for managing the Cato API cache. Provides commands for
viewing, cleaning, and maintaining cached data.
"""

import argparse
import os
import sys
from datetime import datetime
# Add parent directory to path to import cato module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cato import API


def format_timestamp(iso_string):
    """Format ISO timestamp string for display"""
    return datetime.fromisoformat(iso_string).strftime('%Y-%m-%d %H:%M:%S')


def cmd_stats(api, args):
    """Show cache statistics"""
    if args.container:
        stats = api.container_cache_stats(args.container)
        print(f"=== Cache Stats for '{args.container}' ===")
        print(f"Cached IP ranges: {stats['cached_ip_ranges']}")
        print(f"Cached FQDNs: {stats['cached_fqdns']}")
        print(f"Total cached entries: {stats['total_cached']}")
        if 'type' in stats:
            print(f"Container type: {stats['type']}")
        if 'api_size' in stats:
            print(f"API reported size: {stats['api_size']}")
        if 'last_sync' in stats:
            print(f"Last sync: {stats['last_sync']}")
    else:
        stats = api.container_cache_stats()
        print("=== Global Cache Statistics ===")
        print(f"Total cached IP ranges: {stats['total_cached_ip_ranges']}")
        print(f"Total cached FQDNs: {stats['total_cached_fqdns']}")
        print(f"Total cached entries: {stats['total_cached_entries']}")
        print(f"Tracked containers: {stats['tracked_containers']}")
        print(f"Containers with IPs: {stats['containers_with_ips']}")
        print(f"Containers with FQDNs: {stats['containers_with_fqdns']}")
        print(f"Cache file: {stats['cache_file']}")


def cmd_list(api, args):
    """List cached values for a container"""
    if not args.container:
        print("Error: --container required for list command")
        return 1
    
    cached = api.container_list_cached_values(args.container)
    
    if not cached:
        print(f"No cached data found for container '{args.container}'")
        return 0
    
    print(f"=== Cached Values for '{args.container}' ===")
    
    if 'ip_ranges' in cached and cached['ip_ranges']:
        print(f"\nIP Ranges ({len(cached['ip_ranges'])}):")
        for ip_range in cached['ip_ranges']:
            print(f"  {ip_range['from_ip']} - {ip_range['to_ip']}")
            print(f"    Added: {format_timestamp(ip_range['added'])}")
            print(f"    Last seen: {format_timestamp(ip_range['last_seen'])}")
    
    if 'fqdns' in cached and cached['fqdns']:
        print(f"\nFQDNs ({len(cached['fqdns'])}):")
        for fqdn in cached['fqdns']:
            print(f"  {fqdn['fqdn']}")
            print(f"    Added: {format_timestamp(fqdn['added'])}")
            print(f"    Last seen: {format_timestamp(fqdn['last_seen'])}")
    
    return 0


def cmd_purge(api, args):
    """Purge stale entries from cache"""
    if not args.container:
        print("Error: --container required for purge command")
        return 1
    
    if not args.force:
        response = input(f"Purge entries older than {args.days} days from '{args.container}'? (y/N): ")
        if response.lower() != 'y':
            print("Purge cancelled")
            return 0
    
    purged_ip, purged_fqdn = api.container_purge_stale(args.container, args.days)
    print(f"Purged {purged_ip} IP ranges and {purged_fqdn} FQDNs older than {args.days} days")
    return 0


def cmd_clear(api, args):
    """Clear all cache entries for a container"""
    if not args.container:
        print("Error: --container required for clear command")
        return 1
    
    if not args.force:
        response = input(f"Clear ALL cached entries for '{args.container}'? This cannot be undone! (y/N): ")
        if response.lower() != 'y':
            print("Clear cancelled")
            return 0
    
    deleted_ip, deleted_fqdn = api.container_clear_cache(args.container)
    print(f"Cleared {deleted_ip} IP ranges and {deleted_fqdn} FQDNs from cache")
    return 0


def cmd_containers(api, args):
    """List all cached containers"""
    import json
    from datetime import datetime
    
    # Get all containers from cache database directly
    if not api._cache:
        print("Error: Cache is not enabled")
        return 1
    
    cursor = api._cache.conn.cursor()
    cursor.execute("""
        SELECT name, type, api_size, last_sync_timestamp,
               (SELECT COUNT(*) FROM ip_ranges WHERE container_name = containers.name) as cached_ip_ranges,
               (SELECT COUNT(*) FROM fqdns WHERE container_name = containers.name) as cached_fqdns
        FROM containers 
        ORDER BY name
    """)
    
    containers = []
    for row in cursor.fetchall():
        container_data = {
            'name': row['name'],
            'type': row['type'],
            'api_size': row['api_size'],
            'cached_ip_ranges': row['cached_ip_ranges'],
            'cached_fqdns': row['cached_fqdns'],
            'total_cached': row['cached_ip_ranges'] + row['cached_fqdns'],
            'last_sync': datetime.fromtimestamp(row['last_sync_timestamp']).isoformat() if row['last_sync_timestamp'] else None
        }
        containers.append(container_data)
    
    if not containers:
        print("No containers found in cache")
        return 0
    
    # Output in requested format
    if args.format == 'json':
        print(json.dumps(containers, indent=2))
    elif args.format == 'simple':
        print(f"=== Cached Containers ({len(containers)} total) ===")
        for container in containers:
            print(f"{container['name']} ({container['type']}) - {container['total_cached']} cached entries")
    else:  # table format
        print(f"=== Cached Containers ({len(containers)} total) ===")
        print(f"{'Name':<30} {'Type':<6} {'API Size':<8} {'Cached':<7} {'IPs':<4} {'FQDNs':<6} {'Last Sync':<19}")
        print("-" * 85)
        
        for container in containers:
            last_sync = container['last_sync'][:19] if container['last_sync'] else 'Never'
            print(f"{container['name']:<30} {container['type']:<6} {container['api_size'] or 0:<8} "
                  f"{container['total_cached']:<7} {container['cached_ip_ranges']:<4} "
                  f"{container['cached_fqdns']:<6} {last_sync:<19}")
    
    return 0


def cmd_validate(api, args):
    """Validate cache integrity against API"""
    import json
    
    print("🔍 Validating cache integrity against API...")
    print("This may take a moment as it queries the API...")
    print()
    
    try:
        validation_result = api.container_validate_cache_integrity()
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        return 1
    
    # Output results based on format
    if args.format == 'json':
        print(json.dumps(validation_result, indent=2))
        return 0 if validation_result['overall_status'] == 'PASS' else 1
    
    # Display results in human-readable format
    status_emoji = "✅" if validation_result['overall_status'] == 'PASS' else "❌"
    print(f"{status_emoji} Cache Integrity Validation: {validation_result['overall_status']}")
    print(f"Validation Time: {validation_result['timestamp']}")
    print(f"API Containers: {validation_result['api_containers_count']}")
    print(f"Cache Containers: {validation_result['cache_containers_count']}")
    print()
    
    # Check 1: API containers should exist in cache
    api_to_cache = validation_result['checks']['api_to_cache']
    check1_emoji = "✅" if api_to_cache['passed'] else "❌"
    print(f"{check1_emoji} Check 1: API containers exist in cache")
    if not api_to_cache['passed']:
        print(f"   Found {len(api_to_cache['missing_in_cache'])} containers in API but not in cache:")
        for container in api_to_cache['missing_in_cache']:
            print(f"   - {container['name']} ({container['type']}, size: {container['size']})")
    else:
        print("   All API containers found in cache")
    print()
    
    # Check 2: Cache containers should exist in API
    cache_to_api = validation_result['checks']['cache_to_api']
    check2_emoji = "✅" if cache_to_api['passed'] else "❌"
    print(f"{check2_emoji} Check 2: Cache containers exist in API")
    if not cache_to_api['passed']:
        print(f"   Found {len(cache_to_api['missing_in_api'])} containers in cache but not in API:")
        for container in cache_to_api['missing_in_api']:
            print(f"   - {container['name']} ({container['type']}, cached size: {container['size']})")
        if args.fix:
            print("   🔧 Fixing: Removing orphaned cache entries...")
            removed_count = 0
            for container in cache_to_api['missing_in_api']:
                try:
                    api.container_clear_cache(container['name'])
                    removed_count += 1
                    print(f"   ✅ Removed cache entries for: {container['name']}")
                except Exception as e:
                    print(f"   ❌ Failed to remove cache for {container['name']}: {e}")
            print(f"   Removed cache entries for {removed_count} containers")
    else:
        print("   All cache containers found in API")
    print()
    
    # Check 3: Container sizes should match
    size_consistency = validation_result['checks']['size_consistency']
    check3_emoji = "✅" if size_consistency['passed'] else "❌"
    print(f"{check3_emoji} Check 3: Container sizes match between API and cache")
    if not size_consistency['passed']:
        print(f"   Found {len(size_consistency['mismatched_sizes'])} containers with size mismatches:")
        for container in size_consistency['mismatched_sizes']:
            diff_sign = "+" if container['difference'] > 0 else ""
            print(f"   - {container['name']} ({container['type']}): API={container['api_size']}, "
                  f"Cache={container['cache_size']} (diff: {diff_sign}{container['difference']})")
    else:
        print("   All container sizes match between API and cache")
    print()
    
    # Summary
    summary = validation_result['summary']
    print("📊 Summary:")
    print(f"   Containers validated: {summary['containers_validated']}")
    print(f"   Missing in cache: {summary['containers_missing_in_cache']}")
    print(f"   Missing in API (orphaned): {summary['containers_missing_in_api']}")
    print(f"   Size mismatches: {summary['containers_with_size_mismatch']}")
    
    if validation_result['overall_status'] != 'PASS':
        print()
        print("💡 Recommendations:")
        if summary['containers_missing_in_cache'] > 0:
            print("   - Containers missing in cache will be added automatically when you interact with them")
        if summary['containers_missing_in_api'] > 0:
            print("   - Run with --fix to remove orphaned cache entries")
        if summary['containers_with_size_mismatch'] > 0:
            print("   - Size mismatches may indicate cache is out of sync - consider clearing and rebuilding cache")
    
    return 0 if validation_result['overall_status'] == 'PASS' else 1


def main():
    parser = argparse.ArgumentParser(
        description="Cato API Cache Maintenance Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show global cache statistics
  python cache_maintenance.py stats
  
  # Show cache stats for specific container
  python cache_maintenance.py stats --container "My Container"
  
  # List all cached containers
  python cache_maintenance.py containers
  python cache_maintenance.py containers --format simple
  
  # List all cached values for a container
  python cache_maintenance.py list --container "My Container"
  
  # Validate cache integrity against API
  python cache_maintenance.py validate
  python cache_maintenance.py validate --fix  # Remove orphaned cache entries
  
  # Purge entries older than 30 days
  python cache_maintenance.py purge --container "My Container" --days 30
  
  # Clear all cache entries for a container
  python cache_maintenance.py clear --container "My Container" --force
        """
    )
    
    # Global options
    parser.add_argument('--key', help='API key (overrides CATO_API_KEY env var)')
    parser.add_argument('--account', help='Account ID (overrides CATO_ACCOUNT_ID env var)')
    parser.add_argument('--url', help='API URL (overrides CATO_API_URL env var)')
    parser.add_argument('--cache-path', help='Cache file path (overrides CATO_CACHE_PATH env var)')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show cache statistics')
    stats_parser.add_argument('--container', help='Show stats for specific container')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List cached values')
    list_parser.add_argument('--container', required=True, help='Container name')
    
    # Purge command  
    purge_parser = subparsers.add_parser('purge', help='Purge stale entries')
    purge_parser.add_argument('--container', required=True, help='Container name')
    purge_parser.add_argument('--days', type=int, default=30, help='Max age in days (default: 30)')
    purge_parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')
    
    # Clear command
    clear_parser = subparsers.add_parser('clear', help='Clear all cache entries')
    clear_parser.add_argument('--container', required=True, help='Container name')
    clear_parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')
    
    # Containers command
    containers_parser = subparsers.add_parser('containers', help='List all cached containers')
    containers_parser.add_argument('--format', choices=['table', 'json', 'simple'], default='table', 
                                   help='Output format (default: table)')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate cache integrity against API')
    validate_parser.add_argument('--format', choices=['table', 'json', 'simple'], default='table',
                                help='Output format (default: table)')
    validate_parser.add_argument('--fix', action='store_true',
                                help='Attempt to fix found issues (remove orphaned cache entries)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        # Initialize API with cache enabled
        api = API(
            key=args.key,
            account_id=args.account,
            url=args.url,
            cache_enabled=True,
            cache_path=args.cache_path
        )
        
        # Route to appropriate command function
        commands = {
            'stats': cmd_stats,
            'list': cmd_list,
            'purge': cmd_purge,
            'clear': cmd_clear,
            'containers': cmd_containers,
            'validate': cmd_validate
        }
        
        return commands[args.command](api, args)
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())