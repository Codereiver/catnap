"""
Tests for cache.py module
"""

import os
import tempfile
import time
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from cache import Cache


class TestCacheInit:
    """Test Cache initialization"""
    
    def test_init_with_default_path(self):
        """Test cache initialization with default path"""
        cache = Cache()
        expected_path = str(Path.home() / ".cato_cache.db")
        assert cache.db_path == expected_path
        cache.close()
    
    def test_init_with_custom_path(self):
        """Test cache initialization with custom path"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            cache = Cache(db_path)
            assert cache.db_path == db_path
            cache.close()
        finally:
            os.unlink(db_path)
    
    def test_schema_creation(self):
        """Test that database schema is created correctly"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            cache = Cache(db_path)
            cursor = cache.conn.cursor()
            
            # Check tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            
            assert 'ip_ranges' in tables
            assert 'fqdns' in tables
            assert 'containers' in tables
            
            cache.close()
        finally:
            os.unlink(db_path)


class TestIPRangeCache:
    """Test IP range caching functionality"""
    
    @pytest.fixture
    def cache(self):
        """Create a temporary cache for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        cache = Cache(db_path)
        yield cache
        cache.close()
        os.unlink(db_path)
    
    def test_add_ip_range(self, cache):
        """Test adding an IP range to cache"""
        cache.add_ip_range("Test Container", "192.168.1.1", "192.168.1.10")
        
        assert cache.has_ip_range("Test Container", "192.168.1.1", "192.168.1.10")
        assert not cache.has_ip_range("Test Container", "192.168.1.1", "192.168.1.20")
        assert not cache.has_ip_range("Other Container", "192.168.1.1", "192.168.1.10")
    
    def test_update_ip_timestamp(self, cache):
        """Test updating timestamp for existing IP range"""
        cache.add_ip_range("Test Container", "10.0.0.1", "10.0.0.10")
        
        # Get initial timestamp
        ranges = cache.get_container_ip_ranges("Test Container")
        initial_timestamp = ranges[0]['last_seen_timestamp']
        
        # Wait a bit and update
        time.sleep(1.1)
        cache.update_ip_timestamp("Test Container", "10.0.0.1", "10.0.0.10")
        
        # Check timestamp was updated
        ranges = cache.get_container_ip_ranges("Test Container")
        new_timestamp = ranges[0]['last_seen_timestamp']
        
        assert new_timestamp > initial_timestamp
    
    def test_get_container_ip_ranges(self, cache):
        """Test retrieving IP ranges for a container"""
        cache.add_ip_range("Test Container", "192.168.1.1", "192.168.1.10")
        cache.add_ip_range("Test Container", "10.0.0.1", "10.0.0.255")
        cache.add_ip_range("Other Container", "172.16.0.1", "172.16.0.100")
        
        ranges = cache.get_container_ip_ranges("Test Container")
        
        assert len(ranges) == 2
        assert any(r['from_ip'] == "192.168.1.1" and r['to_ip'] == "192.168.1.10" for r in ranges)
        assert any(r['from_ip'] == "10.0.0.1" and r['to_ip'] == "10.0.0.255" for r in ranges)
        
        # Check timestamps are included
        for r in ranges:
            assert 'added' in r
            assert 'last_seen' in r
            assert 'added_timestamp' in r
            assert 'last_seen_timestamp' in r
    
    def test_purge_stale_ip_ranges(self, cache):
        """Test purging old IP ranges"""
        now = int(time.time())
        old_timestamp = now - (35 * 86400)  # 35 days ago
        
        # Add IP ranges with different timestamps
        cursor = cache.conn.cursor()
        cursor.execute("""
            INSERT INTO ip_ranges (container_name, from_ip, to_ip, added_timestamp, last_seen_timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, ("Test Container", "192.168.1.1", "192.168.1.10", old_timestamp, old_timestamp))
        
        cache.add_ip_range("Test Container", "10.0.0.1", "10.0.0.10")  # Recent
        cache.conn.commit()
        
        # Purge entries older than 30 days
        deleted = cache.purge_stale_ip_ranges("Test Container", 30)
        
        assert deleted == 1
        assert not cache.has_ip_range("Test Container", "192.168.1.1", "192.168.1.10")
        assert cache.has_ip_range("Test Container", "10.0.0.1", "10.0.0.10")


