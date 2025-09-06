# Cato Networks API Wrapper

> **⚠️ DISCLAIMER:** This is an unofficial, community-developed wrapper for the Cato Networks API. It is not affiliated with, endorsed by, or supported by Cato Networks. For official tools and support, please contact Cato Networks directly.

A simple Python wrapper for the Cato Networks GraphQL API that provides easy-to-use methods for container management operations.

## Features

- ✅ Simple, lightweight wrapper with minimal dependencies
- ✅ Comprehensive error handling with custom exception classes
- ✅ Debug mode for API request/response inspection
- ✅ Full container lifecycle management (create, list, delete)
- ✅ Support for both IP address and FQDN containers
- ✅ **Value management** - add and remove IP ranges and FQDNs with cache synchronization
- ✅ **Container content inspection** - view individual items in containers with cache timestamps
- ✅ **SQLite caching layer** with timestamp tracking and duplicate detection
- ✅ **Smart API optimization** - cache hits skip redundant API calls
- ✅ **Cache management utilities** - view, purge, and maintain cached data
- ✅ **Enhanced container listing** with cache status information
- ✅ **Write-through caching** - container creation immediately updates cache
- ✅ Extensive test coverage with pytest (70+ tests)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd catnap
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your credentials (choose one method):

   **Option A: Environment variables**
   ```bash
   export CATO_API_KEY="your-api-key"
   export CATO_ACCOUNT_ID="your-account-id"
   ```

   **Option B: .env file**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

## Quick Start

```python
from cato import API

# Initialize API with caching enabled (default)
api = API()

# Or provide credentials directly
api = API(key="your-api-key", account_id="your-account-id")

# List containers (includes cache information)
containers = api.container_list()

# Create an IP container with initial addresses
response = api.container_create_ip(
    name="Blocked IPs",
    description="IP addresses to block",
    ip_addresses=["192.168.1.0/24", "10.0.0.1", "172.16.0.0/16"]
)

# Add IP range - first call hits API, subsequent calls use cache
api.container_add_ip_range(
    container_name="Blocked IPs",
    from_ip="203.0.113.1",
    to_ip="203.0.113.100"
)

# Adding same range again - cache hit, no API call!
api.container_add_ip_range(
    container_name="Blocked IPs", 
    from_ip="203.0.113.1",
    to_ip="203.0.113.100"
)

# Remove IP range - also removes from cache
api.container_remove_ip_range(
    container_name="Blocked IPs",
    from_ip="203.0.113.1", 
    to_ip="203.0.113.100"
)

# View cached values with timestamps
cached_data = api.container_list_cached_values("Blocked IPs")

# Get cache statistics
stats = api.container_cache_stats("Blocked IPs")

# Purge old entries (older than 30 days)
purged = api.container_purge_stale("Blocked IPs", max_age_days=30)

# Initialize with cache disabled if needed
api_no_cache = API(cache_enabled=False)
```

## API Reference

### Container Management

#### `container_list(account_id=None)`
List all containers in your Cato account, augmented with cache information when caching is enabled.

**Returns:** Dictionary with container list data, including cache statistics for each container

**Cache Enhancement:** Each container includes a `cache` object with:
- `cached`: Boolean indicating if container has cached entries
- `cached_ip_ranges`: Number of cached IP ranges
- `cached_fqdns`: Number of cached FQDNs  
- `total_cached`: Total cached entries
- `last_sync`: Timestamp of last cache update (if available)

#### `container_create_ip(name, description, ip_addresses=None, account_id=None)`
Create an IP address container.

**Parameters:**
- `name` (str): Container name
- `description` (str): Container description  
- `ip_addresses` (list, optional): List of IP addresses/ranges to add initially
- `account_id` (str, optional): Account ID (uses default if not provided)

**Returns:** Dictionary with creation response data

#### `container_create_fqdn(name, description, fqdns=None, account_id=None)`
Create an FQDN (Fully Qualified Domain Name) container.

**Parameters:**
- `name` (str): Container name
- `description` (str): Container description
- `fqdns` (list, optional): List of FQDNs to add initially
- `account_id` (str, optional): Account ID (uses default if not provided)

**Returns:** Dictionary with creation response data

#### `container_add_ip_range(container_name, from_ip, to_ip, account_id=None)`
Add an IP address range to an existing IP container with intelligent caching.

**Parameters:**
- `container_name` (str): Name of the container to add IPs to
- `from_ip` (str): Starting IP address of the range
- `to_ip` (str): Ending IP address of the range  
- `account_id` (str, optional): Account ID (uses default if not provided)

**Returns:** Dictionary with API response

**Cache Behavior:** If the IP range is already cached, updates timestamp and skips API call

#### `container_add_fqdns(container_name, fqdns, account_id=None)`
Add FQDNs to an existing FQDN container with smart filtering.

**Parameters:**
- `container_name` (str): Name of the container to add FQDNs to
- `fqdns` (list): List of FQDNs to add to the container
- `account_id` (str, optional): Account ID (uses default if not provided)

