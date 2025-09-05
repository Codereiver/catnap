"""
Tests for cato.py module
"""

import os
import json
import gzip
import time
import pytest
from unittest.mock import Mock, patch
import urllib.error
from dotenv import load_dotenv
from cato import API, CatoAPIError, CatoNetworkError, CatoGraphQLError

# Load .env file for integration tests
load_dotenv()


class TestExceptions:
    """Test custom exception classes"""
    
    def test_cato_api_error_inheritance(self):
        """Test that CatoAPIError is a proper Exception"""
        error = CatoAPIError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"
    
    def test_cato_network_error_inheritance(self):
        """Test that CatoNetworkError inherits from CatoAPIError"""
        error = CatoNetworkError("network error")
        assert isinstance(error, CatoAPIError)
        assert isinstance(error, Exception)
        assert str(error) == "network error"
    
    def test_cato_graphql_error(self):
        """Test CatoGraphQLError stores errors properly"""
        errors = [{"message": "Field error"}, {"message": "Another error"}]
        error = CatoGraphQLError(errors)
        assert isinstance(error, CatoAPIError)
        assert error.errors == errors
        assert "GraphQL errors:" in str(error)
        assert str(errors) in str(error)


class TestAPIInit:
    """Test API class initialization"""
    
    def test_init_with_direct_parameters(self):
        """Test initialization with direct parameters"""
        api = API(key="test_key", account_id="test_account")
        assert api._key == "test_key"
        assert api._account_id == "test_account"
        assert api._url == "https://api.catonetworks.com/api/v1/graphql2"
    
    def test_init_with_custom_url(self):
        """Test initialization with custom URL"""
        api = API(key="test_key", account_id="test_account", url="https://custom.url")
        assert api._url == "https://custom.url"
    
    @patch.dict(os.environ, {
        'CATO_API_KEY': 'env_key',
        'CATO_ACCOUNT_ID': 'env_account',
        'CATO_API_URL': 'https://env.url'
    })
    def test_init_from_environment_variables(self):
        """Test initialization from environment variables"""
        api = API()
        assert api._key == "env_key"
        assert api._account_id == "env_account"
        assert api._url == "https://env.url"
    
    @patch.dict(os.environ, {
        'CATO_API_KEY': 'env_key',
        'CATO_ACCOUNT_ID': 'env_account'
    }, clear=True)
    def test_init_env_vars_with_default_url(self):
        """Test that URL defaults when not in environment"""
        api = API()
        assert api._key == "env_key"
        assert api._account_id == "env_account"
        assert api._url == "https://api.catonetworks.com/api/v1/graphql2"
    
    @patch.dict(os.environ, {
        'CATO_API_KEY': 'env_key',
        'CATO_ACCOUNT_ID': 'env_account'
    })
    def test_init_parameters_override_env_vars(self):
        """Test that direct parameters override environment variables"""
        api = API(key="override_key", account_id="override_account")
        assert api._key == "override_key"
        assert api._account_id == "override_account"
    
    @patch.dict(os.environ, {}, clear=True)
    def test_init_missing_key_raises_error(self):
        """Test that missing API key raises ValueError"""
        with pytest.raises(ValueError, match="API key is required"):
            API(account_id="test_account")
    
    @patch.dict(os.environ, {}, clear=True)
    def test_init_missing_account_id_raises_error(self):
        """Test that missing account ID raises ValueError"""
        with pytest.raises(ValueError, match="Account ID is required"):
            API(key="test_key")


class TestMultipartUpload:
    """Test multipart file upload functionality"""
    
    @pytest.fixture
    def api(self):
        """Create API instance for testing"""
        return API(key="test_key", account_id="test_account")
    
    @patch('urllib.request.urlopen')
    def test_send_multipart_with_file(self, mock_urlopen, api):
        """Test multipart upload with file"""
        mock_response = Mock()
        mock_response.read.return_value = gzip.compress(json.dumps({"data": "success"}).encode())
        mock_urlopen.return_value = mock_response
        
        files = {
            "variables.uploadFile": ("test.csv", "192.168.1.1\n10.0.0.1")
        }
        
        result = api.send_multipart(
            "testOp",
            {"uploadFile": None},
            "mutation test",
            files
        )
        
        assert result == {"data": "success"}
        
        # Verify the request was made with multipart content type
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert "multipart/form-data" in request.headers.get('Content-type', '')
    
    @patch('urllib.request.urlopen')
    def test_container_create_ip_with_addresses(self, mock_urlopen, api):
        """Test container_create_ip with IP addresses"""
        mock_response = Mock()
        response_data = {
            "data": {
                "container": {
                    "ipAddressRange": {
                        "createFromFile": {
                            "container": {
                                "id": "12345",
                                "name": "Test Container",
                                "size": 2
                            }
                        }
                    }
                }
            }
        }
        mock_response.read.return_value = gzip.compress(json.dumps(response_data).encode())
        mock_urlopen.return_value = mock_response
        
        result = api.container_create_ip(
            name="Test Container",
            description="Test Description",
            ip_addresses=["192.168.1.0/24", "10.0.0.1"]
        )
        
        assert "data" in result
        container = result["data"]["container"]["ipAddressRange"]["createFromFile"]["container"]
        assert container["name"] == "Test Container"
        assert container["size"] == 2
        
        # Verify multipart request was made
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert "multipart/form-data" in request.headers.get('Content-type', '')
    
    @patch('urllib.request.urlopen')
    def test_container_create_ip_empty(self, mock_urlopen, api):
        """Test container_create_ip without IP addresses"""
        mock_response = Mock()
        response_data = {
            "data": {
                "container": {
                    "ipAddressRange": {
                        "createFromFile": {
                            "container": {
                                "id": "12345",
                                "name": "Empty Container",
                                "size": 0
                            }
                        }
                    }
                }
            }
        }
        mock_response.read.return_value = gzip.compress(json.dumps(response_data).encode())
        mock_urlopen.return_value = mock_response
        
        result = api.container_create_ip(
            name="Empty Container",
            description="Empty Description"
        )
        
        assert "data" in result
        container = result["data"]["container"]["ipAddressRange"]["createFromFile"]["container"]
        assert container["name"] == "Empty Container"
        assert container["size"] == 0
    
    @patch('urllib.request.urlopen')
    def test_container_create_fqdn_with_domains(self, mock_urlopen, api):
        """Test container_create_fqdn with FQDNs"""
        mock_response = Mock()
        response_data = {
            "data": {
                "container": {
                    "fqdn": {
                        "createFromFile": {
                            "container": {
                                "id": "67890",
                                "name": "FQDN Container",
                                "size": 3,
                                "__typename": "FqdnContainer"
                            }
                        }
                    }
                }
            }
        }
        mock_response.read.return_value = gzip.compress(json.dumps(response_data).encode())
        mock_urlopen.return_value = mock_response
        
        result = api.container_create_fqdn(
            name="FQDN Container",
            description="FQDN Description",
            fqdns=["example.com", "mail.google.com", "api.github.com"]
        )
        
        assert "data" in result
        container = result["data"]["container"]["fqdn"]["createFromFile"]["container"]
        assert container["name"] == "FQDN Container"
        assert container["size"] == 3
        assert container["__typename"] == "FqdnContainer"
        
        # Verify multipart request was made
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert "multipart/form-data" in request.headers.get('Content-type', '')
    
    @patch('urllib.request.urlopen')
    def test_container_create_fqdn_empty(self, mock_urlopen, api):
        """Test container_create_fqdn without FQDNs"""
        mock_response = Mock()
        response_data = {
            "data": {
                "container": {
                    "fqdn": {
                        "createFromFile": {
                            "container": {
                                "id": "67890",
                                "name": "Empty FQDN Container",
                                "size": 0,
                                "__typename": "FqdnContainer"
                            }
                        }
                    }
                }
            }
        }
        mock_response.read.return_value = gzip.compress(json.dumps(response_data).encode())
        mock_urlopen.return_value = mock_response
        
        result = api.container_create_fqdn(
            name="Empty FQDN Container",
            description="Empty FQDN Description"
        )
        
        assert "data" in result
        container = result["data"]["container"]["fqdn"]["createFromFile"]["container"]
        assert container["name"] == "Empty FQDN Container"
        assert container["size"] == 0


