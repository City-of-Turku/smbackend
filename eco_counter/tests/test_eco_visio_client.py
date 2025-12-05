"""
Unit tests for EcoVisioAPIClient.

These tests provide comprehensive coverage of the Eco-Visio API client,
including authentication, rate limiting, error handling, and data retrieval.
"""

import time
from datetime import date, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from eco_counter.management.commands.eco_visio_client import (
    EcoVisioAPIClient,
    EcoVisioAPIError,
    EcoVisioAuthError,
    EcoVisioRateLimitError,
)


class TestEcoVisioAPIClientInitialization:
    """Tests for EcoVisioAPIClient initialization."""

    def test_init_with_api_key(self):
        """Test initialization with API key provided."""
        client = EcoVisioAPIClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.api_url == "https://api.eco-counter.com/api/v2"
        assert client.max_retries == 3
        assert "X-API-KEY" in client.session.headers
        assert client.session.headers["X-API-KEY"] == "test-key"
        assert client.session.headers["Accept"] == "application/json"

    def test_init_with_custom_url(self):
        """Test initialization with custom API URL."""
        client = EcoVisioAPIClient(
            api_key="test-key", api_url="https://custom.api.com/v2"
        )
        assert client.api_url == "https://custom.api.com/v2"

    @patch("eco_counter.management.commands.eco_visio_client.settings")
    def test_init_with_settings(self, mock_settings):
        """Test initialization using Django settings."""
        mock_settings.ECO_VISIO_API_KEY = "settings-key"
        mock_settings.ECO_VISIO_API_URL = "https://settings.api.com/v2"

        client = EcoVisioAPIClient()
        assert client.api_key == "settings-key"
        assert client.api_url == "https://settings.api.com/v2"

    @patch("eco_counter.management.commands.eco_visio_client.settings")
    def test_init_without_api_key_raises_error(self, mock_settings):
        """Test that initialization without API key raises EcoVisioAuthError."""
        mock_settings.ECO_VISIO_API_KEY = None

        with pytest.raises(EcoVisioAuthError) as exc_info:
            EcoVisioAPIClient()
        assert "ECO_VISIO_API_KEY not configured" in str(exc_info.value)

    def test_init_with_custom_max_retries(self):
        """Test initialization with custom max_retries."""
        client = EcoVisioAPIClient(api_key="test-key", max_retries=5)
        assert client.max_retries == 5

    def test_rate_limit_tracking_initialized(self):
        """Test that rate limit tracking attributes are initialized."""
        client = EcoVisioAPIClient(api_key="test-key")
        assert client._rate_limit_remaining is None
        assert client._rate_limit_reset is None


class TestRateLimitHandling:
    """Tests for rate limit handling."""

    def test_update_rate_limit_info(self):
        """Test updating rate limit info from response headers."""
        client = EcoVisioAPIClient(api_key="test-key")
        headers = {"X-RateLimit-Remaining": "100", "X-RateLimit-Reset": "60"}

        client._update_rate_limit_info(headers)

        assert client._rate_limit_remaining == 100
        assert client._rate_limit_reset == 60

    def test_update_rate_limit_info_partial_headers(self):
        """Test updating rate limit with only some headers present."""
        client = EcoVisioAPIClient(api_key="test-key")
        headers = {"X-RateLimit-Remaining": "50"}

        client._update_rate_limit_info(headers)

        assert client._rate_limit_remaining == 50
        assert client._rate_limit_reset is None

    def test_update_rate_limit_info_no_headers(self):
        """Test updating rate limit with no relevant headers."""
        client = EcoVisioAPIClient(api_key="test-key")
        headers = {}

        client._update_rate_limit_info(headers)

        assert client._rate_limit_remaining is None
        assert client._rate_limit_reset is None

    @patch("eco_counter.management.commands.eco_visio_client.time.sleep")
    def test_wait_for_rate_limit_when_approaching(self, mock_sleep):
        """Test that client waits when approaching rate limit."""
        client = EcoVisioAPIClient(api_key="test-key")
        client._rate_limit_remaining = 3
        client._rate_limit_reset = 10

        client._wait_for_rate_limit()

        mock_sleep.assert_called_once_with(11)
        assert client._rate_limit_remaining is None
        assert client._rate_limit_reset is None

    @patch("eco_counter.management.commands.eco_visio_client.time.sleep")
    def test_wait_for_rate_limit_when_not_approaching(self, mock_sleep):
        """Test that client doesn't wait when rate limit is not approaching."""
        client = EcoVisioAPIClient(api_key="test-key")
        client._rate_limit_remaining = 100
        client._rate_limit_reset = 60

        client._wait_for_rate_limit()

        mock_sleep.assert_not_called()

    @patch("eco_counter.management.commands.eco_visio_client.time.sleep")
    def test_wait_for_rate_limit_no_info(self, mock_sleep):
        """Test that client doesn't wait when no rate limit info is available."""
        client = EcoVisioAPIClient(api_key="test-key")

        client._wait_for_rate_limit()

        mock_sleep.assert_not_called()


