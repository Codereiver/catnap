"""
cato.py

A simple wrapper for Cato API queries.
"""

import os
import certifi
import gzip
import json
import ssl
import urllib.parse
import urllib.request
import uuid
import io
from dotenv import load_dotenv
from cache import Cache

load_dotenv()


class CatoAPIError(Exception):
	"""Base exception for Cato API errors"""
	pass


class CatoNetworkError(CatoAPIError):
	"""Raised when network/connection errors occur"""
	pass


class CatoGraphQLError(CatoAPIError):
	"""Raised when GraphQL returns errors in response"""
	def __init__(self, errors):
		self.errors = errors
		super().__init__(f"GraphQL errors: {errors}")



class API:
	"""
	Simple class to make API queries. Includes:

	* Automatic response compression.
	* Error handling.
	"""


	def __init__(self, key=None, account_id=None, url=None, debug=False, cache_enabled=None, cache_path=None):
		"""
		Instantiate object with API key.
		
		Parameters can be provided directly or read from environment variables:
		- key: API key (or CATO_API_KEY env var)
		- account_id: Account ID (or CATO_ACCOUNT_ID env var)
		- url: API URL (or CATO_API_URL env var, defaults to Cato API endpoint)
		- debug: Enable debug mode to print raw requests/responses
		- cache_enabled: Enable/disable cache (or CATO_CACHE_ENABLED env var, defaults to True)
		- cache_path: Path to cache database (or CATO_CACHE_PATH env var)
		"""
		self._key = key or os.environ.get('CATO_API_KEY')
		self._account_id = account_id or os.environ.get('CATO_ACCOUNT_ID')
		self._url = url or os.environ.get('CATO_API_URL', 'https://api.catonetworks.com/api/v1/graphql2')
		self._debug = debug or os.environ.get('CATO_DEBUG', '').lower() in ('true', '1', 'yes')
		
		# Cache settings
		if cache_enabled is None:
			cache_env = os.environ.get('CATO_CACHE_ENABLED', '').lower()
			cache_enabled = cache_env != 'false' and cache_env != '0' and cache_env != 'no'
		
		if cache_enabled:
			cache_path = cache_path or os.environ.get('CATO_CACHE_PATH')
			self._cache = Cache(cache_path)
		else:
			self._cache = None
		
		if not self._key:
			raise ValueError("API key is required. Provide 'key' parameter or set CATO_API_KEY environment variable.")
		if not self._account_id:
			raise ValueError("Account ID is required. Provide 'account_id' parameter or set CATO_ACCOUNT_ID environment variable.")


	def send(self, operation, variables, query):
		"""
		Send an API request and return the response as a Python object.

		Returns the Python object converted from JSON response.
		Raises CatoNetworkError for connection issues.
		Raises CatoGraphQLError if the API returns errors.
		"""
		body = json.dumps({
			"operationName": operation,
			"query":query,
			"variables":variables
		}, indent=2)
		
		if self._debug:
			print("\n" + "="*60)
			print("DEBUG: JSON API Request")
			print("="*60)
			print(f"URL: {self._url}")
			print(f"Operation: {operation}")
			print("Headers:")
			print(f"  Content-Type: application/json")
			print(f"  X-api-key: {self._key[:8]}..." if len(self._key) > 8 else f"  X-api-key: {self._key}")
			print("Body:")
			print(body)
			print("="*60)
		
		body = body.encode("ascii")
		headers = {
			"Content-Type": "application/json",
			"Accept-Encoding": "gzip, deflate, br",
			"X-api-key": self._key
		}
		
		try:
			request = urllib.request.Request(
				url=self._url,
				data=body,
				headers=headers
			)
			response = urllib.request.urlopen(
				request, 
				context=ssl.create_default_context(cafile=certifi.where()),
				timeout=10
			)
			response_data = gzip.decompress(response.read())
			response_text = response_data.decode('utf-8','replace')
			response_obj = json.loads(response_text)
			
			if self._debug:
				print("\n" + "="*60)
				print("DEBUG: API Response")
				print("="*60)
				print(f"Status: {response.status if hasattr(response, 'status') else 'OK'}")
				print("Response Body:")
				print(json.dumps(response_obj, indent=2))
				print("="*60 + "\n")
				
		except urllib.error.HTTPError as e:
			# Try to read error response body
			error_body = None
			try:
				error_data = e.read()
				if error_data:
					# Try to decompress if gzipped
					try:
						error_data = gzip.decompress(error_data)
					except:
						pass
					error_body = error_data.decode('utf-8', 'replace')
			except:
				pass
			
			if self._debug:
				print("\n" + "="*60)
				print("DEBUG: HTTP Error")
				print("="*60)
				print(f"Status Code: {e.code}")
				print(f"Error Message: {e.msg}")
				if error_body:
					print("Error Response Body:")
					try:
						error_json = json.loads(error_body)
						print(json.dumps(error_json, indent=2))
					except:
						print(error_body)
				print("="*60 + "\n")
			
			# Include error body in exception if available
			if error_body:
				raise CatoNetworkError(f"HTTP {e.code}: {e.msg}. Response: {error_body}") from e
			else:
				raise CatoNetworkError(f"HTTP {e.code}: {e.msg}") from e
		except Exception as e:
			if self._debug:
				print("\n" + "="*60)
				print("DEBUG: API Error")
				print("="*60)
				print(f"Error: {e}")
				print("="*60 + "\n")
			raise CatoNetworkError(f"Failed to connect to API: {e}") from e
		
		if "errors" in response_obj:
			if self._debug:
				print("\n" + "="*60)
				print("DEBUG: GraphQL Errors")
				print("="*60)
				print(json.dumps(response_obj["errors"], indent=2))
				print("="*60 + "\n")
			raise CatoGraphQLError(response_obj["errors"])
		
		return response_obj
	
	
	def send_multipart(self, operation, variables, query, files=None):
		"""
		Send a multipart GraphQL request with file upload support.
		
		Args:
			operation: GraphQL operation name
			variables: GraphQL variables (files should be None in variables)
			query: GraphQL query string
			files: Dict mapping variable paths to file contents
				   e.g., {"variables.uploadFile": ("filename.csv", file_content)}
		
		Returns the Python object converted from JSON response.
		Raises CatoNetworkError for connection issues.
		Raises CatoGraphQLError if the API returns errors.
		"""
		boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
		
		# Build multipart body
		body_parts = []
		
		# Add operations part
		operations = {
			"operationName": operation,
			"query": query,
			"variables": variables
		}
		
		if self._debug:
			print("\n" + "="*60)
			print("DEBUG: Multipart API Request")
			print("="*60)
			print(f"URL: {self._url}")
			print(f"Operation: {operation}")
			print(f"Boundary: {boundary}")
			print("Operations:")
			print(json.dumps(operations, indent=2))
		
		body_parts.append(f'--{boundary}'.encode())
		body_parts.append(b'Content-Disposition: form-data; name="operations"')
		body_parts.append(b'')
		body_parts.append(json.dumps(operations).encode('utf-8'))
		
		# Add map part if files are provided
		if files:
			file_map = {}
			file_index = 0
			for path, _ in files.items():
				file_map[str(file_index)] = [path]
				file_index += 1
			
			if self._debug:
				print("Map:")
				print(json.dumps(file_map, indent=2))
			
			body_parts.append(f'--{boundary}'.encode())
			body_parts.append(b'Content-Disposition: form-data; name="map"')
			body_parts.append(b'')
			body_parts.append(json.dumps(file_map).encode('utf-8'))
			
			# Add file parts
			file_index = 0
			for path, (filename, content) in files.items():
				if self._debug:
					print(f"File {file_index}:")
					print(f"  Path: {path}")
					print(f"  Filename: {filename}")
					print(f"  Content Length: {len(content) if content else 0} bytes")
					if content and len(content) < 500:
						print(f"  Content Preview: {content[:100]}...")
				
				body_parts.append(f'--{boundary}'.encode())
				body_parts.append(f'Content-Disposition: form-data; name="{file_index}"; filename="{filename}"'.encode())
				body_parts.append(b'Content-Type: text/csv')
				body_parts.append(b'')
				if isinstance(content, str):
					body_parts.append(content.encode('utf-8'))
				else:
					body_parts.append(content)
				file_index += 1
		
		body_parts.append(f'--{boundary}--'.encode())
		
		# Join body parts with CRLF
		body = b'\r\n'.join(body_parts)
		
		if self._debug:
			print("Headers:")
			print(f"  Content-Type: multipart/form-data; boundary={boundary}")
			print(f"  X-api-key: {self._key[:8]}..." if len(self._key) > 8 else f"  X-api-key: {self._key}")
			print(f"Raw Body Length: {len(body)} bytes")
			if len(body) < 2000:
				print("Raw Body Preview:")
				print(body.decode('utf-8', 'replace')[:1000])
			print("="*60)
		
		headers = {
			"Content-Type": f"multipart/form-data; boundary={boundary}",
			"Accept-Encoding": "gzip, deflate, br",
			"X-api-key": self._key
		}
		
		try:
			request = urllib.request.Request(
				url=self._url,
				data=body,
				headers=headers
			)
			response = urllib.request.urlopen(
				request, 
				context=ssl.create_default_context(cafile=certifi.where()),
				timeout=30  # Longer timeout for file uploads
			)
			response_data = gzip.decompress(response.read())
			response_text = response_data.decode('utf-8','replace')
			response_obj = json.loads(response_text)
			
			if self._debug:
				print("\n" + "="*60)
				print("DEBUG: API Response")
				print("="*60)
				print(f"Status: {response.status if hasattr(response, 'status') else 'OK'}")
				print("Response Body:")
				print(json.dumps(response_obj, indent=2))
				print("="*60 + "\n")
				
		except urllib.error.HTTPError as e:
			# Try to read error response body
			error_body = None
			try:
				error_data = e.read()
				if error_data:
					# Try to decompress if gzipped
					try:
						error_data = gzip.decompress(error_data)
					except:
						pass
					error_body = error_data.decode('utf-8', 'replace')
			except:
				pass
			
			if self._debug:
				print("\n" + "="*60)
				print("DEBUG: HTTP Error")
				print("="*60)
				print(f"Status Code: {e.code}")
				print(f"Error Message: {e.msg}")
				print(f"URL: {e.url}")
				if error_body:
					print("Error Response Body:")
					try:
						error_json = json.loads(error_body)
						print(json.dumps(error_json, indent=2))
					except:
						print(error_body)
				import traceback
				print("Traceback:")
				traceback.print_exc()
				print("="*60 + "\n")
			
			# Include error body in exception if available
			if error_body:
				raise CatoNetworkError(f"HTTP {e.code}: {e.msg}. Response: {error_body}") from e
			else:
				raise CatoNetworkError(f"HTTP {e.code}: {e.msg}") from e
		except Exception as e:
			if self._debug:
				print("\n" + "="*60)
				print("DEBUG: API Error")
				print("="*60)
				print(f"Error Type: {type(e).__name__}")
				print(f"Error: {e}")
				import traceback
				print("Traceback:")
				traceback.print_exc()
				print("="*60 + "\n")
			raise CatoNetworkError(f"Failed to connect to API: {e}") from e
		
		if "errors" in response_obj:
			if self._debug:
				print("\n" + "="*60)
				print("DEBUG: GraphQL Errors")
				print("="*60)
				print(json.dumps(response_obj["errors"], indent=2))
				print("="*60 + "\n")
			raise CatoGraphQLError(response_obj["errors"])
		
		return response_obj


	#
	# Container handling queries and mutations
	#


	def container_create_ip(self, name, description, ip_addresses=None, account_id=None):
		"""
		Creates an IP address container, optionally with initial IP addresses.
		
		Args:
			name: Container name
			description: Container description
			ip_addresses: Optional list of IP addresses/ranges to add initially
			account_id: Optional account ID (uses default if not provided)
		
		Returns the container creation response.
		"""
		if account_id is None:
			account_id = self._account_id
		
		operation = "createIpAddressRangeContainerFromFile"
		query = """
mutation createIpAddressRangeContainerFromFile($accountId:ID!, $input:CreateIpAddressRangeContainerFromFileInput!)  {
	container(accountId: $accountId) {
		ipAddressRange {
			createFromFile(input: $input) {
				container {
					__typename
					id
					name
					description
					size
					audit {
						createdBy
						createdAt
						lastModifiedBy
						lastModifiedAt
					}
				}
			}
		}
	}
}
"""
		variables = {
			"accountId": account_id,
			"input": {
				"description": description,
				"fileType": "CSV",
				"name": name,
				"uploadFile": None
			}
		}
		
		# If IP addresses are provided, create a CSV file content
		if ip_addresses:
			# Create CSV content from IP addresses
			csv_content = "\n".join(ip_addresses) if ip_addresses else ""
			
			# Use multipart upload with the file
			files = {
				"variables.input.uploadFile": (f"{name}.csv", csv_content)
			}
			return self.send_multipart(operation, variables, query, files)
		else:
			# Create empty container - still needs an empty file
			files = {
				"variables.input.uploadFile": (f"{name}.csv", "")
			}
			return self.send_multipart(operation, variables, query, files)


	def container_create_fqdn(self, name, description, fqdns=None, account_id=None):
		"""
		Creates an FQDN container, optionally with initial FQDNs.
		
		Args:
			name: Container name
			description: Container description
			fqdns: Optional list of FQDNs to add initially
			account_id: Optional account ID (uses default if not provided)
		
		Returns the container creation response.
		"""
		if account_id is None:
			account_id = self._account_id
		
		operation = "createFqdnContainerFromFile"
		query = """
mutation createFqdnContainerFromFile($accountId:ID!, $input:CreateFqdnContainerFromFileInput!)  {
	container(accountId: $accountId) {
		fqdn {
			createFromFile(input: $input) {
				container {
					__typename
					id
					name
					description
					size
					audit {
						createdBy
						createdAt
						lastModifiedBy
						lastModifiedAt
					}
				}
			}
		}
	}
}
"""
		variables = {
			"accountId": account_id,
			"input": {
				"description": description,
				"fileType": "CSV",
				"name": name,
				"uploadFile": None
			}
		}
		
		# If FQDNs are provided, create a CSV file content
		if fqdns:
			# Create CSV content from FQDNs
			csv_content = "\n".join(fqdns) if fqdns else ""
			
			# Use multipart upload with the file
			files = {
				"variables.input.uploadFile": (f"{name}.csv", csv_content)
			}
			return self.send_multipart(operation, variables, query, files)
		else:
			# Create empty container - still needs an empty file
			files = {
				"variables.input.uploadFile": (f"{name}.csv", "")
			}
			return self.send_multipart(operation, variables, query, files)


	def container_add_ip_range(self, container_name, from_ip, to_ip, account_id=None):
		"""
		Add an IP address range to an existing IP container.
		
		Args:
			container_name: Name of the container to add IPs to
			from_ip: Starting IP address of the range
			to_ip: Ending IP address of the range
			account_id: Optional account ID (uses default if not provided)
		
		Returns the API response for adding the IP range.
		"""
		if account_id is None:
			account_id = self._account_id
		
		# Check cache first
		if self._cache and self._cache.has_ip_range(container_name, from_ip, to_ip):
			self._cache.update_ip_timestamp(container_name, from_ip, to_ip)
			if self._debug:
				print(f"DEBUG: IP range {from_ip}-{to_ip} already in cache for container '{container_name}', skipping API call")
			# Return a mock response that looks like the API response
			return {
				"cached": True,
				"data": {
					"container": {
						"ipAddressRange": {
							"addValues": {
								"container": {
									"name": container_name,
									"__typename": "IpAddressRangeContainer"
								}
							}
						}
					}
				}
			}
		
		operation = "addIpRangeToContainer"
		query = """
mutation addIpRangeToContainer($accountId:ID!, $input:IpAddressRangeContainerAddValuesInput!)  {
	container(accountId: $accountId) {
		ipAddressRange {
			addValues(input: $input) {
				container {
					__typename
					id
					name
					description
					size
					audit {
						createdBy
						createdAt
						lastModifiedBy
						lastModifiedAt
					}
				}
			}
		}
	}
}
"""
		variables = {
			"accountId": account_id,
			"input": {
				"ref": {"by": "NAME", "input": container_name},
				"values": [
					{"from": from_ip, "to": to_ip},
				]
			}
		}
		
		result = self.send(operation, variables, query)
		
		# Update cache on success
		if self._cache and "data" in result and not "errors" in result:
			self._cache.add_ip_range(container_name, from_ip, to_ip)
			# Update container metadata if size is available
			container_data = result.get("data", {}).get("container", {}).get("ipAddressRange", {}).get("addValues", {}).get("container", {})
			if "size" in container_data:
				self._cache.update_container_metadata(container_name, "ip", container_data["size"])
			if self._debug:
				print(f"DEBUG: Cached IP range {from_ip}-{to_ip} for container '{container_name}'")
		
		return result

	def container_remove_ip_range(self, container_name, from_ip, to_ip, account_id=None):
		"""
		Remove an IP address range from an existing IP container.
		
		Args:
			container_name: Name of the container to remove IPs from
			from_ip: Starting IP address of the range
			to_ip: Ending IP address of the range
			account_id: Optional account ID (uses default if not provided)
		
		Returns the API response for removing the IP range.
		"""
		if account_id is None:
			account_id = self._account_id
		
		operation = "removeIpRangeFromContainer"
		query = """
mutation removeIpRangeFromContainer($accountId:ID!, $input:IpAddressRangeContainerRemoveValuesInput!)  {
	container(accountId: $accountId) {
		ipAddressRange {
			removeValues(input: $input) {
				container {
					id
					name
					description
					size
					audit {
						createdBy
						createdAt
						lastModifiedBy
						lastModifiedAt
					}
				}
			}
		}
	}
}
"""
		variables = {
			"accountId": account_id,
			"input": {
				"ref": {"by": "NAME", "input": container_name},
				"values": [
					{"from": from_ip, "to": to_ip},
				]
			}
		}
		
		result = self.send(operation, variables, query)
		
		# Remove from cache on success
		if self._cache and "data" in result and not "errors" in result:
			removed = self._cache.remove_ip_range(container_name, from_ip, to_ip)
			# Update container metadata if size is available
			container_data = result.get("data", {}).get("container", {}).get("ipAddressRange", {}).get("removeValues", {}).get("container", {})
			if "size" in container_data:
				self._cache.update_container_metadata(container_name, "ip", container_data["size"])
			if self._debug:
				if removed:
					print(f"DEBUG: Removed IP range {from_ip}-{to_ip} from cache for container '{container_name}'")
				else:
					print(f"DEBUG: IP range {from_ip}-{to_ip} was not in cache for container '{container_name}'")
		
		return result


	def container_add_fqdns(self, container_name, fqdns, account_id=None):
		"""
		Add FQDNs to an existing FQDN container.
		
		Args:
			container_name: Name of the container to add FQDNs to
			fqdns: List of FQDNs to add to the container
			account_id: Optional account ID (uses default if not provided)
		
		Returns the API response for adding the FQDNs.
		"""
		if account_id is None:
			account_id = self._account_id
		
		# Check cache and filter out existing FQDNs
		new_fqdns = []
		cached_fqdns = []
		
		if self._cache:
			for fqdn in fqdns:
				if self._cache.has_fqdn(container_name, fqdn):
					self._cache.update_fqdn_timestamp(container_name, fqdn)
					cached_fqdns.append(fqdn)
				else:
					new_fqdns.append(fqdn)
			
			if cached_fqdns and self._debug:
				print(f"DEBUG: {len(cached_fqdns)} FQDNs already in cache for container '{container_name}': {', '.join(cached_fqdns)}")
			
			# If all FQDNs are cached, skip API call
			if not new_fqdns:
				if self._debug:
					print(f"DEBUG: All FQDNs already in cache, skipping API call")
				return {
					"cached": True,
					"data": {
						"container": {
							"fqdn": {
								"addValues": {
									"container": {
										"name": container_name,
										"__typename": "FqdnContainer"
									}
								}
							}
						}
					}
				}
		else:
			new_fqdns = fqdns
		
		operation = "addFqdnsToContainer"
		query = """
mutation addFqdnsToContainer($accountId:ID!, $input:FqdnContainerAddValuesInput!)  {
	container(accountId: $accountId) {
		fqdn {
			addValues(input: $input) {
				container {
					__typename
					id
					name
					description
					size
					audit {
						createdBy
						createdAt
						lastModifiedBy
						lastModifiedAt
					}
				}
			}
		}
	}
}
"""
		variables = {
			"accountId": account_id,
			"input": {
				"ref": {"by": "NAME", "input": container_name},
				"values": new_fqdns
			}
		}
		
		result = self.send(operation, variables, query)
		
		# Update cache on success
		if self._cache and "data" in result and not "errors" in result:
			for fqdn in new_fqdns:
				self._cache.add_fqdn(container_name, fqdn)
			# Update container metadata if size is available
			container_data = result.get("data", {}).get("container", {}).get("fqdn", {}).get("addValues", {}).get("container", {})
			if "size" in container_data:
				self._cache.update_container_metadata(container_name, "fqdn", container_data["size"])
			if self._debug:
				print(f"DEBUG: Cached {len(new_fqdns)} new FQDNs for container '{container_name}'")
		
		return result

	def container_remove_fqdns(self, container_name, fqdns, account_id=None):
		"""
		Remove FQDNs from an existing FQDN container.
		
		Args:
			container_name: Name of the container to remove FQDNs from
			fqdns: List of FQDNs to remove from the container
			account_id: Optional account ID (uses default if not provided)
		
		Returns the API response for removing the FQDNs.
		"""
		if account_id is None:
			account_id = self._account_id
		
		operation = "removeFqdnsFromContainer"
		query = """
mutation removeFqdnsFromContainer($accountId:ID!, $input:FqdnContainerRemoveValuesInput!)  {
	container(accountId: $accountId) {
		fqdn {
			removeValues(input: $input) {
				container {
					__typename
					id
					name
					description
					size
					audit {
						createdBy
						createdAt
						lastModifiedBy
						lastModifiedAt
					}
				}
			}
		}
	}
}
"""
		variables = {
			"accountId": account_id,
			"input": {
				"ref": {"by": "NAME", "input": container_name},
				"values": fqdns
			}
		}
		
		result = self.send(operation, variables, query)
		
		# Remove from cache on success
		if self._cache and "data" in result and not "errors" in result:
			removed_count = 0
			for fqdn in fqdns:
				if self._cache.remove_fqdn(container_name, fqdn):
					removed_count += 1
			# Update container metadata if size is available
			container_data = result.get("data", {}).get("container", {}).get("fqdn", {}).get("removeValues", {}).get("container", {})
			if "size" in container_data:
				self._cache.update_container_metadata(container_name, "fqdn", container_data["size"])
			if self._debug:
				print(f"DEBUG: Removed {removed_count} FQDNs from cache for container '{container_name}'")
		
		return result


	def container_delete(self, name, account_id=None):
		"""
		Delete a container.
		"""
		if account_id is None:
			account_id = self._account_id
		operation = "deleteContainer"
		query = """
mutation deleteContainer($accountId:ID!, $input:DeleteContainerInput!) {
	container(accountId: $accountId) {
		delete(input: $input) {
			container {
				id
				name
				description
				size
				audit {
					createdBy
					createdAt
					lastModifiedBy
					lastModifiedAt
				}
			}
		}
	}
}   
"""
		variables = {
			"accountId": account_id,
			"input": {
				"ref": {
					"by": "NAME", 
					"input": name
				}
			}
		}
		
		response = self.send(operation, variables, query)
		
		# Clear cache entries when container is successfully deleted
		if self._cache and response.get("data") and not response.get("errors"):
			try:
				self._cache.clear_container(name)
			except Exception:
				# Don't fail the deletion if cache cleanup fails
				pass
		
		return response


	def container_list(self, account_id=None):
		"""
		List current containers in a Cato account.
		
		Returns the container list response, augmented with cache information
		if caching is enabled.
		
		Raises CatoNetworkError or CatoGraphQLError on failure.
		"""
		if account_id is None:
			account_id = self._account_id
			
		operation = "listContainers"
		query = """
query listContainers($accountId:ID!, $input:ContainerSearchInput!)  {
	container(accountId: $accountId) {
		list(input: $input) {
			containers {
				__typename
				id
				name
				description
				size
				audit {
					createdBy
					createdAt
					lastModifiedBy
					lastModifiedAt
				}
			}
		}
	}
}
"""
		variables = {
			"accountId": account_id,
			"input": {}
		}
		
		response = self.send(operation, variables, query)
		
		# Augment response with cache information if cache is enabled
		if self._cache and response.get("data", {}).get("container", {}).get("list", {}).get("containers"):
			containers = response["data"]["container"]["list"]["containers"]
			
			for container in containers:
				container_name = container["name"]
				
				# Get cache statistics for this container
				try:
					cache_stats = self._cache.get_stats(container_name)
					container["cache"] = {
						"cached": cache_stats["total_cached"] > 0,
						"cached_ip_ranges": cache_stats["cached_ip_ranges"],
						"cached_fqdns": cache_stats["cached_fqdns"],
						"total_cached": cache_stats["total_cached"]
					}
					
					if "last_sync" in cache_stats:
						container["cache"]["last_sync"] = cache_stats["last_sync"]
						
				except Exception:
					# If cache lookup fails, indicate container is not cached
					container["cache"] = {
						"cached": False,
						"cached_ip_ranges": 0,
						"cached_fqdns": 0,
						"total_cached": 0
					}
		
		return response
	
	
	#
	# Cache management methods
	#
	
	
	def container_list_cached_values(self, container_name):
		"""
		List all cached values for a container with timestamps.
		
		Args:
			container_name: Name of the container
		
		Returns:
			Dictionary with 'ip_ranges' and/or 'fqdns' lists containing cached values
		
		Raises:
			ValueError if cache is not enabled
		"""
		if not self._cache:
			raise ValueError("Cache is not enabled. Initialize API with cache_enabled=True")
		
		result = {}
		
		# Get container type from metadata or try both
		container_type = self._cache.get_container_type(container_name)
		
		if container_type == "ip" or container_type is None:
			ip_ranges = self._cache.get_container_ip_ranges(container_name)
			if ip_ranges:
				result['ip_ranges'] = ip_ranges
		
		if container_type == "fqdn" or container_type is None:
			fqdns = self._cache.get_container_fqdns(container_name)
			if fqdns:
				result['fqdns'] = fqdns
		
		result['container'] = container_name
		result['type'] = container_type or 'unknown'
		
		return result
	
	
	def container_purge_stale(self, container_name, max_age_days=30):
		"""
		Remove cached entries older than specified days.
		
		Args:
			container_name: Name of the container
			max_age_days: Maximum age in days (default 30)
		
		Returns:
			Dictionary with number of deleted entries
		
		Raises:
			ValueError if cache is not enabled
		"""
		if not self._cache:
			raise ValueError("Cache is not enabled. Initialize API with cache_enabled=True")
		
		deleted_ip = self._cache.purge_stale_ip_ranges(container_name, max_age_days)
		deleted_fqdn = self._cache.purge_stale_fqdns(container_name, max_age_days)
		
		return {
			'container': container_name,
			'deleted_ip_ranges': deleted_ip,
			'deleted_fqdns': deleted_fqdn,
			'total_deleted': deleted_ip + deleted_fqdn,
			'max_age_days': max_age_days
		}
	
	
	def container_cache_stats(self, container_name=None):
		"""
		Get cache statistics for container(s).
		
		Args:
			container_name: Optional container name for specific stats
		
		Returns:
			Dictionary with cache statistics
		
		Raises:
			ValueError if cache is not enabled
		"""
		if not self._cache:
			raise ValueError("Cache is not enabled. Initialize API with cache_enabled=True")
		
		return self._cache.get_stats(container_name)
	
	
	def container_clear_cache(self, container_name):
		"""
		Clear all cached entries for a container.
		
		Args:
			container_name: Name of the container
		
		Returns:
			Dictionary with number of deleted entries
		
		Raises:
			ValueError if cache is not enabled
		"""
		if not self._cache:
			raise ValueError("Cache is not enabled. Initialize API with cache_enabled=True")
		
		deleted_ip, deleted_fqdn = self._cache.clear_container(container_name)
		
		return {
			'container': container_name,
			'deleted_ip_ranges': deleted_ip,
			'deleted_fqdns': deleted_fqdn,
			'total_deleted': deleted_ip + deleted_fqdn
		}


	def container_validate_cache_integrity(self, account_id=None):
		"""
		Validate the integrity of the cache by comparing it with the API.
		
		Performs the following checks:
		1. Verifies that containers in the API also exist in the cache
		2. Verifies that containers in the cache also exist in the API  
		3. Verifies that container sizes match between API and cache
		
		Args:
			account_id: Optional account ID (uses default if not provided)
		
		Returns:
			Dictionary with validation results and any discrepancies found
		
		Raises:
			ValueError if cache is not enabled
		"""
		if not self._cache:
			raise ValueError("Cache is not enabled. Initialize API with cache_enabled=True")
		
		if account_id is None:
			account_id = self._account_id
		
		# Get containers from API
		api_response = self.container_list(account_id)
		api_containers = {}
		
		if (api_response.get("data", {}).get("container", {}).get("list", {}).get("containers")):
			for container in api_response["data"]["container"]["list"]["containers"]:
				# Use __typename to determine container type more accurately
				typename = container.get('__typename', '')
				container_type = 'ip' if typename == 'IpAddressRangeContainer' else 'fqdn'
				
				api_containers[container['name']] = {
					'name': container['name'],
					'type': container_type,
					'size': container.get('size', 0)
				}
		
		# Get containers from cache
		cursor = self._cache.conn.cursor()
		cursor.execute("SELECT name, type, api_size FROM containers")
		cache_containers = {}
		
		for row in cursor.fetchall():
			cache_containers[row['name']] = {
				'name': row['name'],
				'type': row['type'],
				'size': row['api_size'] or 0
			}
		
		# Perform validation checks
		validation_result = {
			'timestamp': __import__('datetime').datetime.now().isoformat(),
			'api_containers_count': len(api_containers),
			'cache_containers_count': len(cache_containers),
			'checks': {
				'api_to_cache': {'passed': True, 'missing_in_cache': []},
				'cache_to_api': {'passed': True, 'missing_in_api': []},
				'size_consistency': {'passed': True, 'mismatched_sizes': []}
			},
			'overall_status': 'PASS'
		}
		
		# Check 1: Containers in API should exist in cache
		for api_name, api_container in api_containers.items():
			if api_name not in cache_containers:
				validation_result['checks']['api_to_cache']['passed'] = False
				validation_result['checks']['api_to_cache']['missing_in_cache'].append({
					'name': api_name,
					'type': api_container['type'],
					'size': api_container['size']
				})
		
		# Check 2: Containers in cache should exist in API
		for cache_name, cache_container in cache_containers.items():
			if cache_name not in api_containers:
				validation_result['checks']['cache_to_api']['passed'] = False
				validation_result['checks']['cache_to_api']['missing_in_api'].append({
					'name': cache_name,
					'type': cache_container['type'],
					'size': cache_container['size']
				})
		
		# Check 3: Container sizes should match
		common_containers = set(api_containers.keys()) & set(cache_containers.keys())
		for container_name in common_containers:
			api_size = api_containers[container_name]['size']
			cache_size = cache_containers[container_name]['size']
			
			if api_size != cache_size:
				validation_result['checks']['size_consistency']['passed'] = False
				validation_result['checks']['size_consistency']['mismatched_sizes'].append({
					'name': container_name,
					'type': api_containers[container_name]['type'],
					'api_size': api_size,
					'cache_size': cache_size,
					'difference': api_size - cache_size
				})
		
		# Set overall status
		all_checks_passed = all(
			check['passed'] for check in validation_result['checks'].values()
		)
		validation_result['overall_status'] = 'PASS' if all_checks_passed else 'FAIL'
		
		# Add summary counts
		validation_result['summary'] = {
			'containers_missing_in_cache': len(validation_result['checks']['api_to_cache']['missing_in_cache']),
			'containers_missing_in_api': len(validation_result['checks']['cache_to_api']['missing_in_api']),
			'containers_with_size_mismatch': len(validation_result['checks']['size_consistency']['mismatched_sizes']),
			'containers_validated': len(common_containers)
		}
		
		return validation_result