class TestAPISend:
    """Test API.send() method"""
    
    @pytest.fixture
    def api(self):
        """Create API instance for testing"""
        return API(key="test_key", account_id="test_account")
    
    @pytest.fixture
    def mock_response(self):
        """Create a mock response object"""
        mock = Mock()
        mock.read.return_value = gzip.compress(json.dumps({"data": "test"}).encode())
        return mock
    
    @patch('urllib.request.urlopen')
    def test_send_success(self, mock_urlopen, api, mock_response):
        """Test successful API call"""
        mock_urlopen.return_value = mock_response
        
        result = api.send("testOp", {"var": "value"}, "query test")
        
        assert result == {"data": "test"}
        mock_urlopen.assert_called_once()
        
        # Verify request construction
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert request.full_url == api._url
        assert request.headers['X-api-key'] == "test_key"
        assert request.headers['Content-type'] == "application/json"
    
    @patch('urllib.request.urlopen')
    def test_send_with_graphql_errors(self, mock_urlopen, api):
        """Test API call that returns GraphQL errors"""
        mock_response = Mock()
        response_data = {"errors": [{"message": "GraphQL error"}], "data": None}
        mock_response.read.return_value = gzip.compress(json.dumps(response_data).encode())
        mock_urlopen.return_value = mock_response
        
        with pytest.raises(CatoGraphQLError) as exc_info:
            api.send("testOp", {}, "query test")
        
        assert exc_info.value.errors == [{"message": "GraphQL error"}]
    
    @patch('urllib.request.urlopen')
    def test_send_network_error(self, mock_urlopen, api):
        """Test network error handling"""
        mock_urlopen.side_effect = urllib.error.URLError("Connection failed")
        
        with pytest.raises(CatoNetworkError, match="Failed to connect to API"):
            api.send("testOp", {}, "query test")
    
    @patch('urllib.request.urlopen')
    def test_send_timeout_error(self, mock_urlopen, api):
        """Test timeout error handling"""
        mock_urlopen.side_effect = TimeoutError("Request timed out")
        
        with pytest.raises(CatoNetworkError, match="Failed to connect to API"):
            api.send("testOp", {}, "query test")
    
    @patch('urllib.request.urlopen')
    def test_send_json_decode_error(self, mock_urlopen, api):
        """Test JSON decode error handling"""
        mock_response = Mock()
        mock_response.read.return_value = gzip.compress(b"invalid json")
        mock_urlopen.return_value = mock_response
        
        with pytest.raises(CatoNetworkError, match="Failed to connect to API"):
            api.send("testOp", {}, "query test")
    
    @patch('urllib.request.urlopen')
    def test_send_request_body_format(self, mock_urlopen, api, mock_response):
        """Test that request body is properly formatted"""
        mock_urlopen.return_value = mock_response
        
        operation = "testOperation"
        variables = {"key": "value", "num": 123}
        query = "query testQuery { field }"
        
        api.send(operation, variables, query)
        
        # Get the request that was made
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        
        # Decode and verify the request body
        body = json.loads(request.data.decode('ascii'))
        assert body["operationName"] == operation
        assert body["variables"] == variables
        assert body["query"] == query


class TestContainerAddIpRange:
    """Test container_add_ip_range method"""
    
    @pytest.fixture
    def api(self):
        """Create API instance for testing"""
        return API(key="test_key", account_id="default_account", cache_enabled=False)
    
    @pytest.fixture
    def api_no_cache(self):
        """Create API instance with cache disabled"""
        return API(key="test_key", account_id="default_account", cache_enabled=False)
    
    @patch.object(API, 'send')
    def test_container_add_ip_range_with_explicit_account(self, mock_send, api):
        """Test container_add_ip_range with explicitly provided account_id"""
        mock_send.return_value = {"data": {"container": {"addIpRange": {"success": True}}}}
        
        result = api.container_add_ip_range(
            container_name="Test Container",
            from_ip="192.168.1.1",
            to_ip="192.168.1.10",
            account_id="explicit_account"
        )
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        operation, variables, query = call_args
        
        assert operation == "addIpRangeToContainer"
        assert variables["accountId"] == "explicit_account"
        assert variables["input"]["ref"]["by"] == "NAME"
        assert variables["input"]["ref"]["input"] == "Test Container"
        assert variables["input"]["values"][0]["from"] == "192.168.1.1"
        assert variables["input"]["values"][0]["to"] == "192.168.1.10"
        assert "mutation addIpRangeToContainer" in query
    
    @patch.object(API, 'send')
    def test_container_add_ip_range_with_default_account(self, mock_send, api):
        """Test container_add_ip_range uses default account_id when not provided"""
        mock_send.return_value = {"data": {"container": {"addIpRange": {"success": True}}}}
        
        result = api.container_add_ip_range(
            container_name="Test Container",
            from_ip="10.0.0.1",
            to_ip="10.0.0.255"
        )
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        operation, variables, query = call_args
        
        assert variables["accountId"] == "default_account"
        assert variables["input"]["ref"]["input"] == "Test Container"
        assert variables["input"]["values"][0]["from"] == "10.0.0.1"
        assert variables["input"]["values"][0]["to"] == "10.0.0.255"
    
    @patch.object(API, 'send')
    def test_container_add_ip_range_single_ip(self, mock_send, api):
        """Test container_add_ip_range with same from_ip and to_ip (single IP)"""
        mock_send.return_value = {"data": {"container": {"addIpRange": {"success": True}}}}
        
        result = api.container_add_ip_range(
            container_name="Single IP Container",
            from_ip="172.16.0.1",
            to_ip="172.16.0.1"
        )
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        operation, variables, query = call_args
        
        assert variables["input"]["ref"]["input"] == "Single IP Container"
        assert variables["input"]["values"][0]["from"] == "172.16.0.1"
        assert variables["input"]["values"][0]["to"] == "172.16.0.1"
    
    @patch.object(API, 'send')
    def test_container_add_ip_range_propagates_exceptions(self, mock_send, api_no_cache):
        """Test that container_add_ip_range propagates exceptions from send()"""
        mock_send.side_effect = CatoNetworkError("Network error")
        
        with pytest.raises(CatoNetworkError, match="Network error"):
            api_no_cache.container_add_ip_range(
                container_name="Test Container",
                from_ip="192.168.1.1",
                to_ip="192.168.1.10"
            )
    
    @patch.object(API, 'send')
    def test_container_add_ip_range_propagates_graphql_errors(self, mock_send, api_no_cache):
        """Test that container_add_ip_range propagates GraphQL errors from send()"""
        mock_send.side_effect = CatoGraphQLError([{"message": "Container not found"}])
        
        with pytest.raises(CatoGraphQLError):
            api_no_cache.container_add_ip_range(
                container_name="NonExistent Container",
                from_ip="192.168.1.1",
                to_ip="192.168.1.10"
            )
    
    @patch.object(API, 'send')
    def test_container_add_ip_range_variable_structure(self, mock_send, api):
        """Test that variables are properly structured"""
        mock_send.return_value = {"data": {}}
        
        api.container_add_ip_range(
            container_name="Variable Test Container",
            from_ip="203.0.113.1",
            to_ip="203.0.113.100",
            account_id="test_account"
        )
        
        call_args = mock_send.call_args[0]
        operation, variables, query = call_args
        
        # Verify all required variables are present
        assert "accountId" in variables
        assert "input" in variables
        assert "ref" in variables["input"]
        assert "values" in variables["input"]
        
        # Verify nested structure
        assert variables["input"]["ref"]["by"] == "NAME"
        assert variables["input"]["ref"]["input"] == "Variable Test Container"
        
        # Verify variable values
        assert variables["accountId"] == "test_account"
        assert variables["input"]["values"][0]["from"] == "203.0.113.1"
        assert variables["input"]["values"][0]["to"] == "203.0.113.100"


