import json
import logging
from typing import Any, Callable, Generic, List, Tuple

import requests

from pangea_multipass.core import (
    FilterOperator,
    MetadataFilter,
    PangeaGenericNodeProcessor,
    PangeaMetadataKeys,
    PangeaMetadataValues,
    T,
)


class GitHubClient:
    _actor = "github_client"

    def __init__(self, logger_name: str = "multipass"):
        self.logger = logging.getLogger(logger_name)

    def get_auth_headers(self, token: str) -> dict[str, str]:
        """Authenticate to GitHub using a personal access token."""
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        return headers

    def has_access(self, token: str, owner: str, repo_name: str) -> bool:
        """
        Check if this token has access to this particular GitHub repository
        """
        access = False

        headers = self.get_auth_headers(token)
        url = f"https://api.github.com/repos/{owner}/{repo_name}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            access = True  # User has access
        elif response.status_code == 404:
            access = False  # Repository not found or no access
        elif response.status_code == 403:
            self._log_error("has_access", url, {}, response)
            raise Exception(f"Access forbidden. Check permissions or token scope.")
        else:
            self._log_error("has_access", url, {}, response)
            raise Exception(f"Unexpected error: {response.status_code} - {response.json()}")

        return access

    def user_has_access(self, admin_token: str, owner: str, repo_name: str, username: str) -> bool:
        """
        Checks if a user has access to a specific GitHub repository using an admin token
        """
        headers = self.get_auth_headers(admin_token)
        url = f"https://api.github.com/repos/{owner}/{repo_name}/collaborators/{username}"
        response = requests.get(url, headers=headers)

        if response.status_code == 204:
            return True
        elif response.status_code == 404:
            return False
        elif response.status_code == 403:
            self._log_error("user_has_access", url, {}, response)
            raise Exception("Admin token does not have sufficient permissions to check access.")
        else:
            self._log_error("user_has_access", url, {}, response)
            raise Exception(f"Unexpected error: {response.status_code} - {response.json()}")

    def get_user_repos(self, token: str) -> List[dict[str, Any]]:
        """Get all repositories the authenticated user has access to."""

        headers = self.get_auth_headers(token)
        url = "https://api.github.com/user/repos"
        repos: List[dict[str, Any]] = []
        page = 1

        while True:
            response = requests.get(url, headers=headers, params={"per_page": 100, "page": page})
            if response.status_code != 200:
                self._log_error("get_user_repos", url, {"per_page": 100, "page": page}, response)
                raise Exception(f"Error fetching repositories: {response.json()}")

            data = response.json()
            if not data:
                break

            repos.extend(data)
            page += 1

        return repos

    def get_repo_files(self, token: str, owner: str, repo: str) -> List[dict[str, Any]]:
        """Fetch all files in a repository using the GitHub Tree API."""

        headers = self.get_auth_headers(token)

        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            tree_data = response.json()
            return [item for item in tree_data.get("tree", []) if item["type"] == "blob"]
        elif response.status_code == 404:
            self.logger.warning(f"Repository '{repo}' not found.")
            return []
        else:
            self._log_error("get_repo_files", url, {}, response)
            raise Exception(f"Error fetching files for repository '{repo}': {response.json()}")

    def download_file_content(self, token: str, url: str) -> str:
        """Download the content of a file from GitHub."""

        headers = self.get_auth_headers(token)

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return str(response.content)
        else:
            self._log_error("download_file_content", url, {}, response)
            raise Exception(f"Error downloading file: {response.json()}")

    def get_allowed_repos(self, token: str, username: str) -> List[dict]:
        projects = self.get_user_repos(token)
        user_projects = []

        for project in projects:
            if self.user_has_access(token, project["owner"]["login"], project["name"], username):
                user_projects.append(project)

        return user_projects

    def _log_error(self, function_name: str, url: str, data: dict, response: requests.Response):
        self.logger.error(
            json.dumps(
                {
                    "actor": GitHubClient._actor,
                    "fn": function_name,
                    "url": url,
                    "data": data,
                    "status_code": response.status_code,
                    "reason": response.reason,
                    "text": response.text,
                }
            )
        )


class GitHubProcessor(PangeaGenericNodeProcessor[T], Generic[T]):
    _access_cache: dict[Tuple[str, str], bool] = {}
    _token: str
    _repos: List[Tuple[str, str]] = []
    _username: str

    def __init__(
        self,
        token: str,
        get_node_metadata: Callable[[T], dict[str, Any]],
        username: str,
        logger_name: str = "multipass",
    ):
        super().__init__()
        self._token = token
        self._access_cache = {}
        self.get_node_metadata = get_node_metadata
        self._username = username
        self._client = GitHubClient(logger_name)

    def filter(
        self,
        nodes: List[T],
    ) -> List[T]:
        """Filter GitHub files by access permissions.

        Args:
            nodes (List[T]): List of nodes to process.

        Returns:
            List[Any]: Nodes that have authorized access.
        """

        filtered: List[T] = []
        for node in nodes:
            if self._is_authorized(node):
                filtered.append(node)
        return filtered

    def get_filter(
        self,
    ) -> MetadataFilter:
        """Generate a filter based on accessible Jira issue IDs.

        Returns:
            MetadataFilter: Filter for Jira issue IDs.
        """

        if not self._repos:
            repos_info = self._client.get_allowed_repos(self._token, username=self._username)
            repos = []

            for repo in repos_info:
                owner = repo["owner"]["login"]
                repo_name = repo["name"]
                repos.append((owner, repo_name))

        self._repos = repos

        return MetadataFilter(
            key=PangeaMetadataKeys.GITHUB_REPOSITORY_OWNER_AND_NAME, value=self._repos, operator=FilterOperator.IN
        )

    def _has_access(self, metadata: dict[str, Any]) -> bool:
        """Check if the authenticated user has access to a repository."""

        repo_name = metadata.get(PangeaMetadataKeys.GITHUB_REPOSITORY_NAME, None)
        if repo_name is None:
            raise KeyError(f"Invalid metadata key: {PangeaMetadataKeys.GITHUB_REPOSITORY_NAME}")

        owner = metadata.get(PangeaMetadataKeys.GITHUB_REPOSITORY_OWNER, None)
        if owner is None:
            raise KeyError(f"Invalid metadata key: {PangeaMetadataKeys.GITHUB_REPOSITORY_OWNER}")

        access_tuple = (owner, repo_name)
        has_access = self._access_cache.get(access_tuple, None)
        if has_access is not None:
            return has_access

        if self._username:
            has_access = self._client.user_has_access(
                admin_token=self._token, owner=owner, repo_name=repo_name, username=self._username
            )
        else:
            has_access = self._client.has_access(token=self._token, owner=owner, repo_name=repo_name)

        self._access_cache[access_tuple] = has_access
        return has_access

    def _is_authorized(self, node: T) -> bool:
        metadata = self.get_node_metadata(node)
        return metadata[PangeaMetadataKeys.DATA_SOURCE] == PangeaMetadataValues.DATA_SOURCE_GITHUB and self._has_access(
            metadata
        )