class TestMakeRequest:
    """Tests for the _make_request method."""

    def test_successful_request(self):
        """Test successful API request."""
        client = EcoVisioAPIClient(api_key="test-key")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}

        with patch.object(client.session, "get", return_value=mock_response):
            response = client._make_request("/test")

        assert response == mock_response

    def test_request_with_params(self):
        """Test request with query parameters."""
        client = EcoVisioAPIClient(api_key="test-key")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}

        with patch.object(client.session, "get", return_value=mock_response) as mock_get:
            client._make_request("/test", params={"key": "value"})

        mock_get.assert_called_once_with(
            "https://api.eco-counter.com/api/v2/test",
            params={"key": "value"},
            timeout=30,
        )

    def test_request_updates_rate_limit_info(self):
        """Test that successful request updates rate limit info."""
        client = EcoVisioAPIClient(api_key="test-key")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"X-RateLimit-Remaining": "99", "X-RateLimit-Reset": "60"}

        with patch.object(client.session, "get", return_value=mock_response):
            client._make_request("/test")

        assert client._rate_limit_remaining == 99
        assert client._rate_limit_reset == 60

    def test_request_401_raises_auth_error(self):
        """Test that 401 response raises EcoVisioAuthError."""
        client = EcoVisioAPIClient(api_key="test-key")
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.headers = {}

        with patch.object(client.session, "get", return_value=mock_response):
            with pytest.raises(EcoVisioAuthError) as exc_info:
                client._make_request("/test")

        assert "Authentication failed" in str(exc_info.value)

    def test_request_403_raises_auth_error(self):
        """Test that 403 response raises EcoVisioAuthError."""
        client = EcoVisioAPIClient(api_key="test-key")
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.headers = {}

        with patch.object(client.session, "get", return_value=mock_response):
            with pytest.raises(EcoVisioAuthError) as exc_info:
                client._make_request("/test")

        assert "Access forbidden" in str(exc_info.value)

    def test_request_400_raises_api_error(self):
        """Test that 400 response raises EcoVisioAPIError."""
        client = EcoVisioAPIClient(api_key="test-key")
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_response.headers = {}

        with patch.object(client.session, "get", return_value=mock_response):
            with pytest.raises(EcoVisioAPIError) as exc_info:
                client._make_request("/test")

        assert "Bad request" in str(exc_info.value)

    def test_request_404_raises_api_error(self):
        """Test that 404 response raises EcoVisioAPIError."""
        client = EcoVisioAPIClient(api_key="test-key")
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.headers = {}

        with patch.object(client.session, "get", return_value=mock_response):
            with pytest.raises(EcoVisioAPIError) as exc_info:
                client._make_request("/test")

        assert "Resource not found" in str(exc_info.value)

    def test_request_500_raises_api_error(self):
        """Test that 500 response raises EcoVisioAPIError."""
        client = EcoVisioAPIClient(api_key="test-key")
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_response.headers = {}

        with patch.object(client.session, "get", return_value=mock_response):
            with pytest.raises(EcoVisioAPIError) as exc_info:
                client._make_request("/test")

        assert "API request failed with status 500" in str(exc_info.value)

    @patch("eco_counter.management.commands.eco_visio_client.time.sleep")
    def test_request_429_retries_and_succeeds(self, mock_sleep):
        """Test that 429 response retries and can succeed."""
        client = EcoVisioAPIClient(api_key="test-key")

        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"X-RateLimit-Reset": "2"}

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.headers = {}

        with patch.object(
            client.session, "get", side_effect=[mock_response_429, mock_response_200]
        ) as mock_get:
            response = client._make_request("/test")

        assert response == mock_response_200
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once_with(3)

    @patch("eco_counter.management.commands.eco_visio_client.time.sleep")
    def test_request_429_exceeds_retries(self, mock_sleep):
        """Test that 429 response raises error after max retries."""
        client = EcoVisioAPIClient(api_key="test-key", max_retries=2)

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"X-RateLimit-Reset": "1"}

        with patch.object(client.session, "get", return_value=mock_response):
            with pytest.raises(EcoVisioRateLimitError) as exc_info:
                client._make_request("/test")

        assert "Rate limit exceeded after 2 retries" in str(exc_info.value)

    @patch("eco_counter.management.commands.eco_visio_client.time.sleep")
    def test_request_timeout_retries(self, mock_sleep):
        """Test that timeout retries with exponential backoff."""
        client = EcoVisioAPIClient(api_key="test-key", max_retries=3)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}

        with patch.object(
            client.session,
            "get",
            side_effect=[
                requests.exceptions.Timeout(),
                requests.exceptions.Timeout(),
                mock_response,
            ],
        ) as mock_get:
            response = client._make_request("/test")

        assert response == mock_response
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2
        # Check exponential backoff: 2^0=1, 2^1=2
        assert mock_sleep.call_args_list[0][0][0] == 1
        assert mock_sleep.call_args_list[1][0][0] == 2

    @patch("eco_counter.management.commands.eco_visio_client.time.sleep")
    def test_request_timeout_exceeds_retries(self, mock_sleep):
        """Test that timeout raises error after max retries."""
        client = EcoVisioAPIClient(api_key="test-key", max_retries=1)

        with patch.object(
            client.session, "get", side_effect=requests.exceptions.Timeout()
        ):
            with pytest.raises(EcoVisioAPIError) as exc_info:
                client._make_request("/test")

        assert "Request timeout after 1 retries" in str(exc_info.value)

    def test_request_connection_error(self):
        """Test that connection error raises EcoVisioAPIError."""
        client = EcoVisioAPIClient(api_key="test-key")

        with patch.object(
            client.session,
            "get",
            side_effect=requests.exceptions.ConnectionError("Connection failed"),
        ):
            with pytest.raises(EcoVisioAPIError) as exc_info:
                client._make_request("/test")

        assert "Request failed" in str(exc_info.value)


