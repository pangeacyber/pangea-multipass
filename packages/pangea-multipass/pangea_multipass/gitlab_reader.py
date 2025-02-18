from typing import Any, List, Optional
from urllib.parse import quote

import requests

from pangea_multipass import MultipassDocument, PangeaMetadataKeys, PangeaMetadataValues, generate_id


class GitLabReader:
    _token: str
    _page_size: int
    _has_more_files: bool
    _has_more_repos: bool
    _next_repo_page: Optional[str]
    _next_files_page: Optional[str]
    _current_repository: dict

    def __init__(self, token: str, page_size: int = 20):
        self._token = token
        self._page_size = page_size
        self.restart()

    def _get_headers(self):
        return {"Authorization": f"Bearer {self._token}"}

    def get_repos(self):
        url = (
            self._next_repo_page
            if self._next_repo_page
            else f"https://gitlab.com/api/v4/projects?pagination=keyset&per_page=20&order_by=id&sort=asc&simple=true&membership=true"
        )

        response = requests.get(url, headers=self._get_headers())
        if response.status_code != 200:
            raise Exception(f"Failed to fetch repositories: {response.status_code} - {response.text}")

        repos = response.json()
        self._next_repo_page = response.links.get("next", {}).get("url", None)  # Check if pagination has next page
        self._has_more_repos = self._next_repo_page is not None
        return repos

    def read_repo_files(self, repository: Optional[dict] = None) -> List[MultipassDocument]:
        if repository is not None:
            repo_id = repository.get("id", None)
            if repo_id is None:
                raise Exception("Invalid repository id")

            url = f"https://gitlab.com/api/v4/projects/{repo_id}/repository/tree?recursive=true&per_page={self._page_size}&pagination=keyset"
            self._next_files_page = None
            self._has_more_files = True
            self._current_repository = repository
        elif self._next_files_page is not None:
            url = self._next_files_page
        else:
            self._has_more_files = False
            return []

        repo_id = self._current_repository.get("id", None)

        response = requests.get(url, headers=self._get_headers())

        if response.status_code != 200:
            raise Exception(f"Skipping {repo_id}: Could not fetch file tree")

        self._next_files_page = response.links.get("next", {}).get("url", None)  # Check if pagination has next page
        documents: List[MultipassDocument] = []

        files = response.json()
        for file in files:
            if file["type"] == "blob":  # Only download actual files
                file_path = file["path"]
                file_name = file["name"]
                repo_name = self._current_repository.get("name", "")
                repo_namespace_path = self._current_repository.get("path_with_namespace", "")
                content = self._download_file(repo_id, file_path)
                metadata: dict[str, Any] = {
                    PangeaMetadataKeys.DATA_SOURCE: PangeaMetadataValues.DATA_SOURCE_GITLAB,
                    PangeaMetadataKeys.GITLAB_REPOSITORY_ID: repo_id,
                    PangeaMetadataKeys.GITLAB_REPOSITORY_NAME: repo_name,
                    PangeaMetadataKeys.GITLAB_REPOSITORY_NAMESPACE_WITH_PATH: repo_namespace_path,
                    PangeaMetadataKeys.FILE_PATH: file_path,
                    PangeaMetadataKeys.FILE_NAME: file_name,
                }
                documents.append(MultipassDocument(generate_id(), content, metadata))

        return documents

    def _download_file(self, repo_id: str, file_path: str):
        encoded_file_path = quote(file_path, safe="")  # Encode special chars
        file_url = f"https://gitlab.com/api/v4/projects/{repo_id}/repository/files/{encoded_file_path}/raw"

        response = requests.get(file_url, headers=self._get_headers())
        if response.status_code != 200:
            raise Exception(f"Skipping {file_path}: Could not download file")

        return response.content

    def load_data(self) -> List[MultipassDocument]:
        documents: List[MultipassDocument] = []
        repos = self.get_repos()

        while self.has_more_repos:
            for repo in repos:
                files = self.read_repo_files(repository=repo)
                documents.extend(files)

                while self.has_more_files:
                    files = self.read_repo_files(repository=None)
                    documents.extend(files)

            repos = self.get_repos()

        return documents

    @property
    def has_more_files(self):
        return self._has_more_files

    @property
    def has_more_repos(self):
        return self._has_more_repos

    def restart(self):
        self._has_more_files = True
        self._has_more_repos = True
        self._next_files_page = None
        self._next_repo_page = None
        self._current_repository = {}
