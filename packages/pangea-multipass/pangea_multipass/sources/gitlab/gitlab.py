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


class GitLabAPI:
    @staticmethod
    def get_auth_headers(token: str) -> dict[str, str]:
        """Authenticate to GitLab using a personal access token."""
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def user_has_access(admin_token: str, user_id: str, project_id: str) -> bool:
        """
        Check if a specific user has access to a GitLab project using an admin token.
        """
        headers = GitLabAPI.get_auth_headers(admin_token)
        response = requests.get(
            f"https://gitlab.com/api/v4/projects/{project_id}/members/all/{user_id}", headers=headers
        )

        if response.status_code == 200:
            return True  # User has access
        elif response.status_code == 404:
            return False  # User does not have access
        elif response.status_code == 403:
            raise Exception("Admin token does not have sufficient permissions to check access.")
        else:
            raise Exception(f"Unexpected error: {response.status_code} - {response.json()}")

    @staticmethod
    def get_user(admin_token: str, username: str) -> dict:
        """Get user information using an admin token."""

        response = requests.get(
            f"https://gitlab.com/api/v4/users?username={quote(username)}",
            headers=GitLabAPI.get_auth_headers(admin_token),
        )
        response.raise_for_status()
        users = response.json()
        return users[0] if len(users) else {}

    @staticmethod
    def get_user_projects(admin_token: str) -> list[dict[str, Any]]:
        """Fetch all projects the authenticated user has access to."""
        projects = []
        headers = GitLabAPI.get_auth_headers(admin_token)
        url = f"https://gitlab.com/api/v4/projects"
        params = {"per_page": 100, "membership": True, "simple": True}
        while url:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                raise Exception(f"Error fetching projects: {response.text}")

            projects.extend(response.json())
            url = response.links.get("next", {}).get("url")  # Pagination
        return projects

    @staticmethod
    def get_allowed_projects(admin_token: str, user_id: str) -> list[int]:
        projects = GitLabAPI.get_user_projects(admin_token=admin_token)
        user_projects = []

        for project in projects:
            if GitLabAPI.user_has_access(admin_token, user_id, project["id"]):
                user_projects.append(project["id"])

        return user_projects


class GitLabProcessor(PangeaGenericNodeProcessor[T], Generic[T]):
    _access_cache: dict[str, bool] = {}
    _token: str
    _username: str
    _user_id: Optional[str]
    _projects: list[int] = []
    _get_node_metadata: Callable[[T], dict[str, Any]]

    def __init__(self, admin_token: str, username: str, get_node_metadata: Callable[[T], dict[str, Any]]):
        self._token = admin_token
        self._username = username
        self._access_cache = {}
        self._get_node_metadata = get_node_metadata
        self._user_id = None

    def _has_access(self, metadata: dict[str, Any]) -> bool:
        """Check if the user has access to the given file."""

        project_id = metadata.get(PangeaMetadataKeys.GITLAB_REPOSITORY_ID, None)
        if not project_id:
            raise KeyError(f"Invalid metadata key: {PangeaMetadataKeys.GITLAB_REPOSITORY_ID}")

        if self._user_id is None:
            self._load_user_id()

        if self._user_id is None:
            return False

        if project_id in self._access_cache:
            return self._access_cache[project_id]

        has_access = GitLabAPI.user_has_access(self._token, self._user_id, project_id)
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

            self._projects = GitLabAPI.get_allowed_projects(self._token, self._user_id)

        return MetadataFilter(
            key=PangeaMetadataKeys.GITLAB_REPOSITORY_ID, value=self._projects, operator=FilterOperator.IN
        )

    def _is_authorized(self, node: T) -> bool:
        metadata = self._get_node_metadata(node)
        return metadata[PangeaMetadataKeys.DATA_SOURCE] == PangeaMetadataValues.DATA_SOURCE_GITLAB and self._has_access(
            metadata
        )

    def _load_user_id(self):
        user = GitLabAPI.get_user(self._token, username=self._username)
        self._user_id = user.get("id", None)