**Returns:** Dictionary with API response

**Cache Behavior:** Filters out already cached FQDNs, only sending new ones to API for efficiency

#### `container_remove_ip_range(container_name, from_ip, to_ip, account_id=None)`
Remove an IP address range from an existing IP container with cache synchronization.

**Parameters:**
- `container_name` (str): Name of the container to remove IPs from
- `from_ip` (str): Starting IP address of the range to remove
- `to_ip` (str): Ending IP address of the range to remove
- `account_id` (str, optional): Account ID (uses default if not provided)

**Returns:** Dictionary with API response

**Cache Behavior:** Removes the IP range from cache when API operation succeeds

#### `container_remove_fqdns(container_name, fqdns, account_id=None)`
Remove FQDNs from an existing FQDN container with cache synchronization.

**Parameters:**
- `container_name` (str): Name of the container to remove FQDNs from
- `fqdns` (list): List of FQDNs to remove from the container
- `account_id` (str, optional): Account ID (uses default if not provided)

**Returns:** Dictionary with API response

**Cache Behavior:** Removes FQDNs from cache when API operation succeeds

#### `container_delete(name, account_id=None)`
Delete a container by name.

**Parameters:**
- `name` (str): Container name to delete
- `account_id` (str, optional): Account ID (uses default if not provided)

**Returns:** Dictionary with deletion response data

### Cache Management

The wrapper includes powerful cache management capabilities to optimize API usage and provide visibility into cached data.

#### `container_list_cached_values(container_name)`
List all cached values for a container with timestamps.

**Parameters:**
- `container_name` (str): Name of the container

**Returns:** Dictionary with cached IP ranges and/or FQDNs, including timestamps

#### `container_cache_stats(container_name=None)`
Get cache statistics for one or all containers.

**Parameters:**
- `container_name` (str, optional): Container name for specific stats, or None for global stats

**Returns:** Dictionary with cache statistics including entry counts and sync times

#### `container_purge_stale(container_name, max_age_days=30)`
Remove cached entries older than specified days.

**Parameters:**
- `container_name` (str): Name of the container
- `max_age_days` (int): Maximum age in days (default: 30)

**Returns:** Dictionary with number of deleted entries

#### `container_clear_cache(container_name)`
Clear all cached entries for a container.

**Parameters:**
- `container_name` (str): Name of the container

**Returns:** Dictionary with number of deleted entries

### Error Handling

The API uses custom exception classes for better error handling:

- `CatoAPIError`: Base exception for all API errors
- `CatoNetworkError`: Network/connection errors (inherits from CatoAPIError)
- `CatoGraphQLError`: GraphQL API errors with detailed error information

```python
from cato import API, CatoNetworkError, CatoGraphQLError

try:
    api = API()
    result = api.container_list()
except CatoNetworkError as e:
    print(f"Network error: {e}")
except CatoGraphQLError as e:
    print(f"API error: {e}")
    print(f"Errors: {e.errors}")
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `CATO_API_KEY` | Your Cato API key | Yes |
| `CATO_ACCOUNT_ID` | Your Cato account ID | Yes |
| `CATO_API_URL` | API endpoint URL | No (defaults to Cato's endpoint) |
| `CATO_DEBUG` | Enable debug mode (`true`/`false`) | No |
| `CATO_CACHE_ENABLED` | Enable/disable cache (`true`/`false`) | No (default: true) |
| `CATO_CACHE_PATH` | Custom cache database path | No (default: ~/.cato_cache.db) |

## Example Scripts

The `examples/` directory contains ready-to-use CLI scripts:

### List Containers (Enhanced with Cache Info)
```bash
# Default format with cache information
python examples/list_containers.py

# Table format - great for viewing cache status at a glance
python examples/list_containers.py --format table

# JSON format includes full cache data
python examples/list_containers.py --format json

# Disable cache to see containers without cache information
python examples/list_containers.py --no-cache
```

### Create IP Container
```bash
# Empty container
python examples/create_ip_container.py --name "Blocked IPs" --description "IPs to block"

# With initial IPs  
python examples/create_ip_container.py --name "Allowed IPs" --description "Whitelisted IPs" \
    --ips "192.168.1.0/24,10.0.0.1"
```

### Add IP Range to Container
```bash
# Add a single IP address
python examples/add_ip_range.py --container "Blocked IPs" --from-ip "192.168.1.100" --to-ip "192.168.1.100"

# Add an IP range
python examples/add_ip_range.py --container "Allowed IPs" --from-ip "10.0.0.1" --to-ip "10.0.0.255"
```

### Add FQDNs to Container
```bash
# Add multiple FQDNs
python examples/add_fqdns.py --container "Blocked Domains" --fqdns "malware.com,phishing.net"

# Add from file
python examples/add_fqdns.py --container "Corporate Domains" --fqdns-file ./domains.txt
```

### Remove IP Range from Container
```bash
# Remove a single IP address
python examples/remove_ip_range.py --container "Blocked IPs" --from-ip "192.168.1.100" --to-ip "192.168.1.100"

