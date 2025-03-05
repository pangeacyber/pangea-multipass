import json
import logging
from typing import Any, Callable, Generic, List, Optional

import requests

from pangea_multipass.core import (
    FilterOperator,
    MetadataFilter,
    PangeaGenericNodeProcessor,
    PangeaMetadataKeys,
    PangeaMetadataValues,
    T,
)


class DropboxClient:
    _actor = "dropbox_client"

    AUTH_URL = "https://www.dropbox.com/oauth2/authorize"
    TOKEN_URL = "https://api.dropbox.com/oauth2/token"
    LIST_FILES_URL = "https://api.dropboxapi.com/2/files/list_folder"
    LIST_CONTINUE_URL = "https://api.dropboxapi.com/2/files/list_folder/continue"

    def __init__(self, logger_name: str = "multipass"):
        self.logger = logging.getLogger(logger_name)

    def download_file(self, token: str, file_path: str):
        """Download a file from Dropbox."""

        headers = {
            "Authorization": f"Bearer {token}",
            "Dropbox-API-Arg": json.dumps({"path": file_path}),
        }

        url = "https://content.dropboxapi.com/2/files/download"
        response = requests.post(url, headers=headers, stream=True)
        if response.status_code != 200:
            self.logger.error(
                json.dumps(
                    {
                        "actor": DropboxClient._actor,
                        "fn": "download_file",
                        "url": url,
                        "data": {"path": file_path},
                        "status_code": response.status_code,
                        "reason": response.reason,
                        "text": response.text,
                    }
                )
            )
        response.raise_for_status()
        return response.content

    def check_user_access(self, token: str, file_path: str, user_email: str):
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
            self._log_error("check_user_access", url, data, response)
            return False

        response_data = response.json()
        self.logger.debug(
            json.dumps(
                {
                    "actor": DropboxClient._actor,
                    "fn": "check_user_access",
                    "actions": "post",
                    "url": url,
                    "data": data,
                    "response": response_data,
                }
            )
        )

        members = response_data.get("users", [])
        for member in members:
            if member.get("user", {}).get("email", "").lower() == user_email.lower():
                return True

        return False

    def list_shared_folders(self, token: str, user_email: str) -> List[str]:
        """
        Lists shared folders that a user has access to in Dropbox.

        :param token: Admin OAuth token with access to all files.
        :param user_email: Email of the user whose accessible folders need to be listed.
        :return: List of folder paths the user has access to.
        """

        accessible_folders: List[str] = []
        has_more = True
        cursor: Optional[str] = None
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        while has_more:
            url = (
                "https://api.dropboxapi.com/2/sharing/list_folders"
                if cursor is None
                else "https://api.dropboxapi.com/2/sharing/list_folders/continue"
            )
            data = {} if cursor is None else {"cursor": cursor}
            response = requests.post(url, json=data, headers=headers)

            if response.status_code != 200:
                self._log_error("list_shared_folders", url, data, response)
                return accessible_folders

            resp_data = response.json()
            self.logger.debug(
                json.dumps(
                    {
                        "actor": DropboxClient._actor,
                        "fn": "list_shared_folders",
                        "actions": "post",
                        "url": url,
                        "data": data,
                        "response": resp_data,
                    }
                )
            )

            shared_folders = resp_data.get("entries", [])
            cursor = resp_data.get("cursor", None)
            has_more = cursor is not None

            for folder in shared_folders:
                folder_id = folder.get("shared_folder_id")
                folder_name = folder.get("name")

                members_url = "https://api.dropboxapi.com/2/sharing/list_folder_members"
                members_data = {"shared_folder_id": folder_id}

                members_response = requests.post(members_url, json=members_data, headers=headers)

                if members_response.status_code == 200:
                    members = members_response.json().get("users", [])
                    for member in members:
                        if member.get("user", {}).get("email", "").lower() == user_email.lower():
                            if not folder_name.startswith("/"):
                                folder_name = f"/{folder_name}"
                            accessible_folders.append(folder_name)
                            break

        return accessible_folders

    def list_subfolders(self, token: str, root: str) -> List[str]:
        """
        Lists all folders in Dropbox.

        :param token: Admin OAuth token with access to all files.
        :return: List of all folder paths.
        """

        folders: List[str] = []
        has_more = True
        cursor: Optional[str] = None
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        while has_more:
            url = DropboxClient.LIST_FILES_URL if cursor is None else DropboxClient.LIST_CONTINUE_URL
            data = {"path": root, "recursive": True, "limit": 100}
            if cursor:
                data = {"cursor": cursor}

            response = requests.post(url, headers=headers, json=data)

            if response.status_code != 200:
                self._log_error("list_subfolders", url, data, response)
                return folders

            resp_data = response.json()
            folder_entries = resp_data.get("entries", [])
            cursor = resp_data.get("cursor", None)
            has_more = resp_data.get("has_more", False)

            for entrie in folder_entries:
                if entrie.get(".tag") != "folder":
                    continue

                folder_path = entrie.get("path_lower", "")
                folders.append(folder_path)

        return folders

    def _log_error(self, function_name: str, url: str, data: dict, response: requests.Response):
        self.logger.error(
            json.dumps(
                {
                    "actor": DropboxClient._actor,
                    "fn": function_name,
                    "url": url,
                    "data": data,
                    "status_code": response.status_code,
                    "reason": response.reason,
                    "text": response.text,
                }
            )
        )


class DropboxProcessor(PangeaGenericNodeProcessor[T], Generic[T]):
    _access_cache: dict[str, bool] = {}
    _token: str
    _folders: List[str] = []
    _user_email: str

    def __init__(
        self,
        token: str,
        user_email: str,
        get_node_metadata: Callable[[T], dict[str, Any]],
        logger_name: str = "multipass",
    ):
        super().__init__()
        self._token = token
        self._access_cache = {}
        self.get_node_metadata = get_node_metadata
        self._user_email = user_email
        self.logger = logging.getLogger(logger_name)
        self._client = DropboxClient(logger_name)

    def _has_access(self, metadata: dict[str, Any]) -> bool:
        """Check if the authenticated user has access to a file."""

        path = metadata.get(PangeaMetadataKeys.DROPBOX_FILE_PATH, "")
        if not path:
            raise KeyError(f"Invalid metadata key: {PangeaMetadataKeys.DROPBOX_FILE_PATH}")

        has_access = self._access_cache.get(path, None)
        if has_access is not None:
            return has_access

        has_access = self._client.check_user_access(token=self._token, file_path=path, user_email=self._user_email)

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

        if not self._folders:
            shared_folders = self._client.list_shared_folders(self._token, self._user_email)
            folders = {value: True for value in shared_folders}

            for folder in shared_folders:
                subfolders = self._client.list_subfolders(self._token, folder)
                folders.update({value: True for value in subfolders})

            self._access_cache = folders
            self._folders = list(folders.keys())

        return MetadataFilter(key=PangeaMetadataKeys.DROPBOX_PATH, value=self._folders, operator=FilterOperator.IN)

    def _is_authorized(self, node: T) -> bool:
        metadata = self.get_node_metadata(node)
        return metadata[
            PangeaMetadataKeys.DATA_SOURCE
        ] == PangeaMetadataValues.DATA_SOURCE_DROPBOX and self._has_access(metadata)
