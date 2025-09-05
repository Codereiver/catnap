# Cato API Examples

This directory contains example scripts demonstrating how to use the Cato Networks API wrapper.

## Prerequisites

1. Install the required dependencies:
   ```bash
   pip install -r ../requirements.txt
   ```

2. Set up your credentials using one of these methods:
   - Create a `.env` file in the parent directory (copy from `.env.example`)
   - Export environment variables:
     ```bash
     export CATO_API_KEY="your-api-key"
     export CATO_ACCOUNT_ID="your-account-id"
     ```
   - Pass credentials as command-line arguments (see individual examples)

## Available Examples

### list_containers.py
Lists all containers in your Cato account with cache information when available.

```bash
# Use environment variables with cache enabled (default)
python examples/list_containers.py

# Override with CLI parameters
python examples/list_containers.py --key YOUR_KEY --account YOUR_ACCOUNT

# Different output formats
python examples/list_containers.py --format json
python examples/list_containers.py --format table  # Great for seeing cache info
python examples/list_containers.py --format simple  # default

# Disable cache to see containers without cache information
python examples/list_containers.py --no-cache
```

#### Output Formats:
- **simple**: Human-readable format with all details including cache information
- **table**: Compact table format with cache columns (Cached, Cache)
- **json**: Full JSON response from the API including cache data

#### Cache Information Display:
When cache is enabled (default), the output includes:
- **Cached**: Whether the container has cached entries (Yes/No)
- **Cache entries**: Number of cached IP ranges and FQDNs
- **Last sync**: When cache was last updated (if available)

#### Command-line Options:
- `--key KEY`: API key (overrides CATO_API_KEY env var)
- `--account ACCOUNT`: Account ID (overrides CATO_ACCOUNT_ID env var)
- `--url URL`: API URL (overrides CATO_API_URL env var)
- `--format FORMAT`: Output format (json, table, or simple)
- `--no-cache`: Disable cache functionality (cache enabled by default)
- `--debug`: Enable debug mode
- `-h, --help`: Show help message

### create_ip_container.py
Creates an empty IP address container that can be populated with IP addresses later.

```bash
# Create a container using environment variables
python examples/create_ip_container.py --name "Blocked IPs" --description "IP addresses to block"

# Override credentials with CLI parameters
python examples/create_ip_container.py --name "Allowed IPs" --description "Whitelisted IPs" \
    --key YOUR_KEY --account YOUR_ACCOUNT

# Get JSON output for scripting
python examples/create_ip_container.py --name "Test" --description "Test container" --format json
```

#### Required Arguments:
- `--name NAME`: Container name (required, max 255 chars)
- `--description DESC`: Container description (required, max 1000 chars)

#### Optional Arguments:
- `--key KEY`: API key (overrides CATO_API_KEY env var)
- `--account ACCOUNT`: Account ID (overrides CATO_ACCOUNT_ID env var)
- `--url URL`: API URL (overrides CATO_API_URL env var)
- `--format FORMAT`: Output format (json or simple, default: simple)
- `-h, --help`: Show help message

⚠️ **Note**: This creates a new container in your Cato account. Ensure you have the necessary permissions.

### create_fqdn_container.py
Creates an FQDN (Fully Qualified Domain Name) container that can be populated with domain names.

```bash
# Create an empty FQDN container
python examples/create_fqdn_container.py --name "Blocked Domains" --description "Domains to block"

# Create container with initial FQDNs
python examples/create_fqdn_container.py --name "Allowed Domains" --description "Whitelisted domains" \
    --fqdns "example.com,mail.google.com,api.github.com"

# Create container with FQDNs from file
python examples/create_fqdn_container.py --name "Corporate Domains" --description "Internal domains" \
    --fqdns-file ./domain_list.txt

# Get JSON output for scripting
python examples/create_fqdn_container.py --name "Test" --description "Test container" --format json
```

#### Required Arguments:
- `--name NAME`: Container name (required, max 255 chars)
- `--description DESC`: Container description (required, max 1000 chars)

