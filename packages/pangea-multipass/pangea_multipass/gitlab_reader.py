from typing import Any, List, Optional

import requests

from .sources import GitLabAPI
from pangea_multipass import MultipassDocument, PangeaMetadataKeys, PangeaMetadataValues, generate_id


class GitLabReader:
    _token: str
    _has_more_files: bool
    _next_files_page: Optional[str]
    _current_repository: dict

    def __init__(self, token: str):
        self._token = token
        self._restart()

    def get_repos(self):
        """Get all the repositories the token has access to"""
        return GitLabAPI.get_user_projects(self._token)

    def read_repo_files(self, repository: dict, page_size: int = 100) -> List[MultipassDocument]:
        """
        Read files from a given repository
        If the repository is different from the last one, it will restart the reader.
        If the repository is the same, it will continue reading from the last file.
        """
        self._read_repo_files_checks(repository, page_size)
        if self._next_files_page is None:
            return []

        response = requests.get(self._next_files_page, headers={"Authorization": f"Bearer {self._token}"})

        repo_id = self._current_repository.get("id", None)
        if response.status_code != 200:
            raise Exception(f"Skipping {repo_id}: Could not fetch file tree")

        documents: List[MultipassDocument] = []
        files = response.json()
        for file in files:
            if file["type"] == "blob":  # Only download actual files
                file_path = file["path"]
                file_name = file["name"]
                repo_name = self._current_repository.get("name", "")
                repo_namespace_path = self._current_repository.get("path_with_namespace", "")
                content = GitLabAPI.download_file(self._token, repo_id, file_path)
                metadata: dict[str, Any] = {
                    PangeaMetadataKeys.DATA_SOURCE: PangeaMetadataValues.DATA_SOURCE_GITLAB,
                    PangeaMetadataKeys.GITLAB_REPOSITORY_ID: repo_id,
                    PangeaMetadataKeys.GITLAB_REPOSITORY_NAME: repo_name,
                    PangeaMetadataKeys.GITLAB_REPOSITORY_NAMESPACE_WITH_PATH: repo_namespace_path,
                    PangeaMetadataKeys.FILE_PATH: file_path,
                    PangeaMetadataKeys.FILE_NAME: file_name,
                }
                documents.append(MultipassDocument(generate_id(), content, metadata))

        self._next_files_page = response.links.get("next", {}).get("url", None)  # Check if pagination has next page
        self._has_more_files = self._next_files_page is not None

        return documents

    def load_data(self) -> List[MultipassDocument]:
        """
        Load all the data from the repositories
        This will read all the files from all the repositories the token has access to.
        This process is blocking and can take a long time. If working with a large number of repositories,
        consider using the read_repo_files method.
        """
        documents: List[MultipassDocument] = []
        repos = self.get_repos()

        for repo in repos:
            has_more_files = True
            while has_more_files:
                files = self.read_repo_files(repository=repo)
                documents.extend(files)
                has_more_files = self.has_more_files

        return documents

    @property
    def has_more_files(self):
        """Check if there are more files to read"""
        return self._has_more_files

    def _restart(self):
        self._has_more_files = True
        self._next_files_page = None
        self._current_repository = {}

    def _read_repo_files_checks(self, repository: dict, page_size: int) -> None:
        current_repo_id = self._current_repository.get("id", None)
        new_repo_id = repository.get("id", None)
        if current_repo_id is None or current_repo_id != new_repo_id:
            self._restart()
            self._current_repository = repository

        if self._has_more_files is True and self._next_files_page is None:
            repo_id = repository.get("id", None)
            if repo_id is None:
                raise Exception("Invalid repository id")

            self._next_files_page = f"https://gitlab.com/api/v4/projects/{repo_id}/repository/tree?recursive=true&per_page={page_size}&pagination=keyset"
        else:
            self._has_more_files = False