class TestGetSites:
    """Tests for the get_sites method."""

    def test_get_sites_default_params(self):
        """Test get_sites with default parameters."""
        client = EcoVisioAPIClient(api_key="test-key")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "X-Total-Count": "150",
            "X-Total-Pages": "2",
            "X-Current-Page": "1",
        }
        mock_response.json.return_value = [{"id": 1, "name": "Site 1"}]

        with patch.object(client.session, "get", return_value=mock_response) as mock_get:
            result = client.get_sites()

        assert result["sites"] == [{"id": 1, "name": "Site 1"}]
        assert result["total_count"] == 150
        assert result["total_pages"] == 2
        assert result["current_page"] == 1

        # Verify request parameters
        call_args = mock_get.call_args
        assert call_args[1]["params"]["page"] == 1
        assert call_args[1]["params"]["pageSize"] == 100
        assert call_args[1]["params"]["sortBy"] == "id"
        assert call_args[1]["params"]["orderBy"] == "asc"

    def test_get_sites_with_custom_params(self):
        """Test get_sites with custom parameters."""
        client = EcoVisioAPIClient(api_key="test-key")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "X-Total-Count": "300",
            "X-Total-Pages": "2",
            "X-Current-Page": "2",
        }
        mock_response.json.return_value = [{"id": 2, "name": "Site 2"}]

        with patch.object(client.session, "get", return_value=mock_response) as mock_get:
            result = client.get_sites(page=2, page_size=200, include=["segments", "counters"])

        assert result["current_page"] == 2

        # Verify request parameters
        call_args = mock_get.call_args
        assert call_args[1]["params"]["page"] == 2
        assert call_args[1]["params"]["pageSize"] == 200
        assert call_args[1]["params"]["include"] == "segments,counters"

    def test_get_sites_max_page_size_limit(self):
        """Test that page_size is capped at 500."""
        client = EcoVisioAPIClient(api_key="test-key")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "X-Total-Count": "1000",
            "X-Total-Pages": "2",
            "X-Current-Page": "1",
        }
        mock_response.json.return_value = []

        with patch.object(client.session, "get", return_value=mock_response) as mock_get:
            client.get_sites(page_size=1000)

        # Verify page size was capped at 500
        call_args = mock_get.call_args
        assert call_args[1]["params"]["pageSize"] == 500

    @patch("eco_counter.management.commands.eco_visio_client.time.sleep")
    def test_get_sites_waits_for_rate_limit(self, mock_sleep):
        """Test that get_sites waits for rate limit before making request."""
        client = EcoVisioAPIClient(api_key="test-key")
        client._rate_limit_remaining = 2
        client._rate_limit_reset = 5

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "X-Total-Count": "10",
            "X-Total-Pages": "1",
            "X-Current-Page": "1",
        }
        mock_response.json.return_value = []

        with patch.object(client.session, "get", return_value=mock_response):
            client.get_sites()

        mock_sleep.assert_called_once_with(6)

    def test_get_sites_handles_missing_headers(self):
        """Test that get_sites handles missing pagination headers."""
        client = EcoVisioAPIClient(api_key="test-key")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = [{"id": 1}]

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.get_sites()

        assert result["total_count"] == 0
        assert result["total_pages"] == 1
        assert result["current_page"] == 1


