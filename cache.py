"""
cache.py

SQLite-based cache for tracking container values with timestamps.
"""

import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime


class Cache:
    """
    SQLite-based cache for tracking IP ranges and FQDNs added to containers.
    Provides timestamp tracking and duplicate detection to minimize API calls.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the cache database.
        
        Args:
            db_path: Path to SQLite database file. Defaults to ~/.cato_cache.db
        """
        if db_path is None:
            db_path = Path.home() / '.cato_cache.db'
        else:
            db_path = Path(db_path)
        
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        self._init_schema()
    
    def _init_schema(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # IP ranges table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ip_ranges (
                container_name TEXT NOT NULL,
                from_ip TEXT NOT NULL,
                to_ip TEXT NOT NULL,
                added_timestamp INTEGER NOT NULL,
                last_seen_timestamp INTEGER NOT NULL,
                PRIMARY KEY (container_name, from_ip, to_ip)
            )
        """)
        
        # FQDNs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fqdns (
                container_name TEXT NOT NULL,
                fqdn TEXT NOT NULL,
                added_timestamp INTEGER NOT NULL,
                last_seen_timestamp INTEGER NOT NULL,
                PRIMARY KEY (container_name, fqdn)
            )
        """)
        
        # Container metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS containers (
                name TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                last_sync_timestamp INTEGER,
                api_size INTEGER
            )
        """)
        
        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ip_ranges_container 
            ON ip_ranges(container_name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fqdns_container 
            ON fqdns(container_name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ip_ranges_timestamp 
            ON ip_ranges(last_seen_timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fqdns_timestamp 
            ON fqdns(last_seen_timestamp)
        """)
        
        self.conn.commit()
    
    def has_ip_range(self, container_name: str, from_ip: str, to_ip: str) -> bool:
        """
        Check if an IP range exists in the cache.
        
        Args:
            container_name: Name of the container
            from_ip: Starting IP address
            to_ip: Ending IP address
            
        Returns:
            True if the IP range exists in cache, False otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 1 FROM ip_ranges 
            WHERE container_name = ? AND from_ip = ? AND to_ip = ?
        """, (container_name, from_ip, to_ip))
        
        return cursor.fetchone() is not None
    
    def add_ip_range(self, container_name: str, from_ip: str, to_ip: str):
        """
        Add or update an IP range in the cache.
        
        Args:
            container_name: Name of the container
            from_ip: Starting IP address
            to_ip: Ending IP address
        """
        now = int(time.time())
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO ip_ranges (container_name, from_ip, to_ip, added_timestamp, last_seen_timestamp)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(container_name, from_ip, to_ip) 
            DO UPDATE SET last_seen_timestamp = ?
        """, (container_name, from_ip, to_ip, now, now, now))
        
        self.conn.commit()
    
    def remove_ip_range(self, container_name: str, from_ip: str, to_ip: str) -> bool:
        """
        Remove an IP range from the cache.
        
        Args:
            container_name: Name of the container
            from_ip: Starting IP address
            to_ip: Ending IP address
            
        Returns:
            True if the IP range was removed, False if it didn't exist
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM ip_ranges 
            WHERE container_name = ? AND from_ip = ? AND to_ip = ?
        """, (container_name, from_ip, to_ip))
        
        deleted = cursor.rowcount > 0
        self.conn.commit()
        return deleted
    
    def update_ip_timestamp(self, container_name: str, from_ip: str, to_ip: str):
        """
        Update the last_seen_timestamp for an IP range.
        
        Args:
            container_name: Name of the container
            from_ip: Starting IP address
            to_ip: Ending IP address
        """
        now = int(time.time())
        cursor = self.conn.cursor()
        
        cursor.execute("""
            UPDATE ip_ranges 
            SET last_seen_timestamp = ?
            WHERE container_name = ? AND from_ip = ? AND to_ip = ?
        """, (now, container_name, from_ip, to_ip))
        
        self.conn.commit()
    
    def has_fqdn(self, container_name: str, fqdn: str) -> bool:
        """
        Check if an FQDN exists in the cache.
        
        Args:
            container_name: Name of the container
            fqdn: Fully qualified domain name
            
        Returns:
            True if the FQDN exists in cache, False otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 1 FROM fqdns 
            WHERE container_name = ? AND fqdn = ?
        """, (container_name, fqdn))
        
        return cursor.fetchone() is not None
    
    def add_fqdn(self, container_name: str, fqdn: str):
        """
        Add or update an FQDN in the cache.
        
        Args:
            container_name: Name of the container
            fqdn: Fully qualified domain name
        """
        now = int(time.time())
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO fqdns (container_name, fqdn, added_timestamp, last_seen_timestamp)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(container_name, fqdn) 
            DO UPDATE SET last_seen_timestamp = ?
        """, (container_name, fqdn, now, now, now))
        
        self.conn.commit()
    
    def remove_fqdn(self, container_name: str, fqdn: str) -> bool:
        """
        Remove an FQDN from the cache.
        
        Args:
            container_name: Name of the container
            fqdn: Fully qualified domain name
            
        Returns:
            True if the FQDN was removed, False if it didn't exist
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM fqdns 
            WHERE container_name = ? AND fqdn = ?
        """, (container_name, fqdn))
        
        deleted = cursor.rowcount > 0
        self.conn.commit()
        return deleted
    
    def update_fqdn_timestamp(self, container_name: str, fqdn: str):
        """
        Update the last_seen_timestamp for an FQDN.
        
        Args:
            container_name: Name of the container
            fqdn: Fully qualified domain name
        """
        now = int(time.time())
        cursor = self.conn.cursor()
        
        cursor.execute("""
            UPDATE fqdns 
            SET last_seen_timestamp = ?
            WHERE container_name = ? AND fqdn = ?
        """, (now, container_name, fqdn))
        
        self.conn.commit()
    
    def get_container_ip_ranges(self, container_name: str) -> List[Dict]:
        """
        Get all cached IP ranges for a container.
        
        Args:
            container_name: Name of the container
            
        Returns:
            List of dictionaries with IP range data and timestamps
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT from_ip, to_ip, added_timestamp, last_seen_timestamp
            FROM ip_ranges
            WHERE container_name = ?
            ORDER BY last_seen_timestamp DESC
        """, (container_name,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'from_ip': row['from_ip'],
                'to_ip': row['to_ip'],
                'added': datetime.fromtimestamp(row['added_timestamp']).isoformat(),
                'last_seen': datetime.fromtimestamp(row['last_seen_timestamp']).isoformat(),
                'added_timestamp': row['added_timestamp'],
                'last_seen_timestamp': row['last_seen_timestamp']
            })
        
        return results
    
    def get_container_fqdns(self, container_name: str) -> List[Dict]:
        """
        Get all cached FQDNs for a container.
        
        Args:
            container_name: Name of the container
            
        Returns:
            List of dictionaries with FQDN data and timestamps
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT fqdn, added_timestamp, last_seen_timestamp
            FROM fqdns
            WHERE container_name = ?
            ORDER BY last_seen_timestamp DESC
        """, (container_name,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'fqdn': row['fqdn'],
                'added': datetime.fromtimestamp(row['added_timestamp']).isoformat(),
                'last_seen': datetime.fromtimestamp(row['last_seen_timestamp']).isoformat(),
                'added_timestamp': row['added_timestamp'],
                'last_seen_timestamp': row['last_seen_timestamp']
            })
        
        return results
    
    def purge_stale_ip_ranges(self, container_name: str, max_age_days: int = 30) -> int:
        """
        Remove IP ranges older than specified days.
        
        Args:
            container_name: Name of the container
            max_age_days: Maximum age in days
            
        Returns:
            Number of entries removed
        """
        cutoff_timestamp = int(time.time()) - (max_age_days * 86400)
        cursor = self.conn.cursor()
        
        cursor.execute("""
            DELETE FROM ip_ranges
            WHERE container_name = ? AND last_seen_timestamp < ?
        """, (container_name, cutoff_timestamp))
        
        deleted = cursor.rowcount
        self.conn.commit()
        
        return deleted
    
    def purge_stale_fqdns(self, container_name: str, max_age_days: int = 30) -> int:
        """
        Remove FQDNs older than specified days.
        
        Args:
            container_name: Name of the container
            max_age_days: Maximum age in days
            
        Returns:
            Number of entries removed
        """
        cutoff_timestamp = int(time.time()) - (max_age_days * 86400)
        cursor = self.conn.cursor()
        
        cursor.execute("""
            DELETE FROM fqdns
            WHERE container_name = ? AND last_seen_timestamp < ?
        """, (container_name, cutoff_timestamp))
        
        deleted = cursor.rowcount
        self.conn.commit()
        
        return deleted
    
    def get_container_type(self, container_name: str) -> Optional[str]:
        """
        Get the type of a container from cache metadata.
        
        Args:
            container_name: Name of the container
            
        Returns:
            'ip' or 'fqdn' or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT type FROM containers WHERE name = ?
        """, (container_name,))
        
        row = cursor.fetchone()
        return row['type'] if row else None
    
    def update_container_metadata(self, container_name: str, container_type: str, api_size: Optional[int] = None):
        """
        Update container metadata in cache.
        
        Args:
            container_name: Name of the container
            container_type: 'ip' or 'fqdn'
            api_size: Size reported by API
        """
        now = int(time.time())
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO containers (name, type, last_sync_timestamp, api_size)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) 
            DO UPDATE SET last_sync_timestamp = ?, api_size = ?
        """, (container_name, container_type, now, api_size, now, api_size))
        
        self.conn.commit()
    
    def get_stats(self, container_name: Optional[str] = None) -> Dict:
        """
        Get cache statistics.
        
        Args:
            container_name: Optional container name for specific stats
            
        Returns:
            Dictionary with cache statistics
        """
        cursor = self.conn.cursor()
        
        if container_name:
            # Stats for specific container
            cursor.execute("""
                SELECT COUNT(*) as count FROM ip_ranges WHERE container_name = ?
            """, (container_name,))
            ip_count = cursor.fetchone()['count']
            
            cursor.execute("""
                SELECT COUNT(*) as count FROM fqdns WHERE container_name = ?
            """, (container_name,))
            fqdn_count = cursor.fetchone()['count']
            
            cursor.execute("""
                SELECT type, api_size, last_sync_timestamp 
                FROM containers WHERE name = ?
            """, (container_name,))
            metadata = cursor.fetchone()
            
            stats = {
                'container': container_name,
                'cached_ip_ranges': ip_count,
                'cached_fqdns': fqdn_count,
                'total_cached': ip_count + fqdn_count
            }
            
            if metadata:
                stats['type'] = metadata['type']
                stats['api_size'] = metadata['api_size']
                if metadata['last_sync_timestamp']:
                    stats['last_sync'] = datetime.fromtimestamp(metadata['last_sync_timestamp']).isoformat()
            
            return stats
        else:
            # Global stats
            cursor.execute("SELECT COUNT(*) as count FROM ip_ranges")
            total_ip = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM fqdns")
            total_fqdn = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM containers")
            total_containers = cursor.fetchone()['count']
            
            cursor.execute("""
                SELECT COUNT(DISTINCT container_name) as count FROM ip_ranges
            """)
            ip_containers = cursor.fetchone()['count']
            
            cursor.execute("""
                SELECT COUNT(DISTINCT container_name) as count FROM fqdns
            """)
            fqdn_containers = cursor.fetchone()['count']
            
            return {
                'total_cached_ip_ranges': total_ip,
                'total_cached_fqdns': total_fqdn,
                'total_cached_entries': total_ip + total_fqdn,
                'tracked_containers': total_containers,
                'containers_with_ips': ip_containers,
                'containers_with_fqdns': fqdn_containers,
                'cache_file': self.db_path
            }
    
    def clear_container(self, container_name: str) -> Tuple[int, int]:
        """
        Clear all cached entries for a container.
        
        Args:
            container_name: Name of the container
            
        Returns:
            Tuple of (deleted_ip_ranges, deleted_fqdns)
        """
        cursor = self.conn.cursor()
        
        cursor.execute("DELETE FROM ip_ranges WHERE container_name = ?", (container_name,))
        deleted_ip = cursor.rowcount
        
        cursor.execute("DELETE FROM fqdns WHERE container_name = ?", (container_name,))
        deleted_fqdn = cursor.rowcount
        
        cursor.execute("DELETE FROM containers WHERE name = ?", (container_name,))
        
        self.conn.commit()
        
        return (deleted_ip, deleted_fqdn)
    
    def close(self):
        """Close the database connection."""
        self.conn.close()