# Remove an IP range
python examples/remove_ip_range.py --container "Allowed IPs" --from-ip "10.0.0.1" --to-ip "10.0.0.255"
```

### Remove FQDNs from Container
```bash
# Remove multiple FQDNs
python examples/remove_fqdns.py --container "Blocked Domains" --fqdns "malware.com,phishing.net"

# Remove from file
python examples/remove_fqdns.py --container "Corporate Domains" --fqdns-file ./domains_to_remove.txt
```

### List Container Contents with Cache Information
```bash
# Show contents of a specific container with cache status
python examples/list_container.py --name "My Container"

# Table format for better readability
python examples/list_container.py --name "Blocked IPs" --format table

# JSON output for scripting
python examples/list_container.py --name "Corporate Domains" --format json

# Disable cache to see container info only
python examples/list_container.py --name "Test Container" --no-cache
```

### Create FQDN Container  
```bash
# With initial FQDNs
python examples/create_fqdn_container.py --name "Blocked Domains" --description "Domains to block" \
    --fqdns "example.com,malware.badsite.com"

# From file
python examples/create_fqdn_container.py --name "Corporate Domains" --description "Internal domains" \
    --fqdns-file ./domains.txt
```

### Delete Container
```bash
# With confirmation
python examples/delete_container.py --name "Test Container"

# Skip confirmation  
python examples/delete_container.py --name "Test Container" --force
```

### Cache Management Examples
```bash
# Interactive cache demonstration with performance comparison
python examples/cache_demo.py

# Cache maintenance utility
python examples/cache_maintenance.py stats  # Global cache stats
python examples/cache_maintenance.py stats --container "My Container"  # Specific container
python examples/cache_maintenance.py list --container "My Container"   # List cached values
python examples/cache_maintenance.py purge --container "My Container" --days 30  # Purge old entries
python examples/cache_maintenance.py clear --container "My Container"  # Clear all cache
```

All scripts support:
- `--debug` flag for troubleshooting
- `--key`, `--account`, `--url` to override environment variables
- `--format json` for machine-readable output
- Cache-related scripts support `--no-cache` to disable caching

## Cache System

The wrapper includes a powerful SQLite-based caching system that provides significant benefits:

### Benefits
- **Performance**: Cache hits avoid redundant API calls, improving speed
- **API Efficiency**: Only new values are sent to the API, reducing bandwidth
- **Timestamp Tracking**: Know exactly when entries were added and last seen
- **Stale Data Management**: Automatically identify and purge old entries
- **Offline Visibility**: View cached container contents without API calls

### How It Works
1. **Transparent Operation**: Works automatically when enabled (default)
2. **Duplicate Detection**: Automatically skips adding duplicate entries
3. **Smart FQDN Handling**: Filters out cached FQDNs, only sends new ones
4. **Remove Synchronization**: Remove operations delete entries from cache
5. **Write-Through Caching**: Container creation immediately updates cache
6. **Timestamp Management**: Tracks both addition and last-seen timestamps
7. **Container List Enhancement**: Shows cache status for each container
8. **Content Inspection**: View individual container items with cache timestamps

### Cache Configuration
```python
# Cache enabled by default
api = API()

# Explicitly enable with custom path
api = API(cache_enabled=True, cache_path="/custom/cache.db")

# Disable caching
api = API(cache_enabled=False)
```

### Cache Files
- **Default location**: `~/.cato_cache.db`
- **Customizable**: Set via `CATO_CACHE_PATH` environment variable
- **SQLite format**: Standard SQLite database, can be inspected with any SQLite tool

## Debug Mode

Enable debug mode to see raw API requests and responses:

```python
# Via constructor
api = API(debug=True)

# Via environment variable
export CATO_DEBUG=true
```

Debug output includes:
- Request headers (with API key masked)
- Request body (JSON or multipart)
- Response status and body
- Error details with full tracebacks

## Testing

Run the test suite:

```bash
# Run all tests
python -m pytest test_cato.py test_cache.py -v

# Run specific test classes
python -m pytest test_cato.py::TestContainerList -v
python -m pytest test_cache.py::TestIPRangeCache -v
python -m pytest test_cato.py::TestAPICache -v

# Run integration tests (requires .env with credentials)
python -m pytest test_cato.py::TestIntegration -v
```

The comprehensive test suite includes:
- **70+ tests** covering all functionality including remove operations
- Unit tests with mocked API calls
- **Cache functionality tests** (cache.py and API integration)
- Multipart upload tests  
- Integration tests with real API calls
- Exception handling tests
- **Container lifecycle tests** with create, add, remove, delete operations
- **Cache performance and behavior tests**
- **Cache synchronization tests** ensuring add/remove operations maintain cache accuracy

## Requirements

- Python 3.7+
- Dependencies (see `requirements.txt`):
  - `python-dotenv` - Environment variable loading
  - `certifi` - SSL certificate verification
  - `pytest` - Testing framework (dev dependency)
  - `pytest-mock` - Test mocking (dev dependency)
