"""
API client for communicating with wanLLMDB backend.
"""

from typing import Any, Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from wanllmdb.errors import APIError, AuthenticationError


class APIClient:
    """Client for wanLLMDB API."""

    def __init__(
        self,
        api_url: str,
        metric_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize API client.

        Args:
            api_url: Base URL for main API
            metric_url: Base URL for metric service
            username: Username for authentication
            password: Password for authentication
            api_key: API key for authentication
        """
        self.api_url = api_url.rstrip("/")
        self.metric_url = metric_url.rstrip("/")
        self.username = username
        self.password = password
        self.api_key = api_key

        # Session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

    def login(self) -> None:
        """Authenticate with the API."""
        if self.api_key:
            self.access_token = self.api_key
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})
            return

        if not self.username or not self.password:
            raise AuthenticationError(
                "Authentication required. Provide username/password or API key."
            )

        try:
            response = self.session.post(
                f"{self.api_url}/auth/login",
                data={
                    "username": self.username,
                    "password": self.password,
                },
            )
            response.raise_for_status()
            data = response.json()

            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")

            self.session.headers.update({
                "Authorization": f"Bearer {self.access_token}"
            })
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid username or password")
            raise APIError(f"Authentication failed: {e}")
        except Exception as e:
            raise APIError(f"Authentication failed: {e}")

    def _request(
        self,
        method: str,
        endpoint: str,
        base_url: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Make an API request.

        Args:
            method: HTTP method
            endpoint: API endpoint
            base_url: Base URL (default: api_url)
            **kwargs: Additional arguments for requests

        Returns:
            Response data

        Raises:
            APIError: If request fails
        """
        url = f"{base_url or self.api_url}/{endpoint.lstrip('/')}"

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()

            if response.status_code == 204:
                return {}

            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"{method} {endpoint} failed: {e}"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("detail", error_msg)
            except:
                pass
            raise APIError(error_msg)
        except Exception as e:
            raise APIError(f"{method} {endpoint} failed: {e}")

    # Project APIs
    def get_project_by_name(self, name: str) -> Dict[str, Any]:
        """Get project by name."""
        projects = self._request("GET", "/projects", params={"search": name})
        for project in projects.get("items", []):
            if project["name"] == name:
                return project
        raise APIError(f"Project '{name}' not found")

    def create_project(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new project."""
        return self._request("POST", "/projects", json=data)

    # Run APIs
    def create_run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new run."""
        return self._request("POST", "/runs", json=data)

    def update_run(self, run_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a run."""
        return self._request("PUT", f"/runs/{run_id}", json=data)

    def finish_run(
        self,
        run_id: str,
        exit_code: int = 0,
        summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Finish a run."""
        return self._request(
            "POST",
            f"/runs/{run_id}/finish",
            json={"exit_code": exit_code, "summary": summary or {}},
        )

    def heartbeat_run(self, run_id: str) -> Dict[str, Any]:
        """Send heartbeat for a run."""
        return self._request("POST", f"/runs/{run_id}/heartbeat")

    def add_run_tags(self, run_id: str, tags: List[str]) -> Dict[str, Any]:
        """Add tags to a run."""
        return self._request("POST", f"/runs/{run_id}/tags", json={"tags": tags})

    # Metric APIs (using metric service)
    def batch_write_metrics(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Write metrics in batch."""
        return self._request(
            "POST",
            "/metrics/batch",
            base_url=self.metric_url,
            json={"metrics": metrics},
        )

    def batch_write_system_metrics(
        self, metrics: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Write system metrics in batch."""
        return self._request(
            "POST",
            "/metrics/system/batch",
            base_url=self.metric_url,
            json={"metrics": metrics},
        )
