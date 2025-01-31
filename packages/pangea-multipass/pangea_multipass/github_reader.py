from typing import Any, List

import requests

from .core import MultipassDocument, PangeaMetadataKeys, PangeaMetadataValues, generate_id
from .sources.github import GitHubAPI


class GitHubReader:
    _token: str
    """GitHub personal access token"""

    def __init__(self, token: str):
        self._token = token

    def load_data(
        self,
    ) -> List[MultipassDocument]:
        # Authenticate
        headers = GitHubAPI.get_auth_headers(self._token)

        # Get repositories
        repos = GitHubAPI.get_user_repos(self._token)

        documents: List[MultipassDocument] = []

        for repo in repos:
            owner = repo["owner"]["login"]
            repo_name = repo["name"]

            # Get all files recursively
            files = self._get_repo_files(headers, owner, repo_name)

            for file in files:
                file_path = file["path"]
                download_url = file["download_url"]

                # Fetch the file content
                content = self._download_file_content(headers, download_url)

                # Create metadata
                metadata: dict[str, Any] = {
                    PangeaMetadataKeys.GITHUB_REPOSITORY_NAME: repo_name,
                    PangeaMetadataKeys.GITHUB_REPOSITORY_OWNER: owner,
                    PangeaMetadataKeys.FILE_PATH: file_path,
                    PangeaMetadataKeys.FILE_NAME: file_path,
                    PangeaMetadataKeys.DATA_SOURCE: PangeaMetadataValues.DATA_SOURCE_GITHUB,
                    PangeaMetadataKeys.GITHUB_REPOSITORY_OWNER_AND_NAME: (owner, repo_name),
                }

                doc = MultipassDocument(id=generate_id(), content=content, metadata=metadata)
                documents.append(doc)

        return documents

    def _get_repo_files(self, headers: dict[str, Any], owner: str, repo: str, path: str = "") -> List[dict[str, Any]]:
        """Recursively fetch all files and directories in a repository."""

        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            items = response.json()
            files: List[dict[str, Any]] = []
            for item in items:
                if item["type"] == "file":
                    files.append(item)
                elif item["type"] == "dir":
                    files.extend(self._get_repo_files(headers, owner, repo, item["path"]))
            return files
        elif response.status_code == 404:
            return []
        else:
            raise Exception(f"Error fetching files for repository '{repo}': {response.json()}")

    def _download_file_content(self, headers: dict[str, Any], url: str) -> str:
        """Download the content of a file from GitHub."""
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return str(response.content)
        else:
            raise Exception(f"Error downloading file: {response.json()}")