class TestGetAllSites:
    """Tests for the get_all_sites method."""

    def test_get_all_sites_single_page(self):
        """Test get_all_sites with single page of results."""
        client = EcoVisioAPIClient(api_key="test-key")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "X-Total-Count": "50",
            "X-Total-Pages": "1",
            "X-Current-Page": "1",
        }
        sites_data = [{"id": i, "name": f"Site {i}"} for i in range(50)]
        mock_response.json.return_value = sites_data

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.get_all_sites()

        assert len(result) == 50
        assert result[0]["id"] == 0
        assert result[49]["id"] == 49

    def test_get_all_sites_multiple_pages(self):
        """Test get_all_sites with multiple pages."""
        client = EcoVisioAPIClient(api_key="test-key")

        # Create mock responses for 3 pages
        page1_sites = [{"id": i, "name": f"Site {i}"} for i in range(100)]
        page2_sites = [{"id": i, "name": f"Site {i}"} for i in range(100, 200)]
        page3_sites = [{"id": i, "name": f"Site {i}"} for i in range(200, 250)]

        mock_responses = []
        for page_num, sites in enumerate([page1_sites, page2_sites, page3_sites], 1):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {
                "X-Total-Count": "250",
                "X-Total-Pages": "3",
                "X-Current-Page": str(page_num),
            }
            mock_response.json.return_value = sites
            mock_responses.append(mock_response)

        with patch.object(client.session, "get", side_effect=mock_responses) as mock_get:
            result = client.get_all_sites()

        assert len(result) == 250
        assert mock_get.call_count == 3
        assert result[0]["id"] == 0
        assert result[249]["id"] == 249

    def test_get_all_sites_with_include(self):
        """Test get_all_sites passes include parameter."""
        client = EcoVisioAPIClient(api_key="test-key")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "X-Total-Count": "10",
            "X-Total-Pages": "1",
            "X-Current-Page": "1",
        }
        mock_response.json.return_value = [{"id": 1, "segments": []}]

        with patch.object(client.session, "get", return_value=mock_response) as mock_get:
            client.get_all_sites(include=["segments", "counters"])

        call_args = mock_get.call_args
        assert call_args[1]["params"]["include"] == "segments,counters"

    def test_get_all_sites_empty_response_breaks_loop(self):
        """Test that get_all_sites stops when receiving empty response."""
        client = EcoVisioAPIClient(api_key="test-key")

        mock_response_empty = Mock()
        mock_response_empty.status_code = 200
        mock_response_empty.headers = {
            "X-Total-Count": "0",
            "X-Total-Pages": "1",
            "X-Current-Page": "1",
        }
        mock_response_empty.json.return_value = []

        with patch.object(client.session, "get", return_value=mock_response_empty) as mock_get:
            result = client.get_all_sites()

        assert len(result) == 0
        assert mock_get.call_count == 1