class TestContainerAddFqdns:
    """Test container_add_fqdns method"""
    
    @pytest.fixture
    def api(self):
        """Create API instance for testing"""
        return API(key="test_key", account_id="default_account", cache_enabled=False)
    
    @pytest.fixture
    def api_no_cache(self):
        """Create API instance with cache disabled"""
        return API(key="test_key", account_id="default_account", cache_enabled=False)
    
    @patch.object(API, 'send')
    def test_container_add_fqdns_with_explicit_account(self, mock_send, api):
        """Test container_add_fqdns with explicitly provided account_id"""
        mock_send.return_value = {"data": {"container": {"fqdn": {"addValues": {"container": {"id": "123"}}}}}}
        
        result = api.container_add_fqdns(
            container_name="Test Container",
            fqdns=["example.com", "mail.google.com"],
            account_id="explicit_account"
        )
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        operation, variables, query = call_args
        
        assert operation == "addFqdnsToContainer"
        assert variables["accountId"] == "explicit_account"
        assert variables["input"]["ref"]["by"] == "NAME"
        assert variables["input"]["ref"]["input"] == "Test Container"
        assert variables["input"]["values"] == ["example.com", "mail.google.com"]
        assert "mutation addFqdnsToContainer" in query
    
    @patch.object(API, 'send')
    def test_container_add_fqdns_with_default_account(self, mock_send, api):
        """Test container_add_fqdns uses default account_id when not provided"""
        mock_send.return_value = {"data": {"container": {"fqdn": {"addValues": {"container": {"id": "123"}}}}}}
        
        result = api.container_add_fqdns(
            container_name="Test Container",
            fqdns=["api.github.com", "subdomain.example.org"]
        )
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        operation, variables, query = call_args
        
        assert variables["accountId"] == "default_account"
        assert variables["input"]["ref"]["input"] == "Test Container"
        assert variables["input"]["values"] == ["api.github.com", "subdomain.example.org"]
    
    @patch.object(API, 'send')
    def test_container_add_fqdns_single_domain(self, mock_send, api):
        """Test container_add_fqdns with single FQDN"""
        mock_send.return_value = {"data": {"container": {"fqdn": {"addValues": {"container": {"id": "123"}}}}}}
        
        result = api.container_add_fqdns(
            container_name="Single Domain Container",
            fqdns=["example.com"]
        )
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        operation, variables, query = call_args
        
        assert variables["input"]["ref"]["input"] == "Single Domain Container"
        assert variables["input"]["values"] == ["example.com"]
    
    @patch.object(API, 'send')
    def test_container_add_fqdns_multiple_domains(self, mock_send, api):
        """Test container_add_fqdns with multiple FQDNs"""
        mock_send.return_value = {"data": {"container": {"fqdn": {"addValues": {"container": {"id": "123"}}}}}}
        
        result = api.container_add_fqdns(
            container_name="Multiple Domains Container",
            fqdns=["cdn.example.com", "api.social.com", "service.internal.com"]
        )
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        operation, variables, query = call_args
        
        assert variables["input"]["values"] == ["cdn.example.com", "api.social.com", "service.internal.com"]
    
    @patch.object(API, 'send')
    def test_container_add_fqdns_propagates_exceptions(self, mock_send, api_no_cache):
        """Test that container_add_fqdns propagates exceptions from send()"""
        mock_send.side_effect = CatoNetworkError("Network error")
        
        with pytest.raises(CatoNetworkError, match="Network error"):
            api_no_cache.container_add_fqdns(
                container_name="Test Container",
                fqdns=["example.com"]
            )
    
    @patch.object(API, 'send')
    def test_container_add_fqdns_propagates_graphql_errors(self, mock_send, api_no_cache):
        """Test that container_add_fqdns propagates GraphQL errors from send()"""
        mock_send.side_effect = CatoGraphQLError([{"message": "Container not found"}])
        
        with pytest.raises(CatoGraphQLError):
            api_no_cache.container_add_fqdns(
                container_name="NonExistent Container",
                fqdns=["example.com"]
            )
    
    @patch.object(API, 'send')
    def test_container_add_fqdns_variable_structure(self, mock_send, api):
        """Test that variables are properly structured"""
        mock_send.return_value = {"data": {}}
        
        api.container_add_fqdns(
            container_name="Variable Test Container",
            fqdns=["test1.com", "test2.org", "api.test3.net"],
            account_id="test_account"
        )
        
        call_args = mock_send.call_args[0]
        operation, variables, query = call_args
        
        # Verify all required variables are present
        assert "accountId" in variables
        assert "input" in variables
        assert "ref" in variables["input"]
        assert "values" in variables["input"]
        
        # Verify nested structure
        assert variables["input"]["ref"]["by"] == "NAME"
        assert variables["input"]["ref"]["input"] == "Variable Test Container"
        
        # Verify variable values
        assert variables["accountId"] == "test_account"
        assert variables["input"]["values"] == ["test1.com", "test2.org", "api.test3.net"]
    
    @patch.object(API, 'send')
    def test_container_add_fqdns_query_structure(self, mock_send, api):
        """Test that the GraphQL query is properly structured"""
        mock_send.return_value = {"data": {}}
        
        api.container_add_fqdns(
            container_name="Query Test Container",
            fqdns=["example.com"]
        )
        
        call_args = mock_send.call_args[0]
        query = call_args[2]
        
        # Verify key parts of the query
        assert "mutation addFqdnsToContainer($accountId:ID!, $input:FqdnContainerAddValuesInput!)" in query
        assert "container(accountId: $accountId)" in query
        assert "fqdn {" in query
        assert "addValues(input: $input)" in query
        assert "container {" in query
        assert "__typename" in query
        assert "id" in query
        assert "name" in query
        assert "description" in query
        assert "size" in query
        assert "audit {" in query


class TestContainerList:
    """Test container_list method"""
    
    @pytest.fixture
    def api(self):
        """Create API instance for testing"""
        return API(key="test_key", account_id="default_account")
    
    @patch.object(API, 'send')
    def test_container_list_with_explicit_account(self, mock_send, api):
        """Test container_list with explicitly provided account_id"""
        mock_send.return_value = {"data": {"container": {"list": {"containers": []}}}}
        
        result = api.container_list("explicit_account")
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        operation, variables, query = call_args
        
        assert operation == "listContainers"
        assert variables["accountId"] == "explicit_account"
        assert "input" in variables
        assert "query listContainers" in query
    
    @patch.object(API, 'send')
    def test_container_list_with_default_account(self, mock_send, api):
        """Test container_list uses default account_id when not provided"""
        mock_send.return_value = {"data": {"container": {"list": {"containers": []}}}}
        
        result = api.container_list()
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        operation, variables, query = call_args
        
        assert variables["accountId"] == "default_account"
    
    @patch.object(API, 'send')
    def test_container_list_propagates_exceptions(self, mock_send, api):
        """Test that container_list propagates exceptions from send()"""
        mock_send.side_effect = CatoNetworkError("Network error")
        
        with pytest.raises(CatoNetworkError, match="Network error"):
            api.container_list()
    
    @patch.object(API, 'send')
    def test_container_list_query_structure(self, mock_send, api):
        """Test that the GraphQL query is properly structured"""
        mock_send.return_value = {"data": {}}
        
        api.container_list()
        
        call_args = mock_send.call_args[0]
        query = call_args[2]
        
        # Verify key parts of the query
        assert "query listContainers($accountId:ID!, $input:ContainerSearchInput!)" in query
        assert "container(accountId: $accountId)" in query
        assert "list(input: $input)" in query
        assert "containers {" in query
        assert "id" in query
        assert "name" in query
        assert "description" in query