#### Optional Arguments:
- `--fqdns FQDNS`: Comma-separated FQDNs (e.g., "example.com,*.google.com")
- `--fqdns-file FILE`: File with FQDNs, one per line
- `--key KEY`: API key (overrides CATO_API_KEY env var)
- `--account ACCOUNT`: Account ID (overrides CATO_ACCOUNT_ID env var)
- `--url URL`: API URL (overrides CATO_API_URL env var)
- `--format FORMAT`: Output format (json or simple, default: simple)
- `--debug`: Enable debug mode
- `-h, --help`: Show help message

**FQDN Examples**: `example.com`, `subdomain.example.com`, `api.github.com`, `mail.server.com`

**Note**: Wildcards (e.g., `*.example.com`) are not supported by the Cato API

⚠️ **Note**: This creates a new container in your Cato account. Ensure you have the necessary permissions.

### add_ip_range.py
Adds an IP address range to an existing IP container in your Cato account.

```bash
# Add a single IP address
python examples/add_ip_range.py --container "Blocked IPs" --from-ip "192.168.1.100" --to-ip "192.168.1.100"

# Add an IP range
python examples/add_ip_range.py --container "Allowed IPs" --from-ip "10.0.0.1" --to-ip "10.0.0.255"

# Add with debug output to troubleshoot
python examples/add_ip_range.py --container "Test IPs" --from-ip "172.16.1.1" --to-ip "172.16.1.50" --debug

# IPv6 support
python examples/add_ip_range.py --container "IPv6 IPs" --from-ip "2001:db8::1" --to-ip "2001:db8::100"

# Get JSON output for scripting
python examples/add_ip_range.py --container "Test" --from-ip "127.0.0.1" --to-ip "127.0.0.1" --format json
```

#### Required Arguments:
- `--container NAME`: Container name to add IPs to (required)
- `--from-ip IP`: Starting IP address of the range (required)
- `--to-ip IP`: Ending IP address of the range (required)

#### Optional Arguments:
- `--key KEY`: API key (overrides CATO_API_KEY env var)
- `--account ACCOUNT`: Account ID (overrides CATO_ACCOUNT_ID env var)
- `--url URL`: API URL (overrides CATO_API_URL env var)
- `--format FORMAT`: Output format (json or simple, default: simple)
- `--debug`: Enable debug mode
- `-h, --help`: Show help message

**IP Examples**: Single IP (same from/to), IP ranges, IPv4 and IPv6 addresses supported

⚠️ **Note**: This modifies an existing container in your Cato account. Ensure you have the necessary permissions.

### add_fqdns.py
Adds FQDNs (Fully Qualified Domain Names) to an existing FQDN container in your Cato account.

```bash
# Add multiple FQDNs from command line
python examples/add_fqdns.py --container "Blocked Domains" --fqdns "malware.com,phishing.net,spam.org"

# Add multiple subdomains  
python examples/add_fqdns.py --container "Social Media" --fqdns "m.facebook.com,api.twitter.com,cdn.instagram.com"

# Add FQDNs from file
python examples/add_fqdns.py --container "Corporate Domains" --fqdns-file ./additional_domains.txt

# Add with debug output to troubleshoot
python examples/add_fqdns.py --container "Test Domains" --fqdns "test1.local,test2.local" --debug

# Get JSON output for scripting
python examples/add_fqdns.py --container "Test" --fqdns "example.com" --format json
```

#### Required Arguments:
- `--container NAME`: Container name to add FQDNs to (required)
- `--fqdns FQDNS`: Comma-separated FQDNs to add (required, OR use --fqdns-file)
- `--fqdns-file FILE`: File with FQDNs, one per line (alternative to --fqdns)

#### Optional Arguments:
- `--key KEY`: API key (overrides CATO_API_KEY env var)
- `--account ACCOUNT`: Account ID (overrides CATO_ACCOUNT_ID env var)
- `--url URL`: API URL (overrides CATO_API_URL env var)
- `--format FORMAT`: Output format (json or simple, default: simple)
- `--debug`: Enable debug mode
- `-h, --help`: Show help message

**FQDN Examples**: `example.com`, `subdomain.example.com`, `api.github.com`, `mail.server.com`

**Note**: Wildcards (e.g., `*.example.com`) are not supported by the Cato API, `test.local`

⚠️ **Note**: This modifies an existing container in your Cato account. Ensure you have the necessary permissions.