class TestGetRawTraffic:
    """Tests for the get_raw_traffic method."""

    def test_get_raw_traffic_basic(self):
        """Test get_raw_traffic with basic parameters."""
        client = EcoVisioAPIClient(api_key="test-key")

        traffic_data = [
            {
                "travelMode": "bike",
                "direction": "in",
                "flowID": 1,
                "flowName": "Flow 1",
                "data": [{"timestamp": "2024-01-01T00:00:00Z", "count": 10}],
            }
        ]

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = traffic_data

        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 10)

        with patch.object(client.session, "get", return_value=mock_response) as mock_get:
            result = client.get_raw_traffic(site_id=12345, start_date=start_date, end_date=end_date)

        assert result == traffic_data

        # Verify request parameters
        call_args = mock_get.call_args
        assert call_args[1]["params"]["siteId"] == 12345
        assert call_args[1]["params"]["startDate"] == "2024-01-01"
        assert call_args[1]["params"]["endDate"] == "2024-01-10"
        assert call_args[1]["params"]["gapFilling"] == "false"

    def test_get_raw_traffic_with_optional_params(self):
        """Test get_raw_traffic with optional parameters."""
        client = EcoVisioAPIClient(api_key="test-key")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = []

        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 10)

        with patch.object(client.session, "get", return_value=mock_response) as mock_get:
            client.get_raw_traffic(
                site_id=12345,
                start_date=start_date,
                end_date=end_date,
                include_status=True,
                travel_modes=["bike", "pedestrian"],
                gap_filling=True,
            )

        # Verify request parameters
        call_args = mock_get.call_args
        params = call_args[1]["params"]
        assert params["include"] == "status"
        assert params["travelModes"] == ["bike", "pedestrian"]
        assert params["gapFilling"] == "true"

    def test_get_raw_traffic_date_range_over_31_days(self):
        """Test that date range over 31 days triggers chunked retrieval."""
        client = EcoVisioAPIClient(api_key="test-key")

        start_date = date(2024, 1, 1)
        end_date = date(2024, 3, 1)  # 60 days

        with patch.object(
            client, "_get_raw_traffic_chunked", return_value=[]
        ) as mock_chunked:
            client.get_raw_traffic(site_id=12345, start_date=start_date, end_date=end_date)

        mock_chunked.assert_called_once_with(12345, start_date, end_date, False, None, False)

    def test_get_raw_traffic_exactly_31_days(self):
        """Test that exactly 31 days does not trigger chunking."""
        client = EcoVisioAPIClient(api_key="test-key")

        start_date = date(2024, 1, 1)
        end_date = date(2024, 2, 1)  # Exactly 31 days

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = []

        with patch.object(client.session, "get", return_value=mock_response):
            with patch.object(client, "_get_raw_traffic_chunked") as mock_chunked:
                client.get_raw_traffic(site_id=12345, start_date=start_date, end_date=end_date)

        mock_chunked.assert_not_called()

    @patch("eco_counter.management.commands.eco_visio_client.time.sleep")
    def test_get_raw_traffic_waits_for_rate_limit(self, mock_sleep):
        """Test that get_raw_traffic waits for rate limit."""
        client = EcoVisioAPIClient(api_key="test-key")
        client._rate_limit_remaining = 3
        client._rate_limit_reset = 2

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = []

        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 10)

        with patch.object(client.session, "get", return_value=mock_response):
            client.get_raw_traffic(site_id=12345, start_date=start_date, end_date=end_date)

        mock_sleep.assert_called_once_with(3)