class TestIntegration:
    """Integration tests that use real API (skipped if no credentials)"""
    
    @pytest.fixture
    def has_credentials(self):
        """Check if .env credentials are available"""
        return (
            os.environ.get('CATO_API_KEY') and 
            os.environ.get('CATO_ACCOUNT_ID')
        )
    
    @pytest.fixture
    def api_with_env_credentials(self):
        """Create API instance using environment credentials"""
        try:
            return API()
        except ValueError:
            return None
    
    @pytest.fixture
    def unique_container_name(self):
        """Generate a unique container name with timestamp"""
        import time
        timestamp = int(time.time())
        return f"pytest_test_container_{timestamp}"
    
    def test_container_list_with_real_api(self, has_credentials, api_with_env_credentials):
        """Test container_list with real API call using .env credentials"""
        if not has_credentials or not api_with_env_credentials:
            pytest.skip("Skipping integration test - no credentials in .env")
        
        # Make real API call
        try:
            result = api_with_env_credentials.container_list()
            
            # Verify response structure
            assert isinstance(result, dict)
            assert 'data' in result or 'errors' in result
            
            if 'data' in result:
                # Successful response should have expected structure
                assert 'container' in result['data']
                container_data = result['data']['container']
                
                if container_data:  # API might return null for empty results
                    assert 'list' in container_data
                    list_data = container_data['list']
                    
                    if list_data:
                        assert 'containers' in list_data
                        containers = list_data['containers']
                        
                        # If there are containers, verify their structure
                        if containers and len(containers) > 0:
                            first_container = containers[0]
                            
                            # Check for expected fields
                            expected_fields = ['id', 'name', 'description', 'size']
                            for field in expected_fields:
                                assert field in first_container, f"Missing field: {field}"
                            
                            # Check audit field if present
                            if 'audit' in first_container:
                                audit = first_container['audit']
                                audit_fields = ['createdBy', 'createdAt', 'lastModifiedBy', 'lastModifiedAt']
                                for field in audit_fields:
                                    assert field in audit, f"Missing audit field: {field}"
                        
                        print(f"\n✓ Successfully retrieved {len(containers)} container(s)")
                    else:
                        print("\n✓ API call successful but no list data returned")
                else:
                    print("\n✓ API call successful but no container data returned")
            
            elif 'errors' in result:
                # This might be expected if account has no permissions
                print(f"\n⚠ API returned errors: {result['errors']}")
                # Still pass the test as the API call itself worked
                assert isinstance(result['errors'], list)
        
        except CatoGraphQLError as e:
            # GraphQL errors might be expected (e.g., no permissions)
            print(f"\n⚠ GraphQL error (may be expected): {e}")
            assert hasattr(e, 'errors')
            assert isinstance(e.errors, list)
            
        except CatoNetworkError as e:
            pytest.fail(f"Network error during API call: {e}")
    
    def test_missing_env_credentials_behavior(self):
        """Test behavior when .env file exists but is missing credentials"""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure no credentials in environment
            with pytest.raises(ValueError, match="API key is required"):
                API()
    
    def test_container_create_and_delete_lifecycle(self, has_credentials, api_with_env_credentials, unique_container_name):
        """Test complete container lifecycle: create -> verify -> delete"""
        if not has_credentials or not api_with_env_credentials:
            pytest.skip("Skipping integration test - no credentials in .env")
        
        created_container = None
        
        try:
            # Create container with test IPs
            test_ips = ["192.168.100.1", "10.1.0.0/24", "172.16.5.10"]
            print(f"\n🏗️  Creating test container: {unique_container_name}")
            
            create_response = api_with_env_credentials.container_create_ip(
                name=unique_container_name,
                description="Integration test container - safe to delete",
                ip_addresses=test_ips
            )
            
            # Verify creation response structure
            assert isinstance(create_response, dict)
            assert 'data' in create_response
            
            container_data = create_response['data']['container']['ipAddressRange']['createFromFile']['container']
            created_container = container_data
            
            # Verify container was created with expected properties
            assert container_data['name'] == unique_container_name
            assert container_data['description'] == "Integration test container - safe to delete"
            assert 'id' in container_data
            assert 'audit' in container_data
            
            container_id = container_data['id']
            container_size = container_data.get('size', 0)
            
            print(f"✅ Container created successfully!")
            print(f"   ID: {container_id}")
            print(f"   Name: {container_data['name']}")
            print(f"   Size: {container_size} items")
            
            # Verify the container appears in the list
            print(f"📋 Verifying container appears in list...")
            list_response = api_with_env_credentials.container_list()
            
            assert 'data' in list_response
            containers = list_response['data']['container']['list']['containers']
            
            # Find our container in the list
            found_container = None
            for container in containers:
                if container['name'] == unique_container_name:
                    found_container = container
                    break
            
            assert found_container is not None, f"Created container {unique_container_name} not found in list"
            assert found_container['id'] == container_id
            print(f"✅ Container found in list with correct ID")
            
            # Add additional IP ranges to test container_add_ip_range
            print(f"➕ Adding additional IP ranges to container...")
            initial_size = container_size
            
            add_response = api_with_env_credentials.container_add_ip_range(
                container_name=unique_container_name,
                from_ip="203.0.113.1", 
                to_ip="203.0.113.50"
            )
            
            # Verify add response structure
            assert isinstance(add_response, dict)
            assert 'data' in add_response
            
            add_container_data = add_response['data']['container']['ipAddressRange']['addValues']['container']
            new_size = add_container_data.get('size', 0)
            
            print(f"✅ IP range added successfully!")
            print(f"   Size before: {initial_size} items")
            print(f"   Size after:  {new_size} items")
            print(f"   Added range: 203.0.113.1 - 203.0.113.50")
            
            # Verify size increased (should be at least initial_size + 1)
            assert new_size > initial_size, f"Container size should have increased from {initial_size} to more than {initial_size}, but got {new_size}"
            
            # Add another single IP to further test
            print(f"➕ Adding single IP to container...")
            
            add_single_response = api_with_env_credentials.container_add_ip_range(
                container_name=unique_container_name,
                from_ip="198.51.100.100",
                to_ip="198.51.100.100"  # Same IP = single IP
            )
            
            add_single_container_data = add_single_response['data']['container']['ipAddressRange']['addValues']['container']
            final_size = add_single_container_data.get('size', 0)
            
            print(f"✅ Single IP added successfully!")
            print(f"   Size after single IP: {final_size} items")
            print(f"   Added IP: 198.51.100.100")
            
            # Verify size increased again
            assert final_size > new_size, f"Container size should have increased from {new_size} to more than {new_size}, but got {final_size}"
            
            # Verify the final container appears correctly in the list with new size
            print(f"📋 Verifying updated container in list...")
            list_response_updated = api_with_env_credentials.container_list()
            containers_updated = list_response_updated['data']['container']['list']['containers']
            
            found_updated_container = None
            for container in containers_updated:
                if container['name'] == unique_container_name:
                    found_updated_container = container
                    break
            
            assert found_updated_container is not None
            listed_size = found_updated_container.get('size', 0)
            print(f"✅ Updated container found in list with size: {listed_size}")
            assert listed_size == final_size, f"Listed size {listed_size} should match final size {final_size}"
            
            # Delete the container
            print(f"🗑️  Deleting test container: {unique_container_name}")
            delete_response = api_with_env_credentials.container_delete(name=unique_container_name)
            
            # Verify deletion response
            assert isinstance(delete_response, dict)
            assert 'data' in delete_response
            
            deleted_container = delete_response['data']['container']['delete']['container']
            
            # Verify the deleted container info matches what we created
            assert deleted_container['name'] == unique_container_name
            assert deleted_container['id'] == container_id
            print(f"✅ Container deleted successfully!")
            
            # Verify container no longer appears in list
            print(f"📋 Verifying container no longer in list...")
            list_response_after = api_with_env_credentials.container_list()
            containers_after = list_response_after['data']['container']['list']['containers']
            
            # Container should not be found
            found_after_delete = any(c['name'] == unique_container_name for c in containers_after)
            assert not found_after_delete, f"Container {unique_container_name} still exists after deletion"
            print(f"✅ Container successfully removed from list")
            
            print(f"\n🎉 Complete lifecycle test passed!")
            print(f"   Created container with {len(test_ips)} initial IP addresses")
            print(f"   Added IP range (203.0.113.1-50) - size increased to {new_size}")
            print(f"   Added single IP (198.51.100.100) - size increased to {final_size}")
            print(f"   Verified container and size updates in list")
            print(f"   Successfully deleted container")
            print(f"   Verified removal from list")
            
            # Mark as successfully deleted so cleanup doesn't try again
            created_container = None
            
        except CatoGraphQLError as e:
            # Handle expected errors (like permission issues)
            error_messages = [str(error) if isinstance(error, str) else error.get('message', str(error)) 
                            for error in e.errors]
            
            if any('permission' in msg.lower() or 'denied' in msg.lower() for msg in error_messages):
                pytest.skip(f"Skipping lifecycle test - insufficient permissions: {error_messages}")
            else:
                # Re-raise unexpected GraphQL errors
                print(f"❌ GraphQL error during lifecycle test: {e}")
                raise
        
        except Exception as e:
            print(f"❌ Unexpected error during lifecycle test: {e}")
            raise
        
        finally:
            # Cleanup: try to delete the container if it was created but test failed
            if created_container and api_with_env_credentials:
                try:
                    print(f"🧹 Cleanup: attempting to delete test container {unique_container_name}")
                    api_with_env_credentials.container_delete(name=unique_container_name)
                    print(f"✅ Cleanup successful")
                except Exception as cleanup_error:
                    print(f"⚠️  Cleanup failed (container may still exist): {cleanup_error}")
    
    def test_container_create_empty_and_delete(self, has_credentials, api_with_env_credentials, unique_container_name):
        """Test lifecycle with empty container (no IPs)"""
        if not has_credentials or not api_with_env_credentials:
            pytest.skip("Skipping integration test - no credentials in .env")
        
        # Modify name for empty container test
        empty_container_name = f"{unique_container_name}_empty"
        created_container = None
        
        try:
            print(f"\n🏗️  Creating empty test container: {empty_container_name}")
            
            # Create container without IPs
            create_response = api_with_env_credentials.container_create_ip(
                name=empty_container_name,
                description="Empty integration test container"
                # No ip_addresses parameter = empty container
            )
            
            # Verify creation
            assert isinstance(create_response, dict)
            assert 'data' in create_response
            
            container_data = create_response['data']['container']['ipAddressRange']['createFromFile']['container']
            created_container = container_data
            
            assert container_data['name'] == empty_container_name
            container_size = container_data.get('size', 0)
            print(f"✅ Empty container created (size: {container_size})")
            
            # Delete the container
            print(f"🗑️  Deleting empty test container: {empty_container_name}")
            delete_response = api_with_env_credentials.container_delete(name=empty_container_name)
            
            assert 'data' in delete_response
            deleted_container = delete_response['data']['container']['delete']['container']
            assert deleted_container['name'] == empty_container_name
            
            print(f"✅ Empty container lifecycle test passed!")
            created_container = None
            
        except CatoGraphQLError as e:
            error_messages = [str(error) if isinstance(error, str) else error.get('message', str(error)) 
                            for error in e.errors]
            
            if any('permission' in msg.lower() or 'denied' in msg.lower() for msg in error_messages):
                pytest.skip(f"Skipping empty container test - insufficient permissions: {error_messages}")
            else:
                raise
        
        finally:
            # Cleanup
            if created_container and api_with_env_credentials:
                try:
                    print(f"🧹 Cleanup: attempting to delete {empty_container_name}")
                    api_with_env_credentials.container_delete(name=empty_container_name)
                except Exception:
                    pass  # Ignore cleanup errors
    
    def test_fqdn_container_create_and_delete_lifecycle(self, has_credentials, api_with_env_credentials, unique_container_name):
        """Test complete FQDN container lifecycle: create -> verify -> delete"""
        if not has_credentials or not api_with_env_credentials:
            pytest.skip("Skipping integration test - no credentials in .env")
        
        # Modify name for FQDN container test
        fqdn_container_name = f"{unique_container_name}_fqdn"
        created_container = None
        
        try:
            # Create container with test FQDNs
            test_fqdns = ["example.com", "test.local", "api.github.com", "subdomain.example.org"]
            print(f"\n🏗️  Creating test FQDN container: {fqdn_container_name}")
            
            create_response = api_with_env_credentials.container_create_fqdn(
                name=fqdn_container_name,
                description="FQDN integration test container - safe to delete",
                fqdns=test_fqdns
            )
            
            # Verify creation response structure
            assert isinstance(create_response, dict)
            assert 'data' in create_response
            
            container_data = create_response['data']['container']['fqdn']['createFromFile']['container']
            created_container = container_data
            
            # Verify container was created with expected properties
            assert container_data['name'] == fqdn_container_name
            assert container_data['description'] == "FQDN integration test container - safe to delete"
            assert 'id' in container_data
            assert 'audit' in container_data
            assert container_data.get('__typename') == 'FqdnContainer'
            
            container_id = container_data['id']
            container_size = container_data.get('size', 0)
            
            print(f"✅ FQDN Container created successfully!")
            print(f"   ID: {container_id}")
            print(f"   Name: {container_data['name']}")
            print(f"   Type: {container_data.get('__typename', 'N/A')}")
            print(f"   Size: {container_size} items")
            
            # Verify the container appears in the list
            print(f"📋 Verifying FQDN container appears in list...")
            list_response = api_with_env_credentials.container_list()
            
            assert 'data' in list_response
            containers = list_response['data']['container']['list']['containers']
            
            # Find our container in the list
            found_container = None
            for container in containers:
                if container['name'] == fqdn_container_name:
                    found_container = container
                    break
            
            assert found_container is not None, f"Created FQDN container {fqdn_container_name} not found in list"
            assert found_container['id'] == container_id
            print(f"✅ FQDN Container found in list with correct ID")
            
            # Add additional FQDNs to test container_add_fqdns
            print(f"➕ Adding additional FQDNs to container...")
            initial_size = container_size
            
            additional_fqdns = ["mail.example.com", "ftp.example.com", "blog.test-domain.org"]
            
            add_response = api_with_env_credentials.container_add_fqdns(
                container_name=fqdn_container_name,
                fqdns=additional_fqdns
            )
            
            # Verify add response structure
            assert isinstance(add_response, dict)
            assert 'data' in add_response
            
            add_container_data = add_response['data']['container']['fqdn']['addValues']['container']
            new_size = add_container_data.get('size', 0)
            
            print(f"✅ FQDNs added successfully!")
            print(f"   Size before: {initial_size} items")
            print(f"   Size after:  {new_size} items")
            print(f"   Added FQDNs: {', '.join(additional_fqdns)}")
            
            # Verify size increased (should be initial_size + len(additional_fqdns))
            expected_new_size = initial_size + len(additional_fqdns)
            assert new_size >= expected_new_size, f"Container size should have increased from {initial_size} to at least {expected_new_size}, but got {new_size}"
            
            # Add more FQDNs
            print(f"➕ Adding more FQDNs to container...")
            
            more_fqdns = ["cdn.example.com", "api.service.local"]
            
            add_more_response = api_with_env_credentials.container_add_fqdns(
                container_name=fqdn_container_name,
                fqdns=more_fqdns
            )
            
            add_more_container_data = add_more_response['data']['container']['fqdn']['addValues']['container']
            final_size = add_more_container_data.get('size', 0)
            
            print(f"✅ More FQDNs added successfully!")
            print(f"   Size after more FQDNs: {final_size} items")
            print(f"   Added FQDNs: {', '.join(more_fqdns)}")
            
            # Verify size increased again
            expected_final_size = new_size + len(more_fqdns)
            assert final_size >= expected_final_size, f"Container size should have increased from {new_size} to at least {expected_final_size}, but got {final_size}"
            
            # Verify the final container appears correctly in the list with new size
            print(f"📋 Verifying updated FQDN container in list...")
            list_response_updated = api_with_env_credentials.container_list()
            containers_updated = list_response_updated['data']['container']['list']['containers']
            
            found_updated_container = None
            for container in containers_updated:
                if container['name'] == fqdn_container_name:
                    found_updated_container = container
                    break
            
            assert found_updated_container is not None
            listed_size = found_updated_container.get('size', 0)
            print(f"✅ Updated FQDN container found in list with size: {listed_size}")
            assert listed_size == final_size, f"Listed size {listed_size} should match final size {final_size}"
            
            # Delete the container
            print(f"🗑️  Deleting test FQDN container: {fqdn_container_name}")
            delete_response = api_with_env_credentials.container_delete(name=fqdn_container_name)
            
            # Verify deletion response
            assert isinstance(delete_response, dict)
            assert 'data' in delete_response
            
            deleted_container = delete_response['data']['container']['delete']['container']
            
            # Verify the deleted container info matches what we created
            assert deleted_container['name'] == fqdn_container_name
            assert deleted_container['id'] == container_id
            print(f"✅ FQDN Container deleted successfully!")
            
            # Verify container no longer appears in list
            print(f"📋 Verifying FQDN container no longer in list...")
            list_response_after = api_with_env_credentials.container_list()
            containers_after = list_response_after['data']['container']['list']['containers']
            
            # Container should not be found
            found_after_delete = any(c['name'] == fqdn_container_name for c in containers_after)
            assert not found_after_delete, f"FQDN Container {fqdn_container_name} still exists after deletion"
            print(f"✅ FQDN Container successfully removed from list")
            
            print(f"\n🎉 Complete FQDN lifecycle test passed!")
            print(f"   Created FQDN container with {len(test_fqdns)} initial domains")
            print(f"   Added {len(additional_fqdns)} FQDNs - size increased to {new_size}")
            print(f"   Added {len(more_fqdns)} more FQDNs - size increased to {final_size}")
            print(f"   Verified container and size updates in list")
            print(f"   Successfully deleted container")
            print(f"   Verified removal from list")
            
            # Mark as successfully deleted so cleanup doesn't try again
            created_container = None
            
        except CatoGraphQLError as e:
            # Handle expected errors (like permission issues)
            error_messages = [str(error) if isinstance(error, str) else error.get('message', str(error)) 
                            for error in e.errors]
            
            if any('permission' in msg.lower() or 'denied' in msg.lower() for msg in error_messages):
                pytest.skip(f"Skipping FQDN lifecycle test - insufficient permissions: {error_messages}")
            else:
                # Re-raise unexpected GraphQL errors
                print(f"❌ GraphQL error during FQDN lifecycle test: {e}")
                raise
        
        except Exception as e:
            print(f"❌ Unexpected error during FQDN lifecycle test: {e}")
            raise
        
        finally:
            # Cleanup: try to delete the container if it was created but test failed
            if created_container and api_with_env_credentials:
                try:
                    print(f"🧹 Cleanup: attempting to delete test FQDN container {fqdn_container_name}")
                    api_with_env_credentials.container_delete(name=fqdn_container_name)
                    print(f"✅ Cleanup successful")
                except Exception as cleanup_error:
                    print(f"⚠️  Cleanup failed (FQDN container may still exist): {cleanup_error}")
    
    def test_fqdn_container_create_empty_and_delete(self, has_credentials, api_with_env_credentials, unique_container_name):
        """Test FQDN lifecycle with empty container (no FQDNs)"""
        if not has_credentials or not api_with_env_credentials:
            pytest.skip("Skipping integration test - no credentials in .env")
        
        # Modify name for empty FQDN container test
        empty_fqdn_name = f"{unique_container_name}_fqdn_empty"
        created_container = None
        
        try:
            print(f"\n🏗️  Creating empty test FQDN container: {empty_fqdn_name}")
            
            # Create container without FQDNs
            create_response = api_with_env_credentials.container_create_fqdn(
                name=empty_fqdn_name,
                description="Empty FQDN integration test container"
                # No fqdns parameter = empty container
            )
            
            # Verify creation
            assert isinstance(create_response, dict)
            assert 'data' in create_response
            
            container_data = create_response['data']['container']['fqdn']['createFromFile']['container']
            created_container = container_data
            
            assert container_data['name'] == empty_fqdn_name
            assert container_data.get('__typename') == 'FqdnContainer'
            container_size = container_data.get('size', 0)
            print(f"✅ Empty FQDN container created (size: {container_size})")
            
            # Delete the container
            print(f"🗑️  Deleting empty test FQDN container: {empty_fqdn_name}")
            delete_response = api_with_env_credentials.container_delete(name=empty_fqdn_name)
            
            assert 'data' in delete_response
            deleted_container = delete_response['data']['container']['delete']['container']
            assert deleted_container['name'] == empty_fqdn_name
            
            print(f"✅ Empty FQDN container lifecycle test passed!")
            created_container = None
            
        except CatoGraphQLError as e:
            error_messages = [str(error) if isinstance(error, str) else error.get('message', str(error)) 
                            for error in e.errors]
            
            if any('permission' in msg.lower() or 'denied' in msg.lower() for msg in error_messages):
                pytest.skip(f"Skipping empty FQDN container test - insufficient permissions: {error_messages}")
            else:
                raise
        
        finally:
            # Cleanup
            if created_container and api_with_env_credentials:
                try:
                    print(f"🧹 Cleanup: attempting to delete {empty_fqdn_name}")
                    api_with_env_credentials.container_delete(name=empty_fqdn_name)
                except Exception:
                    pass  # Ignore cleanup errors
    
    def test_ip_container_full_lifecycle_with_remove_and_cache(self, has_credentials, api_with_env_credentials, unique_container_name):
        """Test complete IP container lifecycle: create, add, remove, delete with cache verification"""
        if not has_credentials or not api_with_env_credentials:
            pytest.skip("Skipping integration test - no credentials in .env")
        
        container_name = f"{unique_container_name}_ip_lifecycle"
        created_container = False
        
        print(f"\n🧪 Testing full IP container lifecycle with remove: {container_name}")
        
        try:
            # Step 1: Create IP container
            print("Step 1: Creating IP container...")
            create_response = api_with_env_credentials.container_create_ip(
                name=container_name,
                description="Test IP container for remove operations"
            )
            created_container = True
            
            assert 'data' in create_response
            container_data = create_response['data']['container']['ipAddressRange']['createFromFile']['container']
            assert container_data['name'] == container_name
            initial_size = container_data.get('size', 0)
            assert initial_size == 0, "New container should be empty"
            print(f"✓ Created container with size: {initial_size}")
            
            # Verify cache metadata if cache is enabled
            if api_with_env_credentials._cache:
                cache_stats = api_with_env_credentials.container_cache_stats(container_name)
                assert cache_stats['cached_ip_ranges'] == 0, "Cache should be empty for new container"
                print(f"✓ Cache verified: {cache_stats['cached_ip_ranges']} IP ranges")
            
            # Step 2: Add first IP range
            print("\nStep 2: Adding first IP range...")
            add_response1 = api_with_env_credentials.container_add_ip_range(
                container_name=container_name,
                from_ip="192.168.1.1",
                to_ip="192.168.1.10"
            )
            
            assert 'data' in add_response1
            container_data = add_response1['data']['container']['ipAddressRange']['addValues']['container']
            size_after_add1 = container_data.get('size', 0)
            assert size_after_add1 > initial_size, "Container size should increase after adding IP range"
            print(f"✓ Added IP range 192.168.1.1-10, container size: {size_after_add1}")
            
            # Verify cache
            if api_with_env_credentials._cache:
                cache_stats = api_with_env_credentials.container_cache_stats(container_name)
                assert cache_stats['cached_ip_ranges'] == 1, "Cache should have 1 IP range"
                assert cache_stats['api_size'] == size_after_add1, "Cache size should match API size"
                print(f"✓ Cache verified: {cache_stats['cached_ip_ranges']} IP ranges, size matches API")
            
            # Step 3: Add second IP range
            print("\nStep 3: Adding second IP range...")
            add_response2 = api_with_env_credentials.container_add_ip_range(
                container_name=container_name,
                from_ip="10.0.0.1",
                to_ip="10.0.0.100"
            )
            
            assert 'data' in add_response2
            container_data = add_response2['data']['container']['ipAddressRange']['addValues']['container']
            size_after_add2 = container_data.get('size', 0)
            assert size_after_add2 > size_after_add1, "Container size should increase after adding second IP range"
            print(f"✓ Added IP range 10.0.0.1-100, container size: {size_after_add2}")
            
            # Verify cache
            if api_with_env_credentials._cache:
                cache_stats = api_with_env_credentials.container_cache_stats(container_name)
                assert cache_stats['cached_ip_ranges'] == 2, "Cache should have 2 IP ranges"
                assert cache_stats['api_size'] == size_after_add2, "Cache size should match API size"
                print(f"✓ Cache verified: {cache_stats['cached_ip_ranges']} IP ranges, size matches API")
            
            # Step 4: Remove first IP range
            print("\nStep 4: Removing first IP range...")
            remove_response1 = api_with_env_credentials.container_remove_ip_range(
                container_name=container_name,
                from_ip="192.168.1.1",
                to_ip="192.168.1.10"
            )
            
            assert 'data' in remove_response1
            container_data = remove_response1['data']['container']['ipAddressRange']['removeValues']['container']
            size_after_remove1 = container_data.get('size', 0)
            assert size_after_remove1 < size_after_add2, "Container size should decrease after removing IP range"
            assert size_after_remove1 == size_after_add1, "Size should match after removing one of two ranges"
            print(f"✓ Removed IP range 192.168.1.1-10, container size: {size_after_remove1}")
            
            # Verify cache
            if api_with_env_credentials._cache:
                cache_stats = api_with_env_credentials.container_cache_stats(container_name)
                assert cache_stats['cached_ip_ranges'] == 1, "Cache should have 1 IP range after removal"
                assert cache_stats['api_size'] == size_after_remove1, "Cache size should match API size after removal"
                print(f"✓ Cache verified: {cache_stats['cached_ip_ranges']} IP ranges, size matches API")
                
                # Verify the correct range was removed
                cached_values = api_with_env_credentials.container_list_cached_values(container_name)
                if 'ip_ranges' in cached_values:
                    cached_ips = [(r['from_ip'], r['to_ip']) for r in cached_values['ip_ranges']]
                    assert ("192.168.1.1", "192.168.1.10") not in cached_ips, "Removed range should not be in cache"
                    assert ("10.0.0.1", "10.0.0.100") in cached_ips, "Remaining range should be in cache"
                    print("✓ Cache contents verified: correct IP range removed")
            
            # Step 5: Remove second IP range
            print("\nStep 5: Removing second IP range...")
            remove_response2 = api_with_env_credentials.container_remove_ip_range(
                container_name=container_name,
                from_ip="10.0.0.1",
                to_ip="10.0.0.100"
            )
            
            assert 'data' in remove_response2
            container_data = remove_response2['data']['container']['ipAddressRange']['removeValues']['container']
            size_after_remove2 = container_data.get('size', 0)
            assert size_after_remove2 == 0, "Container should be empty after removing all IP ranges"
            print(f"✓ Removed IP range 10.0.0.1-100, container size: {size_after_remove2}")
            
            # Verify cache is empty
            if api_with_env_credentials._cache:
                cache_stats = api_with_env_credentials.container_cache_stats(container_name)
                assert cache_stats['cached_ip_ranges'] == 0, "Cache should be empty after removing all ranges"
                assert cache_stats['api_size'] == size_after_remove2, "Cache size should match API size (0)"
                print(f"✓ Cache verified: {cache_stats['cached_ip_ranges']} IP ranges, container empty")
            
            # Step 6: Delete container
            print("\nStep 6: Deleting container...")
            delete_response = api_with_env_credentials.container_delete(name=container_name)
            created_container = False
            
            assert 'data' in delete_response
            print(f"✓ Container {container_name} deleted successfully")
            
            # Verify container list no longer includes it
            list_response = api_with_env_credentials.container_list()
            if 'data' in list_response:
                containers = list_response['data']['container']['list']['containers']
                container_names = [c['name'] for c in containers]
                assert container_name not in container_names, "Container should not exist after deletion"
                print("✓ Verified container no longer exists")
            
            print(f"\n✅ Full IP container lifecycle test passed for {container_name}")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            raise
        finally:
            # Cleanup if needed
            if created_container and api_with_env_credentials:
                try:
                    print(f"🧹 Cleanup: attempting to delete {container_name}")
                    api_with_env_credentials.container_delete(name=container_name)
                except Exception:
                    pass  # Ignore cleanup errors
    
    def test_fqdn_container_full_lifecycle_with_remove_and_cache(self, has_credentials, api_with_env_credentials, unique_container_name):
        """Test complete FQDN container lifecycle: create, add, remove, delete with cache verification"""
        if not has_credentials or not api_with_env_credentials:
            pytest.skip("Skipping integration test - no credentials in .env")
        
        container_name = f"{unique_container_name}_fqdn_lifecycle"
        created_container = False
        
        print(f"\n🧪 Testing full FQDN container lifecycle with remove: {container_name}")
        
        try:
            # Step 1: Create FQDN container
            print("Step 1: Creating FQDN container...")
            create_response = api_with_env_credentials.container_create_fqdn(
                name=container_name,
                description="Test FQDN container for remove operations"
            )
            created_container = True
            
            assert 'data' in create_response
            container_data = create_response['data']['container']['fqdn']['createFromFile']['container']
            assert container_data['name'] == container_name
            initial_size = container_data.get('size', 0)
            assert initial_size == 0, "New container should be empty"
            print(f"✓ Created container with size: {initial_size}")
            
            # Verify cache metadata if cache is enabled
            if api_with_env_credentials._cache:
                cache_stats = api_with_env_credentials.container_cache_stats(container_name)
                assert cache_stats['cached_fqdns'] == 0, "Cache should be empty for new container"
                print(f"✓ Cache verified: {cache_stats['cached_fqdns']} FQDNs")
            
            # Step 2: Add first batch of FQDNs
            print("\nStep 2: Adding first batch of FQDNs...")
            fqdns_batch1 = ["example.com", "test.example.com", "api.example.com"]
            add_response1 = api_with_env_credentials.container_add_fqdns(
                container_name=container_name,
                fqdns=fqdns_batch1
            )
            
            assert 'data' in add_response1
            container_data = add_response1['data']['container']['fqdn']['addValues']['container']
            size_after_add1 = container_data.get('size', 0)
            assert size_after_add1 == len(fqdns_batch1), f"Container size should be {len(fqdns_batch1)} after adding FQDNs"
            print(f"✓ Added {len(fqdns_batch1)} FQDNs, container size: {size_after_add1}")
            
            # Verify cache
            if api_with_env_credentials._cache:
                cache_stats = api_with_env_credentials.container_cache_stats(container_name)
                assert cache_stats['cached_fqdns'] == len(fqdns_batch1), f"Cache should have {len(fqdns_batch1)} FQDNs"
                assert cache_stats['api_size'] == size_after_add1, "Cache size should match API size"
                print(f"✓ Cache verified: {cache_stats['cached_fqdns']} FQDNs, size matches API")
            
            # Step 3: Add second batch of FQDNs
            print("\nStep 3: Adding second batch of FQDNs...")
            fqdns_batch2 = ["google.com", "mail.google.com", "github.com"]
            add_response2 = api_with_env_credentials.container_add_fqdns(
                container_name=container_name,
                fqdns=fqdns_batch2
            )
            
            assert 'data' in add_response2
            container_data = add_response2['data']['container']['fqdn']['addValues']['container']
            size_after_add2 = container_data.get('size', 0)
            expected_size = len(fqdns_batch1) + len(fqdns_batch2)
            assert size_after_add2 == expected_size, f"Container size should be {expected_size} after adding second batch"
            print(f"✓ Added {len(fqdns_batch2)} FQDNs, container size: {size_after_add2}")
            
            # Verify cache
            if api_with_env_credentials._cache:
                cache_stats = api_with_env_credentials.container_cache_stats(container_name)
                assert cache_stats['cached_fqdns'] == expected_size, f"Cache should have {expected_size} FQDNs"
                assert cache_stats['api_size'] == size_after_add2, "Cache size should match API size"
                print(f"✓ Cache verified: {cache_stats['cached_fqdns']} FQDNs, size matches API")
            
            # Step 4: Remove first batch of FQDNs
            print("\nStep 4: Removing first batch of FQDNs...")
            remove_response1 = api_with_env_credentials.container_remove_fqdns(
                container_name=container_name,
                fqdns=fqdns_batch1
            )
            
            assert 'data' in remove_response1
            container_data = remove_response1['data']['container']['fqdn']['removeValues']['container']
            size_after_remove1 = container_data.get('size', 0)
            assert size_after_remove1 == len(fqdns_batch2), f"Container size should be {len(fqdns_batch2)} after removing first batch"
            print(f"✓ Removed {len(fqdns_batch1)} FQDNs, container size: {size_after_remove1}")
            
            # Verify cache
            if api_with_env_credentials._cache:
                cache_stats = api_with_env_credentials.container_cache_stats(container_name)
                assert cache_stats['cached_fqdns'] == len(fqdns_batch2), f"Cache should have {len(fqdns_batch2)} FQDNs after removal"
                assert cache_stats['api_size'] == size_after_remove1, "Cache size should match API size after removal"
                print(f"✓ Cache verified: {cache_stats['cached_fqdns']} FQDNs, size matches API")
                
                # Verify the correct FQDNs were removed
                cached_values = api_with_env_credentials.container_list_cached_values(container_name)
                if 'fqdns' in cached_values:
                    cached_fqdn_list = [f['fqdn'] for f in cached_values['fqdns']]
                    for removed_fqdn in fqdns_batch1:
                        assert removed_fqdn not in cached_fqdn_list, f"{removed_fqdn} should not be in cache"
                    for remaining_fqdn in fqdns_batch2:
                        assert remaining_fqdn in cached_fqdn_list, f"{remaining_fqdn} should be in cache"
                    print("✓ Cache contents verified: correct FQDNs removed")
            
            # Step 5: Remove remaining FQDNs
            print("\nStep 5: Removing remaining FQDNs...")
            remove_response2 = api_with_env_credentials.container_remove_fqdns(
                container_name=container_name,
                fqdns=fqdns_batch2
            )
            
            assert 'data' in remove_response2
            container_data = remove_response2['data']['container']['fqdn']['removeValues']['container']
            size_after_remove2 = container_data.get('size', 0)
            assert size_after_remove2 == 0, "Container should be empty after removing all FQDNs"
            print(f"✓ Removed {len(fqdns_batch2)} FQDNs, container size: {size_after_remove2}")
            
            # Verify cache is empty
            if api_with_env_credentials._cache:
                cache_stats = api_with_env_credentials.container_cache_stats(container_name)
                assert cache_stats['cached_fqdns'] == 0, "Cache should be empty after removing all FQDNs"
                assert cache_stats['api_size'] == size_after_remove2, "Cache size should match API size (0)"
                print(f"✓ Cache verified: {cache_stats['cached_fqdns']} FQDNs, container empty")
            
            # Step 6: Delete container
            print("\nStep 6: Deleting container...")
            delete_response = api_with_env_credentials.container_delete(name=container_name)
            created_container = False
            
            assert 'data' in delete_response
            print(f"✓ Container {container_name} deleted successfully")
            
            # Verify container list no longer includes it
            list_response = api_with_env_credentials.container_list()
            if 'data' in list_response:
                containers = list_response['data']['container']['list']['containers']
                container_names = [c['name'] for c in containers]
                assert container_name not in container_names, "Container should not exist after deletion"
                print("✓ Verified container no longer exists")
            
            print(f"\n✅ Full FQDN container lifecycle test passed for {container_name}")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            raise
        finally:
            # Cleanup if needed
            if created_container and api_with_env_credentials:
                try:
                    print(f"🧹 Cleanup: attempting to delete {container_name}")
                    api_with_env_credentials.container_delete(name=container_name)
                except Exception:
                    pass  # Ignore cleanup errors


