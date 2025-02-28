from typing import Any, List, Optional

from .core import MultipassDocument, PangeaMetadataKeys, PangeaMetadataValues, generate_id
from .sources.github import GitHubAPI


class GitHubReader:
    _token: str
    """GitHub personal access token"""

    _current_file: int = 0
    _repo_files: Optional[List[dict]] = None
    _current_repository: dict = {}

    def __init__(self, token: str):
        self._token = token
        self._restart()

    def load_data(
        self,
    ) -> List[MultipassDocument]:
        """
        Load all the data from the repositories
        This will read all the files from all the repositories the token has access to.
        This process is blocking and can take a long time. If working with a large number of repositories,
        consider using the read_repo_files method.
        """
        documents: List[MultipassDocument] = []

        # Get repositories
        repos = GitHubAPI.get_user_repos(self._token)

        for repo in repos:
            owner = repo["owner"]["login"]
            repo_name = repo["name"]

            # Get all files recursively
            files = GitHubAPI.get_repo_files(self._token, owner, repo_name)

            for file in files:
                file_path = file["path"]
                download_url = file["url"]

                # Fetch the file content
                content = GitHubAPI.download_file_content(self._token, download_url)

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

    def read_repo_files(self, repository: dict, page_size: int = 100) -> List[MultipassDocument]:
        """
        Read files from a given repository
        If the repository is different from the last one, it will restart the reader.
        If the repository is the same, it will continue reading from the last file.
        """
        documents: List[MultipassDocument] = []

        self._read_repo_files_checks(repository)
        if self._repo_files is None:
            return documents

        owner = self._current_repository["owner"]["login"]
        repo_name = self._current_repository["name"]

        i = 0
        while i < page_size and self._current_file < len(self._repo_files):
            file = self._repo_files[self._current_file]
            i += 1
            self._current_file += 1

            file_path = file["path"]
            download_url = file["url"]

            # Fetch the file content
            content = GitHubAPI.download_file_content(self._token, download_url)

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

    def get_repos(self) -> List[dict]:
        """Get all the repositories the token has access to"""
        return GitHubAPI.get_user_repos(self._token)

    @property
    def has_more_files(self):
        """Check if there are more files to read"""
        return self._repo_files is not None and self._current_file < len(self._repo_files)

    def _restart(self) -> None:
        self._current_file = 0
        self._repo_files = None
        self._current_repository = {}

    def _read_repo_files_checks(self, repository: dict) -> None:
        current_repo_id = self._current_repository.get("id", None)
        new_repo_id = repository.get("id", None)

        if current_repo_id is None or current_repo_id != new_repo_id:
            self._restart()
            self._current_repository = repository

        owner = self._current_repository["owner"]["login"]
        repo_name = self._current_repository["name"]

        if self._repo_files is None:
            self._repo_files = GitHubAPI.get_repo_files(self._token, owner, repo_name)