class TestGetRawTrafficChunked:
    """Tests for the _get_raw_traffic_chunked method."""

    def test_get_raw_traffic_chunked_two_chunks(self):
        """Test chunked retrieval with two chunks."""
        client = EcoVisioAPIClient(api_key="test-key")

        start_date = date(2024, 1, 1)
        end_date = date(2024, 3, 5)  # 64 days - requires 3 chunks

        # Mock data for each chunk
        chunk1_data = [
            {
                "travelMode": "bike",
                "direction": "in",
                "data": [{"timestamp": "2024-01-01T00:00:00Z", "count": 10}],
            }
        ]
        chunk2_data = [
            {
                "travelMode": "bike",
                "direction": "in",
                "data": [{"timestamp": "2024-02-01T00:00:00Z", "count": 20}],
            }
        ]
        chunk3_data = [
            {
                "travelMode": "bike",
                "direction": "in",
                "data": [{"timestamp": "2024-03-03T00:00:00Z", "count": 30}],
            }
        ]

        mock_responses = []
        for chunk_data in [chunk1_data, chunk2_data, chunk3_data]:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.json.return_value = chunk_data
            mock_responses.append(mock_response)

        with patch.object(client.session, "get", side_effect=mock_responses) as mock_get:
            result = client._get_raw_traffic_chunked(
                site_id=12345,
                start_date=start_date,
                end_date=end_date,
                include_status=False,
                travel_modes=None,
                gap_filling=False,
            )

        # Should make 3 requests (3 chunks)
        assert mock_get.call_count == 3

        # Verify data was merged
        assert len(result) == 1
        assert len(result[0]["data"]) == 3
        assert result[0]["data"][0]["count"] == 10
        assert result[0]["data"][1]["count"] == 20
        assert result[0]["data"][2]["count"] == 30

    def test_get_raw_traffic_chunked_respects_chunk_boundaries(self):
        """Test that chunks respect 31-day boundaries."""
        client = EcoVisioAPIClient(api_key="test-key")

        start_date = date(2024, 1, 1)
        end_date = date(2024, 3, 1)  # 60 days

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = [{"travelMode": "bike", "data": []}]

        with patch.object(client.session, "get", return_value=mock_response) as mock_get:
            client._get_raw_traffic_chunked(
                site_id=12345,
                start_date=start_date,
                end_date=end_date,
                include_status=False,
                travel_modes=None,
                gap_filling=False,
            )

        # Verify the date parameters in each call
        call_args_list = mock_get.call_args_list
        
        # First chunk: 2024-01-01 to 2024-02-01 (31 days)
        assert call_args_list[0][1]["params"]["startDate"] == "2024-01-01"
        assert call_args_list[0][1]["params"]["endDate"] == "2024-02-01"
        
        # Second chunk: 2024-02-01 to 2024-03-01 (29 days)
        assert call_args_list[1][1]["params"]["startDate"] == "2024-02-01"
        assert call_args_list[1][1]["params"]["endDate"] == "2024-03-01"

    def test_get_raw_traffic_chunked_merges_additional_series(self):
        """Additional series appearing in later chunks are merged instead of dropped."""
        client = EcoVisioAPIClient(api_key="test-key")

        start_date = date(2024, 1, 1)
        end_date = date(2024, 2, 15)  # 45 days -> two chunks

        chunk1_data = [
            {
                "flowID": 1,
                "flowName": "Bikes in",
                "travelMode": "bike",
                "direction": "in",
                "data": [{"timestamp": "2024-01-01T00:00:00Z", "count": 10}],
            }
        ]
        chunk2_data = [
            {
                "flowID": 1,
                "flowName": "Bikes in",
                "travelMode": "bike",
                "direction": "in",
                "data": [{"timestamp": "2024-02-05T00:00:00Z", "count": 20}],
            },
            {
                "flowID": 2,
                "flowName": "Pedestrians out",
                "travelMode": "pedestrian",
                "direction": "out",
                "data": [{"timestamp": "2024-02-05T00:00:00Z", "count": 5}],
            },
        ]

        mock_responses = []
        for chunk_data in [chunk1_data, chunk2_data]:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.json.return_value = chunk_data
            mock_responses.append(mock_response)

        with patch.object(client.session, "get", side_effect=mock_responses):
            result = client._get_raw_traffic_chunked(
                site_id=12345,
                start_date=start_date,
                end_date=end_date,
                include_status=False,
                travel_modes=None,
                gap_filling=False,
            )

        assert len(result) == 2
        result_by_id = {series["flowID"]: series for series in result}
        assert len(result_by_id[1]["data"]) == 2
        assert len(result_by_id[2]["data"]) == 1
        assert result_by_id[2]["data"][0]["count"] == 5

    def test_get_raw_traffic_chunked_handles_empty_initial_chunk(self):
        """Data in later chunks is preserved even if earlier chunks are empty."""
        client = EcoVisioAPIClient(api_key="test-key")

        start_date = date(2024, 1, 1)
        end_date = date(2024, 2, 10)  # Two chunks

        chunk1_data = []
        chunk2_data = [
            {
                "flowID": 3,
                "flowName": "Cars in",
                "travelMode": "car",
                "direction": "in",
                "data": [{"timestamp": "2024-02-05T00:00:00Z", "count": 15}],
            }
        ]

        mock_responses = []
        for chunk_data in [chunk1_data, chunk2_data]:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.json.return_value = chunk_data
            mock_responses.append(mock_response)

        with patch.object(client.session, "get", side_effect=mock_responses):
            result = client._get_raw_traffic_chunked(
                site_id=12345,
                start_date=start_date,
                end_date=end_date,
                include_status=False,
                travel_modes=None,
                gap_filling=False,
            )

        assert len(result) == 1
        assert result[0]["flowID"] == 3
        assert len(result[0]["data"]) == 1
        assert result[0]["data"][0]["count"] == 15