class TestFQDNCache:
    """Test FQDN caching functionality"""
    
    @pytest.fixture
    def cache(self):
        """Create a temporary cache for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        cache = Cache(db_path)
        yield cache
        cache.close()
        os.unlink(db_path)
    
    def test_add_fqdn(self, cache):
        """Test adding an FQDN to cache"""
        cache.add_fqdn("Test Container", "example.com")
        
        assert cache.has_fqdn("Test Container", "example.com")
        assert not cache.has_fqdn("Test Container", "other.com")
        assert not cache.has_fqdn("Other Container", "example.com")
    
    def test_update_fqdn_timestamp(self, cache):
        """Test updating timestamp for existing FQDN"""
        cache.add_fqdn("Test Container", "example.com")
        
        # Get initial timestamp
        fqdns = cache.get_container_fqdns("Test Container")
        initial_timestamp = fqdns[0]['last_seen_timestamp']
        
        # Wait a bit and update
        time.sleep(1.1)
        cache.update_fqdn_timestamp("Test Container", "example.com")
        
        # Check timestamp was updated
        fqdns = cache.get_container_fqdns("Test Container")
        new_timestamp = fqdns[0]['last_seen_timestamp']
        
        assert new_timestamp > initial_timestamp
    
    def test_get_container_fqdns(self, cache):
        """Test retrieving FQDNs for a container"""
        cache.add_fqdn("Test Container", "example.com")
        cache.add_fqdn("Test Container", "api.example.com")
        cache.add_fqdn("Other Container", "other.com")
        
        fqdns = cache.get_container_fqdns("Test Container")
        
        assert len(fqdns) == 2
        assert any(f['fqdn'] == "example.com" for f in fqdns)
        assert any(f['fqdn'] == "api.example.com" for f in fqdns)
        
        # Check timestamps are included
        for f in fqdns:
            assert 'added' in f
            assert 'last_seen' in f
            assert 'added_timestamp' in f
            assert 'last_seen_timestamp' in f
    
    def test_purge_stale_fqdns(self, cache):
        """Test purging old FQDNs"""
        now = int(time.time())
        old_timestamp = now - (35 * 86400)  # 35 days ago
        
        # Add FQDNs with different timestamps
        cursor = cache.conn.cursor()
        cursor.execute("""
            INSERT INTO fqdns (container_name, fqdn, added_timestamp, last_seen_timestamp)
            VALUES (?, ?, ?, ?)
        """, ("Test Container", "old.example.com", old_timestamp, old_timestamp))
        
        cache.add_fqdn("Test Container", "new.example.com")  # Recent
        cache.conn.commit()
        
        # Purge entries older than 30 days
        deleted = cache.purge_stale_fqdns("Test Container", 30)
        
        assert deleted == 1
        assert not cache.has_fqdn("Test Container", "old.example.com")
        assert cache.has_fqdn("Test Container", "new.example.com")


class TestContainerMetadata:
    """Test container metadata functionality"""
    
    @pytest.fixture
    def cache(self):
        """Create a temporary cache for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        cache = Cache(db_path)
        yield cache
        cache.close()
        os.unlink(db_path)
    
    def test_update_container_metadata(self, cache):
        """Test updating container metadata"""
        cache.update_container_metadata("Test Container", "ip", 100)
        
        container_type = cache.get_container_type("Test Container")
        assert container_type == "ip"
        
        # Update with new size
        cache.update_container_metadata("Test Container", "ip", 150)
        
        stats = cache.get_stats("Test Container")
        assert stats['api_size'] == 150
    
    def test_get_container_type(self, cache):
        """Test getting container type"""
        cache.update_container_metadata("IP Container", "ip", 10)
        cache.update_container_metadata("FQDN Container", "fqdn", 20)
        
        assert cache.get_container_type("IP Container") == "ip"
        assert cache.get_container_type("FQDN Container") == "fqdn"
        assert cache.get_container_type("Unknown Container") is None


class TestCacheStats:
    """Test cache statistics functionality"""
    
    @pytest.fixture
    def cache(self):
        """Create a temporary cache for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        cache = Cache(db_path)
        yield cache
        cache.close()
        os.unlink(db_path)
    
    def test_container_stats(self, cache):
        """Test getting stats for a specific container"""
        cache.add_ip_range("Test Container", "192.168.1.1", "192.168.1.10")
        cache.add_ip_range("Test Container", "10.0.0.1", "10.0.0.10")
        cache.add_fqdn("Test Container", "example.com")
        cache.update_container_metadata("Test Container", "mixed", 50)
        
        stats = cache.get_stats("Test Container")
        
        assert stats['container'] == "Test Container"
        assert stats['cached_ip_ranges'] == 2
        assert stats['cached_fqdns'] == 1
        assert stats['total_cached'] == 3
        assert stats['type'] == "mixed"
        assert stats['api_size'] == 50
        assert 'last_sync' in stats
    
    def test_global_stats(self, cache):
        """Test getting global cache statistics"""
        # Add data for multiple containers
        cache.add_ip_range("Container1", "192.168.1.1", "192.168.1.10")
        cache.add_ip_range("Container2", "10.0.0.1", "10.0.0.10")
        cache.add_fqdn("Container3", "example.com")
        cache.add_fqdn("Container3", "test.com")
        
        cache.update_container_metadata("Container1", "ip", 10)
        cache.update_container_metadata("Container2", "ip", 20)
        cache.update_container_metadata("Container3", "fqdn", 30)
        
        stats = cache.get_stats()
        
        assert stats['total_cached_ip_ranges'] == 2
        assert stats['total_cached_fqdns'] == 2
        assert stats['total_cached_entries'] == 4
        assert stats['tracked_containers'] == 3
        assert stats['containers_with_ips'] == 2
        assert stats['containers_with_fqdns'] == 1
        assert 'cache_file' in stats


class TestCacheClear:
    """Test cache clearing functionality"""
    
    @pytest.fixture
    def cache(self):
        """Create a temporary cache for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        cache = Cache(db_path)
        yield cache
        cache.close()
        os.unlink(db_path)
    
    def test_clear_container(self, cache):
        """Test clearing all entries for a container"""
        # Add data
        cache.add_ip_range("Test Container", "192.168.1.1", "192.168.1.10")
        cache.add_ip_range("Test Container", "10.0.0.1", "10.0.0.10")
        cache.add_fqdn("Test Container", "example.com")
        cache.update_container_metadata("Test Container", "mixed", 50)
        
        cache.add_ip_range("Other Container", "172.16.0.1", "172.16.0.10")
        
        # Clear Test Container
        deleted_ip, deleted_fqdn = cache.clear_container("Test Container")
        
        assert deleted_ip == 2
        assert deleted_fqdn == 1
        
        # Verify Test Container is cleared
        assert not cache.has_ip_range("Test Container", "192.168.1.1", "192.168.1.10")
        assert not cache.has_fqdn("Test Container", "example.com")
        assert cache.get_container_type("Test Container") is None
        
        # Verify Other Container is not affected
        assert cache.has_ip_range("Other Container", "172.16.0.1", "172.16.0.10")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])