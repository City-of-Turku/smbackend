"""
Eco-Visio API Client

This module provides a client for interacting with the Eco-Visio API v2.
It handles authentication, pagination, rate limiting, and error handling.

API Documentation: https://developers.eco-counter.com/
"""

import logging
import time
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import requests
from django.conf import settings

logger = logging.getLogger("eco_counter")


class EcoVisioAPIError(Exception):
    """Base exception for Eco-Visio API errors."""

    pass


class EcoVisioAuthError(EcoVisioAPIError):
    """Raised when authentication fails."""

    pass


class EcoVisioRateLimitError(EcoVisioAPIError):
    """Raised when rate limit is exceeded."""

    pass


class EcoVisioAPIClient:
    """
    Client for the Eco-Visio API v2.

    This client provides methods to fetch sites and traffic data from the Eco-Visio API.
    It handles pagination, rate limiting, and proper error handling.

    Attributes:
        api_url: Base URL for the Eco-Visio API
        api_key: API key for authentication
        session: requests.Session for connection pooling
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        max_retries: int = 3,
    ):
        """
        Initialize the Eco-Visio API client.

        Args:
            api_key: API key for authentication. If None, uses settings.ECO_VISIO_API_KEY
            api_url: Base URL for the API. If None, uses settings.ECO_VISIO_API_URL
            max_retries: Maximum number of retries for failed requests
        """
        self.api_key = api_key or settings.ECO_VISIO_API_KEY
        self.api_url = (
            api_url or settings.ECO_VISIO_API_URL or "https://api.eco-counter.com/api/v2"
        )

        if not self.api_key:
            raise EcoVisioAuthError(
                "ECO_VISIO_API_KEY not configured in settings or provided"
            )

        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-API-KEY": self.api_key,
                "Accept": "application/json",
            }
        )

        # Rate limiting tracking
        self._rate_limit_remaining = None
        self._rate_limit_reset = None

        logger.info(f"Initialized Eco-Visio API client with base URL: {self.api_url}")

    def _update_rate_limit_info(self, headers: Dict[str, str]) -> None:
        """
        Update rate limit information from response headers.

        Args:
            headers: Response headers containing rate limit information
        """
        if "X-RateLimit-Remaining" in headers:
            self._rate_limit_remaining = int(headers["X-RateLimit-Remaining"])
        if "X-RateLimit-Reset" in headers:
            self._rate_limit_reset = int(headers["X-RateLimit-Reset"])

        if self._rate_limit_remaining is not None:
            logger.debug(
                f"Rate limit: {self._rate_limit_remaining} requests remaining, "
                f"resets in {self._rate_limit_reset}s"
            )

    def _wait_for_rate_limit(self) -> None:
        """Wait if we're approaching rate limit."""
        if (
            self._rate_limit_remaining is not None
            and self._rate_limit_remaining < 5
            and self._rate_limit_reset is not None
        ):
            wait_time = self._rate_limit_reset + 1
            logger.warning(
                f"Approaching rate limit. Waiting {wait_time} seconds before continuing..."
            )
            time.sleep(wait_time)
            self._rate_limit_remaining = None
            self._rate_limit_reset = None

    def _make_request(
        self, endpoint: str, params: Optional[Dict] = None, retry_count: int = 0
    ) -> requests.Response:
        """
        Make a request to the Eco-Visio API with error handling and retries.

        Args:
            endpoint: API endpoint (e.g., '/sites')
            params: Query parameters
            retry_count: Current retry attempt number

        Returns:
            requests.Response object

        Raises:
            EcoVisioAuthError: For 401/403 errors
            EcoVisioRateLimitError: For 429 errors
            EcoVisioAPIError: For other API errors
        """
        url = f"{self.api_url}{endpoint}"
        params = params or {}

        try:
            logger.debug(f"Making request to {endpoint} with params: {params}")
            response = self.session.get(url, params=params, timeout=30)

            # Update rate limit info from headers
            self._update_rate_limit_info(response.headers)

            # Handle different status codes
            if response.status_code == 200:
                return response

            elif response.status_code == 401:
                raise EcoVisioAuthError(
                    f"Authentication failed: Invalid or missing API key"
                )

            elif response.status_code == 403:
                raise EcoVisioAuthError(f"Access forbidden: {response.text}")

            elif response.status_code == 429:
                # Rate limit exceeded
                reset_time = int(response.headers.get("X-RateLimit-Reset", 60))
                logger.warning(f"Rate limit exceeded. Waiting {reset_time} seconds...")

                if retry_count < self.max_retries:
                    time.sleep(reset_time + 1)
                    return self._make_request(endpoint, params, retry_count + 1)
                else:
                    raise EcoVisioRateLimitError(
                        f"Rate limit exceeded after {self.max_retries} retries"
                    )

            elif response.status_code == 400:
                raise EcoVisioAPIError(f"Bad request: {response.text}")

            elif response.status_code == 404:
                raise EcoVisioAPIError(f"Resource not found: {endpoint}")

            else:
                raise EcoVisioAPIError(
                    f"API request failed with status {response.status_code}: {response.text}"
                )

        except requests.exceptions.Timeout:
            if retry_count < self.max_retries:
                logger.warning(
                    f"Request timeout. Retrying ({retry_count + 1}/{self.max_retries})..."
                )
                time.sleep(2**retry_count)  # Exponential backoff
                return self._make_request(endpoint, params, retry_count + 1)
            else:
                raise EcoVisioAPIError(
                    f"Request timeout after {self.max_retries} retries"
                )

        except requests.exceptions.RequestException as e:
            raise EcoVisioAPIError(f"Request failed: {str(e)}")

    def get_sites(
        self,
        page: int = 1,
        page_size: int = 100,
        include: Optional[List[str]] = None,
    ) -> Dict:
        """
        Fetch sites from the Eco-Visio API with pagination.

        Args:
            page: Page number (1-indexed)
            page_size: Number of results per page (max 500)
            include: Additional information to include (counters, tags, images, segments, etc.)

        Returns:
            Dict containing:
                - sites: List of site objects
                - total_count: Total number of sites
                - total_pages: Total number of pages
                - current_page: Current page number

        Example:
            >>> client = EcoVisioAPIClient()
            >>> result = client.get_sites(page=1, page_size=100, include=['segments', 'counters'])
            >>> sites = result['sites']
            >>> print(f"Retrieved {len(sites)} of {result['total_count']} sites")
        """
        params = {
            "page": page,
            "pageSize": min(page_size, 500),  # API max is 500
            "sortBy": "id",
            "orderBy": "asc",
        }

        if include:
            params["include"] = ",".join(include)

        # Check rate limit before making request
        self._wait_for_rate_limit()

        response = self._make_request("/sites", params)

        # Extract pagination info from headers
        total_count = int(response.headers.get("X-Total-Count", 0))
        total_pages = int(response.headers.get("X-Total-Pages", 1))
        current_page = int(response.headers.get("X-Current-Page", page))

        sites = response.json()

        logger.info(
            f"Retrieved {len(sites)} sites from page {current_page}/{total_pages} "
            f"(total: {total_count} sites)"
        )

        return {
            "sites": sites,
            "total_count": total_count,
            "total_pages": total_pages,
            "current_page": current_page,
        }

    def get_all_sites(self, include: Optional[List[str]] = None) -> List[Dict]:
        """
        Fetch all sites from the Eco-Visio API by iterating through all pages.

        Args:
            include: Additional information to include (counters, tags, images, segments, etc.)

        Returns:
            List of all site objects

        Example:
            >>> client = EcoVisioAPIClient()
            >>> sites = client.get_all_sites(include=['segments', 'counters'])
            >>> print(f"Retrieved {len(sites)} sites in total")
        """
        all_sites = []
        page = 1

        logger.info("Fetching all sites from Eco-Visio API...")

        while True:
            result = self.get_sites(page=page, page_size=500, include=include)
            sites = result["sites"]

            if not sites:
                break

            all_sites.extend(sites)

            # Check if we've retrieved all sites
            if result["current_page"] >= result["total_pages"]:
                break

            page += 1

        logger.info(f"Retrieved all {len(all_sites)} sites from Eco-Visio API")
        return all_sites

    def get_raw_traffic(
        self,
        site_id: int,
        start_date: date,
        end_date: date,
        include_status: bool = False,
        travel_modes: Optional[List[str]] = None,
        gap_filling: bool = False,
    ) -> List[Dict]:
        """
        Fetch raw traffic data for a specific site.

        Note: The API has a maximum timeframe of 31 days for raw traffic data.
        If the date range exceeds 31 days, this method will automatically split
        the request into multiple chunks.

        Args:
            site_id: The Eco-Visio site ID
            start_date: Start date (inclusive)
            end_date: End date (exclusive)
            include_status: Include data status information
            travel_modes: Filter by travel modes (bike, pedestrian, car, etc.)
            gap_filling: Fill gaps with null values for contiguous series

        Returns:
            List of traffic data series, each containing:
                - travelMode: Type of travel mode
                - direction: Direction (in, out, undefined)
                - flowID: Flow identifier
                - flowName: Flow name
                - data: List of data points with timestamp, granularity, and counts

        Raises:
            EcoVisioAPIError: If the request fails

        Example:
            >>> client = EcoVisioAPIClient()
            >>> from datetime import date
            >>> traffic = client.get_raw_traffic(
            ...     site_id=12345,
            ...     start_date=date(2024, 1, 1),
            ...     end_date=date(2024, 1, 31)
            ... )
            >>> for series in traffic:
            ...     print(f"{series['travelMode']} - {series['direction']}: {len(series['data'])} data points")
        """
        # Validate date range
        days_diff = (end_date - start_date).days
        if days_diff > 31:
            logger.info(
                f"Date range exceeds 31 days ({days_diff} days). "
                f"Splitting into chunks..."
            )
            return self._get_raw_traffic_chunked(
                site_id, start_date, end_date, include_status, travel_modes, gap_filling
            )

        params = {
            "siteId": site_id,
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "gapFilling": str(gap_filling).lower(),
        }

        if include_status:
            params["include"] = "status"

        if travel_modes:
            params["travelModes"] = travel_modes

        # Check rate limit before making request
        self._wait_for_rate_limit()

        response = self._make_request("/history/traffic/raw", params)
        traffic_data = response.json()

        logger.info(
            f"Retrieved raw traffic data for site {site_id} "
            f"from {start_date} to {end_date}: {len(traffic_data)} series"
        )

        return traffic_data

    def _get_raw_traffic_chunked(
        self,
        site_id: int,
        start_date: date,
        end_date: date,
        include_status: bool,
        travel_modes: Optional[List[str]],
        gap_filling: bool,
    ) -> List[Dict]:
        """
        Fetch raw traffic data in chunks when date range exceeds 31 days.

        Args:
            site_id: The Eco-Visio site ID
            start_date: Start date (inclusive)
            end_date: End date (exclusive)
            include_status: Include data status information
            travel_modes: Filter by travel modes
            gap_filling: Fill gaps with null values

        Returns:
            Combined list of traffic data series from all chunks
        """
        merged_series: Dict[tuple, Dict] = {}
        current_date = start_date

        def _series_key(series: Dict) -> tuple:
            """Build a stable key for a traffic series across chunks."""
            return (
                series.get("flowID"),
                series.get("flowName"),
                series.get("travelMode"),
                series.get("direction"),
            )

        while current_date < end_date:
            # Calculate chunk end date (max 31 days)
            chunk_end = min(current_date + timedelta(days=31), end_date)

            logger.debug(
                f"Fetching chunk: {current_date.isoformat()} to {chunk_end.isoformat()}"
            )

            chunk_data = self.get_raw_traffic(
                site_id=site_id,
                start_date=current_date,
                end_date=chunk_end,
                include_status=include_status,
                travel_modes=travel_modes,
                gap_filling=gap_filling,
            )

            if not chunk_data:
                current_date = chunk_end
                continue

            for series in chunk_data:
                key = _series_key(series)
                if key not in merged_series:
                    merged_series[key] = {
                        **{k: v for k, v in series.items() if k != "data"},
                        "data": list(series.get("data") or []),
                    }
                else:
                    merged_series[key]["data"].extend(series.get("data") or [])

            current_date = chunk_end

        logger.info(
            f"Retrieved complete raw traffic data for site {site_id} "
            f"from {start_date} to {end_date} in chunks"
        )

        return list(merged_series.values())

    def close(self):
        """Close the session."""
        self.session.close()
        logger.debug("Closed Eco-Visio API client session")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

