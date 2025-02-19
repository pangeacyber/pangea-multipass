import json
from typing import Any, Callable, Generic, List

import requests

from pangea_multipass.core import (
    FilterOperator,
    MetadataFilter,
    PangeaGenericNodeProcessor,
    PangeaMetadataKeys,
    PangeaMetadataValues,
    T,
)


class DropboxAPI:
    AUTH_URL = "https://www.dropbox.com/oauth2/authorize"
    TOKEN_URL = "https://api.dropbox.com/oauth2/token"
    LIST_FILES_URL = "https://api.dropboxapi.com/2/files/list_folder"
    LIST_CONTINUE_URL = "https://api.dropboxapi.com/2/files/list_folder/continue"

    @staticmethod
    def download_file(token: str, file_path: str):
        """Download a file from Dropbox."""

        headers = {
            "Authorization": f"Bearer {token}",
            "Dropbox-API-Arg": json.dumps({"path": file_path}),
        }

        response = requests.post("https://content.dropboxapi.com/2/files/download", headers=headers, stream=True)
        response.raise_for_status()
        return response.content

    @staticmethod
    def check_user_access(token: str, file_path: str, user_email: str):
        """
        Checks if a user has access to a specific Dropbox file.

        :param token: Admin OAuth token with access to all files.
        :param file_path: Path to the file in Dropbox (e.g., "/Documents/file.txt").
        :param user_email: Email of the user whose access needs to be checked.
        :return: Boolean indicating whether the user has access.
        """
        url = "https://api.dropboxapi.com/2/sharing/list_file_members"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        data = {"file": file_path}

        response = requests.post(url, json=data, headers=headers)
        if response.status_code != 200:
            return False

        members = response.json().get("users", [])
        for member in members:
            if member.get("user", {}).get("email", "").lower() == user_email.lower():
                return True

        return False

    @staticmethod
    def list_user_files(token: str, user_email: str):
        """
        Lists all files and folders that a user has access to in Dropbox.

        :param token: Admin OAuth token with access to all files.
        :param user_email: Email of the user whose accessible files need to be listed.
        :return: List of file paths the user has access to.
        """
        url = "https://api.dropboxapi.com/2/sharing/list_folders"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        response = requests.post(url, json={}, headers=headers)

        if response.status_code != 200:
            return []

        accessible_files = []
        shared_folders = response.json().get("entries", [])

        for folder in shared_folders:
            folder_id = folder.get("shared_folder_id")
            folder_name = folder.get("name")

            members_url = "https://api.dropboxapi.com/2/sharing/list_folder_members"
            members_data = {"shared_folder_id": folder_id}

            members_response = requests.post(members_url, json=members_data, headers=headers)

            if members_response.status_code == 200:
                members = members_response.json().get("users", [])
                for member in members:
                    if member.get("email", "").lower() == user_email.lower():
                        accessible_files.append(folder_name)
                        break

        return accessible_files


class DropboxProcessor(PangeaGenericNodeProcessor[T], Generic[T]):
    _access_cache: dict[str, bool] = {}
    _token: str
    _files: List[str] = []
    _user_email: str

    def __init__(self, token: str, get_node_metadata: Callable[[T], dict[str, Any]], user_email: str):
        super().__init__()
        self._token = token
        self._access_cache = {}
        self.get_node_metadata = get_node_metadata
        self._user_email = user_email

    def _has_access(self, metadata: dict[str, Any]) -> bool:
        """Check if the authenticated user has access to a file."""

        path = metadata.get(PangeaMetadataKeys.DROPBOX_FILE_PATH, "")
        if not path:
            raise KeyError(f"Invalid metadata key: {PangeaMetadataKeys.DROPBOX_FILE_PATH}")

        has_access = self._access_cache.get(path, None)
        if has_access is not None:
            return has_access

        has_access = DropboxAPI.check_user_access(token=self._token, file_path=path, user_email=self._user_email)

        self._access_cache[path] = has_access
        return has_access

    def filter(
        self,
        nodes: List[T],
    ) -> List[T]:
        """Filter Dropbox files by access permissions.

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
        """Generate a filter based on accessible Dropbox paths.

        Returns:
            MetadataFilter: Filter for Dropbox paths.
        """

        if not self._files:
            self._files = DropboxAPI.list_user_files(self._token, self._user_email)
            self._access_cache = {value: True for value in self._files}

        return MetadataFilter(key=PangeaMetadataKeys.DROPBOX_FILE_PATH, value=self._files, operator=FilterOperator.IN)

    def _is_authorized(self, node: T) -> bool:
        metadata = self.get_node_metadata(node)
        return metadata[
            PangeaMetadataKeys.DATA_SOURCE
        ] == PangeaMetadataValues.DATA_SOURCE_DROPBOX and self._has_access(metadata)
