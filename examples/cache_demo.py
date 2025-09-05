#!/usr/bin/env python3
"""
cache_demo.py

Demonstrates the cache functionality of the Cato Networks API wrapper.
Shows how caching reduces API calls and provides additional features like
timestamp tracking and stale entry purging.
"""

import os
import sys
import time
from datetime import datetime
# Add parent directory to path to import cato module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cato import API


def main():
    # Initialize API with cache enabled
    api = API(cache_enabled=True)
    
    print("=== Cato Cache Demonstration ===\n")
    
    # Demo container name
    container_name = "Cache Demo Container"
    
    try:
        # Create a test container if it doesn't exist
        print("1. Creating demo container...")
        try:
            result = api.container_create_ip(container_name, "Demo container for cache testing")
            print(f"✓ Created container: {container_name}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"✓ Container already exists: {container_name}")
            else:
                raise
        
        # Add IP ranges with cache demonstration
        print("\n2. Adding IP ranges (first time - API calls made)...")
        start_time = time.time()
        
        api.container_add_ip_range(container_name, "192.168.1.1", "192.168.1.10")
        api.container_add_ip_range(container_name, "10.0.0.1", "10.0.0.50")
        api.container_add_ip_range(container_name, "172.16.0.1", "172.16.0.100")
        
        first_run_time = time.time() - start_time
        print(f"✓ Added 3 IP ranges in {first_run_time:.2f} seconds")
        
        # Add same IP ranges again - should hit cache
        print("\n3. Adding same IP ranges again (cache hits - no API calls)...")
        start_time = time.time()
        
        api.container_add_ip_range(container_name, "192.168.1.1", "192.168.1.10")
        api.container_add_ip_range(container_name, "10.0.0.1", "10.0.0.50")
        api.container_add_ip_range(container_name, "172.16.0.1", "172.16.0.100")
        
        second_run_time = time.time() - start_time
        print(f"✓ 'Added' 3 IP ranges in {second_run_time:.2f} seconds (cache hits)")
        print(f"✓ Speed improvement: {(first_run_time/second_run_time):.1f}x faster")
        
        # Show cached values with timestamps
        print("\n4. Viewing cached IP ranges with timestamps...")
        cached_values = api.container_list_cached_values(container_name)
        
        if cached_values and 'ip_ranges' in cached_values:
            print(f"Found {len(cached_values['ip_ranges'])} cached IP ranges:")
            for ip_range in cached_values['ip_ranges']:
                added_time = datetime.fromisoformat(ip_range['added']).strftime('%Y-%m-%d %H:%M:%S')
                last_seen_time = datetime.fromisoformat(ip_range['last_seen']).strftime('%Y-%m-%d %H:%M:%S')
                print(f"  {ip_range['from_ip']} - {ip_range['to_ip']}")
                print(f"    Added: {added_time}")
                print(f"    Last seen: {last_seen_time}")
        
        # Cache statistics
        print("\n5. Cache statistics...")
        stats = api.container_cache_stats(container_name)
        print(f"Container: {stats['container']}")
        print(f"Cached IP ranges: {stats['cached_ip_ranges']}")
        print(f"Cached FQDNs: {stats['cached_fqdns']}")
        print(f"Total cached entries: {stats['total_cached']}")
        if 'last_sync' in stats:
            print(f"Last sync: {stats['last_sync']}")
        
        # Global cache stats
        print("\n6. Global cache statistics...")
        global_stats = api.container_cache_stats()
        print(f"Total cached IP ranges: {global_stats['total_cached_ip_ranges']}")
        print(f"Total cached FQDNs: {global_stats['total_cached_fqdns']}")
        print(f"Total cached entries: {global_stats['total_cached_entries']}")
        print(f"Tracked containers: {global_stats['tracked_containers']}")
        print(f"Cache file: {global_stats['cache_file']}")
        
        # Demonstrate FQDN caching
        print("\n7. Adding FQDNs with partial caching...")
        
        # Add some FQDNs
        fqdns1 = ["example.com", "test.com", "demo.com"]
        api.container_add_fqdns(container_name, fqdns1)
        print(f"✓ Added FQDNs: {', '.join(fqdns1)}")
        
        # Add mix of new and existing FQDNs - should only send new ones to API
        fqdns2 = ["example.com", "new.com", "test.com", "another.com"]  # 2 cached, 2 new
        api.container_add_fqdns(container_name, fqdns2)
        print(f"✓ Added FQDNs: {', '.join(fqdns2)} (2 were cached, 2 sent to API)")
        
        # Show updated cache stats
        stats = api.container_cache_stats(container_name)
        print(f"✓ Now have {stats['cached_fqdns']} cached FQDNs")
        
        # Purge demonstration (simulated old entries)
        print("\n8. Purge stale entries demonstration...")
        purged = api.container_purge_stale(container_name, max_age_days=0)  # Purge everything
        print(f"✓ Purged {purged[0]} IP ranges and {purged[1]} FQDNs (using max_age_days=0 for demo)")
        
        # Show empty cache
        stats = api.container_cache_stats(container_name)
        print(f"✓ Cache now has {stats['total_cached']} entries")
        
        print("\n=== Cache Demo Complete ===")
        print("\nKey benefits of caching:")
        print("• Faster operations when adding duplicate entries")
        print("• Timestamp tracking for when entries were added/last seen")
        print("• Ability to purge stale entries")
        print("• Statistics and monitoring")
        print("• Offline access to what's been added")
        
    except Exception as e:
        print(f"Error during demo: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())