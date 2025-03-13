import json
import logging
from typing import Any, Callable, Generic, List, Optional
from urllib.parse import quote

import requests

from pangea_multipass.core import (
    FilterOperator,
    MetadataFilter,
    PangeaGenericNodeProcessor,
    PangeaMetadataKeys,
    PangeaMetadataValues,
    T,
)


class GitLabClient:
    _actor = "gitlab_client"

    def __init__(self, logger_name: str = "multipass"):
        self.logger = logging.getLogger(logger_name)

    def get_auth_headers(self, token: str) -> dict[str, str]:
        """Authenticate to GitLab using a personal access token."""
        return {"Authorization": f"Bearer {token}"}

    def user_has_access(self, admin_token: str, user_id: str, project_id: str) -> bool:
        """
        Check if a specific user has access to a GitLab project using an admin token.
        """
        url = f"https://gitlab.com/api/v4/projects/{project_id}/members/all/{user_id}"
        headers = self.get_auth_headers(admin_token)
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return True  # User has access
        elif response.status_code == 404:
            return False  # User does not have access
        elif response.status_code == 403:
            self._log_error("user_has_access", url, {}, response)
            raise Exception("Admin token does not have sufficient permissions to check access.")
        else:
            self._log_error("user_has_access", url, {}, response)
            raise Exception(f"Unexpected error: {response.status_code} - {response.json()}")

    def get_user(self, admin_token: str, username: str) -> dict:
        """Get user information using an admin token."""

        url = f"https://gitlab.com/api/v4/users?username={quote(username)}"
        response = requests.get(
            url,
            headers=self.get_auth_headers(admin_token),
        )

        if response.status_code != 200:
            self._log_error("get_user", url, {}, response)

        response.raise_for_status()
        users = response.json()
        return users[0] if len(users) else {}

    def get_user_info(self, admin_token: str) -> dict:
        """Get user information from current token"""

        url = "https://gitlab.com/api/v4/user/"
        response = requests.get(
            url,
            headers=self.get_auth_headers(admin_token),
        )

        if response.status_code != 200:
            self._log_error("get_user_info", url, {}, response)

        response.raise_for_status()
        return response.json()

    def get_user_projects(self, admin_token: str) -> list[dict[str, Any]]:
        """Fetch all projects the authenticated user has access to."""
        projects = []
        headers = self.get_auth_headers(admin_token)
        url = f"https://gitlab.com/api/v4/projects"
        params = {"per_page": 100, "membership": True, "simple": True}
        while url:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                self._log_error("get_user_projects", url, params, response)
                raise Exception(f"Error fetching projects: {response.text}")

            projects.extend(response.json())
            url = response.links.get("next", {}).get("url")  # Pagination
        return projects

    def get_allowed_projects(self, admin_token: str, user_id: str) -> list[int]:
        projects = self.get_user_projects(admin_token=admin_token)
        user_projects = []

        for project in projects:
            if self.user_has_access(admin_token, user_id, project["id"]):
                user_projects.append(project["id"])

        return user_projects

    def download_file(self, token: str, repo_id: str, file_path: str):
        encoded_file_path = quote(file_path, safe="")  # Encode special chars
        file_url = f"https://gitlab.com/api/v4/projects/{repo_id}/repository/files/{encoded_file_path}/raw"

        response = requests.get(file_url, headers=self.get_auth_headers(token))
        if response.status_code != 200:
            self._log_error("download_file", file_url, {}, response)
            raise Exception(f"Skipping {file_path}: Could not download file")

        return response.content

    def _log_error(self, function_name: str, url: str, data: dict, response: requests.Response):
        self.logger.error(
            json.dumps(
                {
                    "actor": GitLabClient._actor,
                    "fn": function_name,
                    "url": url,
                    "data": data,
                    "status_code": response.status_code,
                    "reason": response.reason,
                    "text": response.text,
                }
            )
        )


class GitLabProcessor(PangeaGenericNodeProcessor[T], Generic[T]):
    _access_cache: dict[str, bool] = {}
    _token: str
    _username: str
    _user_id: Optional[str]
    _projects: list[int] = []
    _get_node_metadata: Callable[[T], dict[str, Any]]

    def __init__(
        self,
        admin_token: str,
        username: str,
        get_node_metadata: Callable[[T], dict[str, Any]],
        logger_name: str = "multipass",
    ):
        self._token = admin_token
        self._username = username
        self._access_cache = {}
        self._get_node_metadata = get_node_metadata
        self._user_id = None
        self._client = GitLabClient(logger_name)

    def _has_access(self, metadata: dict[str, Any]) -> bool:
        """Check if the user has access to the given file."""

        project_id = metadata.get(PangeaMetadataKeys.GITLAB_REPOSITORY_ID, None)
        if not project_id:
            raise KeyError(f"Invalid metadata key: {PangeaMetadataKeys.GITLAB_REPOSITORY_ID}")

        if self._user_id is None:
            self._load_user_id()

        if self._user_id is None:
            print("Could not load user ID")
            return False

        if project_id in self._access_cache:
            return self._access_cache[project_id]

        has_access = self._client.user_has_access(self._token, self._user_id, project_id)
        self._access_cache[project_id] = has_access
        return has_access

    def filter(
        self,
        nodes: List[T],
    ) -> List[T]:
        """Filter GitLab files by access permissions.

        Args:
            nodes (List[T]): List of nodes to process.

        Returns:
            List[T]: Nodes that have authorized access.
        """

        filtered: List[T] = []
        for node in nodes:
            if self._is_authorized(node):
                filtered.append(node)
        return filtered

    def get_filter(
        self,
    ) -> MetadataFilter:
        """Generate a filter based on accessible GitLab project IDs.

        Returns:
            MetadataFilter: Filter for GitLab project IDs.
        """

        if not self._projects:
            if self._user_id is None:
                self._load_user_id()

            if self._user_id is None:
                raise Exception("Could not load user ID")

            self._projects = self._client.get_allowed_projects(self._token, self._user_id)

        return MetadataFilter(
            key=PangeaMetadataKeys.GITLAB_REPOSITORY_ID, value=self._projects, operator=FilterOperator.IN
        )

    def _is_authorized(self, node: T) -> bool:
        metadata = self._get_node_metadata(node)
        return metadata[PangeaMetadataKeys.DATA_SOURCE] == PangeaMetadataValues.DATA_SOURCE_GITLAB and self._has_access(
            metadata
        )

    def _load_user_id(self):
        user = self._client.get_user(self._token, username=self._username)
        self._user_id = user.get("id", None)