class TestAPICache:
    """Test API caching functionality"""
    
    @pytest.fixture
    def api_with_cache(self, tmp_path):
        """Create API instance with cache enabled"""
        cache_path = tmp_path / "test_cache.db"
        api = API(key="test_key", account_id="test_account", cache_enabled=True, cache_path=str(cache_path))
        yield api
        if api._cache:
            api._cache.close()
    
    @pytest.fixture
    def api_no_cache(self):
        """Create API instance with cache disabled"""
        return API(key="test_key", account_id="test_account", cache_enabled=False)
    
    @patch.object(API, 'send')
    def test_ip_range_cache_hit(self, mock_send, api_with_cache):
        """Test that cached IP range skips API call"""
        # First call should hit API
        mock_send.return_value = {"data": {"container": {"ipAddressRange": {"addValues": {"container": {"size": 10}}}}}}
        
        result1 = api_with_cache.container_add_ip_range("Test", "192.168.1.1", "192.168.1.10")
        assert mock_send.call_count == 1
        assert "cached" not in result1
        
        # Second call should use cache
        result2 = api_with_cache.container_add_ip_range("Test", "192.168.1.1", "192.168.1.10")
        assert mock_send.call_count == 1  # No additional API call
        assert "cached" in result2
        assert result2["cached"] == True
    
    @patch.object(API, 'send')
    def test_fqdn_cache_hit(self, mock_send, api_with_cache):
        """Test that cached FQDNs skip API call"""
        # First call should hit API
        mock_send.return_value = {"data": {"container": {"fqdn": {"addValues": {"container": {"size": 5}}}}}}
        
        result1 = api_with_cache.container_add_fqdns("Test", ["example.com", "test.com"])
        assert mock_send.call_count == 1
        assert "cached" not in result1
        
        # Second call with same FQDNs should use cache
        result2 = api_with_cache.container_add_fqdns("Test", ["example.com", "test.com"])
        assert mock_send.call_count == 1  # No additional API call
        assert "cached" in result2
        assert result2["cached"] == True
    
    @patch.object(API, 'send')
    def test_fqdn_partial_cache_hit(self, mock_send, api_with_cache):
        """Test that partially cached FQDNs only send new ones to API"""
        # First call adds some FQDNs
        mock_send.return_value = {"data": {"container": {"fqdn": {"addValues": {"container": {"size": 2}}}}}}
        
        api_with_cache.container_add_fqdns("Test", ["example.com", "test.com"])
        assert mock_send.call_count == 1
        
        # Second call with mixed cached/new FQDNs
        result = api_with_cache.container_add_fqdns("Test", ["example.com", "new.com", "test.com", "another.com"])
        assert mock_send.call_count == 2  # One more API call
        
        # Check that only new FQDNs were sent to API
        call_args = mock_send.call_args[0]
        variables = call_args[1]
        assert set(variables["input"]["values"]) == {"new.com", "another.com"}
    
    def test_cache_disabled(self, api_no_cache):
        """Test that cache methods raise error when cache is disabled"""
        with pytest.raises(ValueError, match="Cache is not enabled"):
            api_no_cache.container_list_cached_values("Test")
        
        with pytest.raises(ValueError, match="Cache is not enabled"):
            api_no_cache.container_purge_stale("Test")
        
        with pytest.raises(ValueError, match="Cache is not enabled"):
            api_no_cache.container_cache_stats()
    
    def test_list_cached_values(self, api_with_cache):
        """Test listing cached values for a container"""
        # Add some test data directly to cache
        api_with_cache._cache.add_ip_range("Test", "192.168.1.1", "192.168.1.10")
        api_with_cache._cache.add_fqdn("Test", "example.com")
        
        result = api_with_cache.container_list_cached_values("Test")
        
        assert result["container"] == "Test"
        assert "ip_ranges" in result
        assert len(result["ip_ranges"]) == 1
        assert result["ip_ranges"][0]["from_ip"] == "192.168.1.1"
        assert "fqdns" in result
        assert len(result["fqdns"]) == 1
        assert result["fqdns"][0]["fqdn"] == "example.com"
    
    def test_purge_stale(self, api_with_cache):
        """Test purging stale cache entries"""
        # Add old and new entries
        now = int(time.time())
        old_timestamp = now - (35 * 86400)
        
        cursor = api_with_cache._cache.conn.cursor()
        cursor.execute("""
            INSERT INTO ip_ranges (container_name, from_ip, to_ip, added_timestamp, last_seen_timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, ("Test", "192.168.1.1", "192.168.1.10", old_timestamp, old_timestamp))
        api_with_cache._cache.conn.commit()
        
        api_with_cache._cache.add_ip_range("Test", "10.0.0.1", "10.0.0.10")
        
        result = api_with_cache.container_purge_stale("Test", max_age_days=30)
        
        assert result["container"] == "Test"
        assert result["deleted_ip_ranges"] == 1
        assert result["max_age_days"] == 30
    
    def test_cache_stats(self, api_with_cache):
        """Test getting cache statistics"""
        api_with_cache._cache.add_ip_range("Test", "192.168.1.1", "192.168.1.10")
        api_with_cache._cache.add_fqdn("Test", "example.com")
        
        # Container-specific stats
        stats = api_with_cache.container_cache_stats("Test")
        assert stats["cached_ip_ranges"] == 1
        assert stats["cached_fqdns"] == 1
        
        # Global stats
        global_stats = api_with_cache.container_cache_stats()
        assert global_stats["total_cached_ip_ranges"] == 1
        assert global_stats["total_cached_fqdns"] == 1
    
    def test_clear_cache(self, api_with_cache):
        """Test clearing container cache"""
        api_with_cache._cache.add_ip_range("Test", "192.168.1.1", "192.168.1.10")
        api_with_cache._cache.add_fqdn("Test", "example.com")
        
        result = api_with_cache.container_clear_cache("Test")
        
        assert result["container"] == "Test"
        assert result["deleted_ip_ranges"] == 1
        assert result["deleted_fqdns"] == 1
        assert result["total_deleted"] == 2
        
        # Verify cache is empty
        values = api_with_cache.container_list_cached_values("Test")
        assert "ip_ranges" not in values or len(values.get("ip_ranges", [])) == 0
        assert "fqdns" not in values or len(values.get("fqdns", [])) == 0
    
    def test_container_delete_clears_cache(self, api_with_cache, mocker):
        """Test that container_delete clears cache entries"""
        # Add some test data directly to cache
        api_with_cache._cache.add_ip_range("Test Container", "192.168.1.1", "192.168.1.10")
        api_with_cache._cache.add_fqdn("Test Container", "example.com")
        api_with_cache._cache.update_container_metadata("Test Container", "ip", 5)
        
        # Verify cache has entries
        stats = api_with_cache.container_cache_stats("Test Container")
        assert stats['cached_ip_ranges'] == 1
        assert stats['cached_fqdns'] == 1
        
        # Mock the API call to return successful deletion
        mock_response = {
            "data": {
                "container": {
                    "delete": {
                        "container": {
                            "id": "123",
                            "name": "Test Container",
                            "description": "Test",
                            "size": 0
                        }
                    }
                }
            }
        }
        mocker.patch.object(api_with_cache, 'send', return_value=mock_response)
        
        # Delete the container
        api_with_cache.container_delete("Test Container")
        
        # Verify the API was called correctly
        api_with_cache.send.assert_called_once()
        args, _ = api_with_cache.send.call_args
        assert args[0] == "deleteContainer"
        
        # Verify cache was cleared
        stats_after = api_with_cache.container_cache_stats("Test Container")
        assert stats_after['cached_ip_ranges'] == 0
        assert stats_after['cached_fqdns'] == 0
        assert stats_after['total_cached'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])