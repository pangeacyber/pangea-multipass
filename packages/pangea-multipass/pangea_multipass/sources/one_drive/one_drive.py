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


class OneDriveClient:
    def check_user_access(self, admin_token: str, user_id: str, item_id: str):
        """
        Checks if a user has access to a specific OneDrive file using an admin token.

        Parameters:
        - admin_token (str): Microsoft Graph API access token with admin privileges.
        - user_id (str): ID of the user to check access for.
        - item_id (str): ID of the file in OneDrive.

        Returns:
        - Boolean indicating whether the user has access to the file.
        """
        # url = f"https://graph.microsoft.com/v1.0/users/{user_id}/drive/items/{item_id}/preview"
        url = f"https://graph.microsoft.com/v1.0/users/{user_id}/drive/items/{item_id}/permissions"

        headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return True
        elif response.status_code == 403:
            # FIXME: Log to logger
            print("Access denied: Admin token does not have required permissions.")
        elif response.status_code == 404:
            print("File not found or user has no access.")
        else:
            print(f"Error: {response.status_code}, {response.text}")

        return False

    def get_user_id(self, admin_token: str, user_email: str) -> Optional[str]:
        """
        Fetches the Microsoft Entra ID (Azure AD) user ID based on the user's email.

        Parameters:
        - admin_token (str): Microsoft Graph API access token with admin privileges.
        - user_email (str): Email of the user to fetch the ID for.

        Returns:
        - str: The user's Microsoft Entra ID (Azure AD user ID) if found, else None.
        """
        url = f"https://graph.microsoft.com/v1.0/users/{user_email}"

        headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            user_data = response.json()
            return user_data.get("id")  # Return the user's ID
        elif response.status_code == 404:
            print("User not found.")
        elif response.status_code == 403:
            print("Access denied: Ensure your token has 'User.Read.All' or 'Directory.Read.All' permissions.")
        else:
            print(f"Error: {response.status_code}, {response.text}")

        return None


class OneDriveProcessor(PangeaGenericNodeProcessor[T], Generic[T]):
    _access_cache: dict[str, bool] = {}
    _token: str
    _username: str
    _user_id: str
    _file_ids: list[str] = []
    _get_node_metadata: Callable[[T], dict[str, Any]]

    def __init__(self, admin_token: str, user_id: str, get_node_metadata: Callable[[T], dict[str, Any]]):
        self._token = admin_token
        self._access_cache = {}
        self._get_node_metadata = get_node_metadata
        self._user_id = user_id
        self._client = OneDriveClient()

    def _has_access(self, metadata: dict[str, Any]) -> bool:
        """Check if the user has access to the given file."""

        file_id = metadata.get(PangeaMetadataKeys.ONEDRIVE_ID, None)
        if not file_id:
            raise KeyError(f"Invalid metadata key: {PangeaMetadataKeys.ONEDRIVE_ID}")

        if file_id in self._access_cache:
            return self._access_cache[file_id]

        has_access = self._client.check_user_access(self._token, self._user_id, file_id)
        self._access_cache[file_id] = has_access
        return has_access

    def filter(
        self,
        nodes: List[T],
    ) -> List[T]:
        """Filter OneDrive files by access permissions.

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
        #     """Generate a filter based on accessible OneDrive project IDs.

        #     Returns:
        #         MetadataFilter: Filter for OneDrive project IDs.
        #     """

        #     if not self._projects:
        #         if self._user_id is None:
        #             self._load_user_id()

        #         if self._user_id is None:
        #             raise Exception("Could not load user ID")

        #         self._projects = GitLabAPI.get_allowed_projects(self._token, self._user_id)

        return MetadataFilter(key=PangeaMetadataKeys.ONEDRIVE_ID, value=self._file_ids, operator=FilterOperator.IN)

    def _is_authorized(self, node: T) -> bool:
        metadata = self._get_node_metadata(node)
        return metadata[
            PangeaMetadataKeys.DATA_SOURCE
        ] == PangeaMetadataValues.DATA_SOURCE_ONEDRIVE and self._has_access(metadata)