class TestContextManager:
    """Tests for context manager functionality."""

    def test_context_manager_enter_exit(self):
        """Test using client as context manager."""
        with patch("eco_counter.management.commands.eco_visio_client.requests.Session"):
            with EcoVisioAPIClient(api_key="test-key") as client:
                assert isinstance(client, EcoVisioAPIClient)

    def test_context_manager_closes_session(self):
        """Test that context manager closes session on exit."""
        client = EcoVisioAPIClient(api_key="test-key")
        mock_session = Mock()
        client.session = mock_session

        with client:
            pass

        mock_session.close.assert_called_once()

    def test_close_method(self):
        """Test close method explicitly."""
        client = EcoVisioAPIClient(api_key="test-key")
        mock_session = Mock()
        client.session = mock_session

        client.close()

        mock_session.close.assert_called_once()

    def test_enter_returns_self(self):
        """Test that __enter__ returns self."""
        client = EcoVisioAPIClient(api_key="test-key")
        result = client.__enter__()
        assert result is client

    def test_exit_closes_session(self):
        """Test that __exit__ closes session."""
        client = EcoVisioAPIClient(api_key="test-key")
        mock_session = Mock()
        client.session = mock_session

        client.__exit__(None, None, None)

        mock_session.close.assert_called_once()


class TestExceptionClasses:
    """Tests for custom exception classes."""

    def test_eco_visio_api_error_is_exception(self):
        """Test that EcoVisioAPIError is an Exception."""
        error = EcoVisioAPIError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_eco_visio_auth_error_is_api_error(self):
        """Test that EcoVisioAuthError inherits from EcoVisioAPIError."""
        error = EcoVisioAuthError("Auth error")
        assert isinstance(error, EcoVisioAPIError)
        assert isinstance(error, Exception)
        assert str(error) == "Auth error"

    def test_eco_visio_rate_limit_error_is_api_error(self):
        """Test that EcoVisioRateLimitError inherits from EcoVisioAPIError."""
        error = EcoVisioRateLimitError("Rate limit error")
        assert isinstance(error, EcoVisioAPIError)
        assert isinstance(error, Exception)
        assert str(error) == "Rate limit error"


class TestIntegrationScenarios:
    """Integration tests for complex scenarios."""

    def test_full_workflow_with_pagination(self):
        """Test a complete workflow: get sites with pagination."""
        client = EcoVisioAPIClient(api_key="test-key")

        # Mock two pages of sites
        page1_response = Mock()
        page1_response.status_code = 200
        page1_response.headers = {
            "X-Total-Count": "3",
            "X-Total-Pages": "2",
            "X-Current-Page": "1",
            "X-RateLimit-Remaining": "100",
        }
        page1_response.json.return_value = [{"id": 1}, {"id": 2}]

        page2_response = Mock()
        page2_response.status_code = 200
        page2_response.headers = {
            "X-Total-Count": "3",
            "X-Total-Pages": "2",
            "X-Current-Page": "2",
            "X-RateLimit-Remaining": "99",
        }
        page2_response.json.return_value = [{"id": 3}]

        with patch.object(
            client.session, "get", side_effect=[page1_response, page2_response]
        ):
            all_sites = client.get_all_sites()

        assert len(all_sites) == 3
        assert all_sites[0]["id"] == 1
        assert all_sites[2]["id"] == 3

    @patch("eco_counter.management.commands.eco_visio_client.time.sleep")
    def test_workflow_with_rate_limiting_and_recovery(self, mock_sleep):
        """Test workflow that hits rate limit and recovers."""
        client = EcoVisioAPIClient(api_key="test-key")

        # First request hits rate limit
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"X-RateLimit-Reset": "1"}

        # Second request succeeds
        success_response = Mock()
        success_response.status_code = 200
        success_response.headers = {}
        success_response.json.return_value = []

        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 10)

        with patch.object(
            client.session, "get", side_effect=[rate_limit_response, success_response]
        ):
            result = client.get_raw_traffic(
                site_id=12345, start_date=start_date, end_date=end_date
            )

        assert result == []
        mock_sleep.assert_called_once_with(2)  # Reset time + 1