### delete_container.py
Deletes an existing container from your Cato account by name.

```bash
# Delete a container with confirmation prompt
python examples/delete_container.py --name "Container Name"

# Delete without confirmation (use with caution!)
python examples/delete_container.py --name "Container Name" --force

# Delete with debug output to troubleshoot
python examples/delete_container.py --name "Container Name" --debug

# Get JSON response
python examples/delete_container.py --name "Container Name" --force --format json
```

#### Required Arguments:
- `--name NAME`: Container name to delete (required)

#### Optional Arguments:
- `--force`: Skip confirmation prompt (dangerous!)
- `--key KEY`: API key (overrides CATO_API_KEY env var)
- `--account ACCOUNT`: Account ID (overrides CATO_ACCOUNT_ID env var)
- `--url URL`: API URL (overrides CATO_API_URL env var)
- `--format FORMAT`: Output format (json or simple, default: simple)
- `--debug`: Enable debug mode
- `-h, --help`: Show help message

⚠️ **WARNING**: This permanently deletes the container and all its contents. This action cannot be undone!

### cache_demo.py
Comprehensive demonstration of the cache functionality, showing how caching improves performance and provides additional features.

```bash
# Run the cache demonstration
python examples/cache_demo.py

# Run with custom cache location
CATO_CACHE_PATH=/tmp/demo_cache.db python examples/cache_demo.py
```

**Features demonstrated:**
- Cache hits vs API calls with performance comparison
- Timestamp tracking for entries (added/last seen)
- Partial cache hits for FQDN operations
- Cache statistics (per-container and global)
- Stale entry purging
- Cache-aware duplicate detection

**Note**: This creates a demo container in your Cato account for testing.

### cache_maintenance.py
Utility script for managing and maintaining the Cato API cache database.

```bash
# Show global cache statistics
python examples/cache_maintenance.py stats

# Show cache stats for specific container
python examples/cache_maintenance.py stats --container "My Container"

# List all cached values for a container with timestamps
python examples/cache_maintenance.py list --container "My Container"

# Purge entries older than 30 days (with confirmation)
python examples/cache_maintenance.py purge --container "My Container" --days 30

# Purge entries older than 7 days without confirmation
python examples/cache_maintenance.py purge --container "My Container" --days 7 --force

# Clear all cache entries for a container (with confirmation)
python examples/cache_maintenance.py clear --container "My Container"

# Clear all cache entries without confirmation (dangerous!)
python examples/cache_maintenance.py clear --container "My Container" --force
```

#### Cache Maintenance Commands:
- **stats**: Show cache statistics (global or per-container)
- **list**: Display all cached values with timestamps
- **purge**: Remove entries older than specified days
- **clear**: Remove all cached entries for a container

#### Optional Arguments:
- `--key KEY`: API key (overrides CATO_API_KEY env var)
- `--account ACCOUNT`: Account ID (overrides CATO_ACCOUNT_ID env var)
- `--url URL`: API URL (overrides CATO_API_URL env var)
- `--cache-path PATH`: Cache file path (overrides CATO_CACHE_PATH env var)

⚠️ **Note**: Clear and purge operations cannot be undone. Use with caution!

## Debug Mode

All examples support a `--debug` flag that shows:
- Raw request payload (JSON or multipart)
- HTTP headers (with API key masked)
- Raw response body
- Detailed error messages with response bodies

This is extremely useful for troubleshooting API issues:

```bash
# Debug a container list request
python examples/list_containers.py --debug

# Debug container creation with file upload
python examples/create_ip_container.py --name "Test" --description "Debug test" --debug

# Set debug mode via environment variable
export CATO_DEBUG=true
python examples/list_containers.py
```

## Error Handling

All examples include comprehensive error handling:
- **Configuration errors**: Missing API key or account ID
- **Network errors**: Connection failures, timeouts
- **GraphQL errors**: API-specific errors with detailed messages
- **Unexpected errors**: General exception handling

## Adding New Examples

When creating new examples, follow these patterns:
1. Support both environment variables and CLI parameters
2. Include proper error handling for all exception types
3. Provide multiple output format options where applicable
4. Add comprehensive documentation in the script header
5. Update this README with usage instructions