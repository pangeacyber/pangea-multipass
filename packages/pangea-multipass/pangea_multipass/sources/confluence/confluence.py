# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

import dataclasses
import json
from typing import Any, Callable, Generic, List, Optional

import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError

from pangea_multipass.core import (
    FilterOperator,
    MetadataEnricher,
    MetadataFilter,
    PangeaGenericNodeProcessor,
    PangeaMetadataKeys,
    PangeaMetadataValues,
    T,
)


@dataclasses.dataclass
class ConfluenceAuth:
    """Holds authentication details for Confluence API."""

    email: str
    token: str
    url: str


class ConfluenceME(MetadataEnricher):
    """Enriches Confluence-specific metadata for documents."""

    def __init__(self):
        super().__init__("unused_key")

    def extract_metadata(self, doc: Any, file_content: str) -> dict[str, Any]:
        """
        Extract Confluence-specific metadata for the document.

        Args:
            doc (Any): The document to process.
            file_content (str): The content of the file.

        Returns:
            dict[str, Any]: Extracted metadata including attributes like file name, permissions, and parent folder.
        """
        metadata: dict[str, Any] = {}

        # This step is to normalize some attributes across platforms
        metadata[PangeaMetadataKeys.FILE_NAME] = doc.metadata.get("title", "")
        metadata[PangeaMetadataKeys.DATA_SOURCE] = PangeaMetadataValues.DATA_SOURCE_CONFLUENCE

        # Particular Confluence metadata enricher
        id = self._get_id_from_metadata(doc.metadata)
        if not id:
            raise Exception("No confluence id")
        metadata[PangeaMetadataKeys.CONFLUENCE_PAGE_ID] = id
        return metadata

    def _get_id_from_metadata(self, metadata: dict[str, Any]) -> str:
        # Langchain metadata id value
        value = metadata.get("id", None)
        if value:
            return value

        # Llama Index metadata id value
        value = metadata.get("page_id", None)
        if value:
            return value

        return ""


class ConfluenceProcessor(PangeaGenericNodeProcessor, Generic[T]):
    """Processor for handling Confluence documents with authorization checks."""

    page_ids: List[str] = []
    page_ids_cache: dict[str, bool] = {}
    auth: ConfluenceAuth
    space_id: Optional[int] = None
    get_node_metadata: Callable[[T], dict[str, Any]]
    _account_id: Optional[str]

    def __init__(
        self,
        auth: ConfluenceAuth,
        get_node_metadata: Callable[[T], dict[str, Any]],
        space_id: Optional[int] = None,
        account_id: Optional[str] = None,
    ):
        super().__init__()
        self.auth = auth
        self.space_id = space_id
        self.get_node_metadata = get_node_metadata
        self._account_id = account_id

    def filter(
        self,
        nodes: List[T],
    ) -> List[Any]:
        """Filters nodes based on authorization criteria."""

        filtered: List[T] = []
        for node in nodes:
            if self._is_authorized(node):
                filtered.append(node)
        return filtered

    def get_filter(
        self,
    ) -> MetadataFilter:
        """Returns a filter to use for Confluence document authorization."""

        if not self.page_ids:
            self.page_ids = ConfluenceAPI.load_page_ids(self.auth.email, self.auth.token, self.auth.url, self.space_id)
        return MetadataFilter(
            key=PangeaMetadataKeys.CONFLUENCE_PAGE_ID, value=self.page_ids, operator=FilterOperator.IN
        )

    def _is_authorized(self, node: T) -> bool:
        """Checks if a node is authorized for access."""

        metadata = self.get_node_metadata(node)
        return metadata[
            PangeaMetadataKeys.DATA_SOURCE
        ] == PangeaMetadataValues.DATA_SOURCE_CONFLUENCE and self._has_access(metadata)

    def _has_access(self, metadata: dict[str, Any]) -> bool:
        """Checks access permissions for a specific Confluence page."""

        id = metadata.get(PangeaMetadataKeys.CONFLUENCE_PAGE_ID, None)
        if not id:
            raise KeyError("Invalid metadata key")

        access = self.page_ids_cache.get(id, None)
        if access is not None:
            return access

        auth = HTTPBasicAuth(self.auth.email, self.auth.token)
        try:
            if self._account_id:
                access = ConfluenceAPI.check_user_access(auth, self.auth.url, id, self._account_id)
            else:
                ConfluenceAPI.get_page(auth, self.auth.url, id)
                access = True
        except HTTPError as e:
            if e.response is None or e.response.status_code == 404:
                access = False

        if access is None:
            return False

        self.page_ids_cache[id] = access
        return access


class ConfluenceAPI:
    @staticmethod
    def get_pages(auth: HTTPBasicAuth, url: str, space_id: Optional[int]) -> dict:
        """
        Fetches a list of pages from a Confluence space.

        Args:
            auth (HTTPBasicAuth): The authentication credentials for Confluence.
            url (str): The base URL of the Confluence instance.
            space_id (Optional[int]): The space ID to filter pages by (optional).

        Returns:
            dict: A JSON response containing the list of pages.
        """

        url = f"{url}/wiki/api/v2/pages"
        if space_id:
            url += f"?space-id={space_id}"

        headers = {"Accept": "application/json"}
        response = requests.request(
            "GET",
            url,
            headers=headers,
            auth=auth,
        )
        response.raise_for_status()
        return json.loads(response.text)

    @staticmethod
    def load_page_ids(email: str, token: str, url: str, space_id: Optional[int]) -> List[str]:
        """
        Retrieves IDs of all pages in a specified Confluence space using `get_pages`.

        Args:
            email (str): The email address associated with the Confluence account.
            token (str): The API token for authentication.
            url (str): The base URL of the Confluence instance.
            space_id (Optional[int]): The space ID to filter pages by (optional).

        Returns:
            List[str]: A list of page IDs in the specified space.
        """
        # FIXME: Iterate over pages

        response = ConfluenceAPI.get_pages(HTTPBasicAuth(email, token), url, space_id=space_id)
        pages = response.get("results", [])
        ids = [page["id"] for page in pages]
        return ids

    @staticmethod
    def get_page(auth: HTTPBasicAuth, url: str, page_id: int | str) -> dict:
        """
        Fetches details of a specific Confluence page by its ID.

        Args:
            auth (HTTPBasicAuth): The authentication credentials for Confluence.
            url (str): The base URL of the Confluence instance.
            page_id (int | str): The ID of the page to retrieve.

        Returns:
            dict: A JSON response containing the page details.
        """

        url = f"{url}/wiki/api/v2/pages/{page_id}"

        headers = {"Accept": "application/json"}
        response = requests.request(
            "GET",
            url,
            headers=headers,
            auth=auth,
        )
        response.raise_for_status()
        return json.loads(response.text)

    @staticmethod
    def get_page_details(auth: HTTPBasicAuth, url: str, page_id: str) -> dict:
        """
        Fetch details of a Confluence page, including its parent.

        Args:
            auth (HTTPBasicAuth): The authentication credentials for Confluence.
            url (str): The base URL of the Confluence instance.
            page_id (str): ID of the Confluence page.

        Returns:
            Page details including the parent page ID.
        """

        url = f"{url}/wiki/rest/api/content/{page_id}?expand=ancestors"
        headers = {"Accept": "application/json"}

        try:
            response = requests.get(url, auth=auth, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Error fetching page details for page {page_id}: {e}")

    @staticmethod
    def get_page_restrictions(auth: HTTPBasicAuth, url: str, page_id: str) -> dict:
        """
        Fetch restrictions for a given Confluence page.

        Args:
            auth (HTTPBasicAuth): The authentication credentials for Confluence.
            url (str): The base URL of the Confluence instance.
            page_id (str): ID of the Confluence page.

        Returns:
            List of restrictions.
        """
        url = f"{url}/wiki/rest/api/content/{page_id}/restriction/byOperation"
        headers = {"Accept": "application/json"}

        try:
            response = requests.get(url, auth=auth, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Error fetching restrictions for page {page_id}: {e}")

    @staticmethod
    def check_user_access(auth: HTTPBasicAuth, url: str, page_id: str, account_id: str) -> bool:
        """
        Recursively checks if a user has access to a Confluence page or its parent pages.

        Args:
            auth (HTTPBasicAuth): The authentication credentials for Confluence.
            url (str): The base URL of the Confluence instance.
            page_id (str): ID of the Confluence page.
            account_id (str): Account ID of the user to check access for.

        Returns:
            Boolean indicating whether the user has access.
        """
        current_page: Optional[str] = page_id

        while current_page:
            # TODO: Log to logger
            # print(f"Checking restrictions for page {current_page}...")
            restrictions = ConfluenceAPI.get_page_restrictions(auth, url, current_page)
            if restrictions:
                # TODO: Check group permissions too
                details = restrictions.get("read", {})
                if details:
                    restriction_user = details.get("restrictions", {}).get("user", {})
                    if restriction_user.get("size", 0) > 0:
                        for restriction in restriction_user.get("results", []):
                            if restriction.get("accountId") == account_id:
                                # TODO: Log to logger
                                # print(f"User '{account_id}' has 'read' access to page {page_id} because of {current_page} permission.")
                                return True

                    restriction_group = details.get("restrictions", {}).get("group", {})
                    if restriction_group.get("size", 0) > 0:
                        # Check group restrictions
                        for group in restriction_group.get("results", []):
                            if account_id in ConfluenceAPI.get_group_members(auth, url, group.get("id")):
                                return True

                    if restriction_group.get("size", 0) > 0 or restriction_user.get("size", 0) > 0:
                        # If there is restrictions but didn't allow this users, just return false.
                        # print(f"User '{account_id}' does not have access to the page {page_id}.")
                        return False
            else:
                # TODO: log to logger
                # print(f"No restrictions found for page {current_page}.")
                pass

            # Get parent page ID
            page_details = ConfluenceAPI.get_page_details(auth, url, current_page)
            if page_details.get("ancestors"):
                current_page = page_details["ancestors"][-1]["id"]
            else:
                current_page = None

        # TODO: Log to logger
        # print(f"User '{account_id}' has access to the page {page_id}. There were not restrictions applied.")
        return True

    @staticmethod
    def get_group_members(auth: HTTPBasicAuth, url: str, group_id: str) -> List[str]:
        """
        Fetch all members of a Confluence group.

        Args:
            auth (HTTPBasicAuth): The authentication credentials for Confluence.
            url (str): The base URL of the Confluence instance.
            group_id (str): group id to request members.

        Returns:
            List of account IDs of group members.
        """
        group_members = []
        start = 0
        limit = 50  # Confluence API returns a limited number of results per request

        while True:
            url = f"{url}/wiki/rest/api/group/{group_id}/membersByGroupId?start={start}&limit={limit}"
            headers = {"Accept": "application/json"}

            try:
                response = requests.get(url, auth=auth, headers=headers)
                response.raise_for_status()
                data = response.json()

                for member in data.get("results", []):
                    group_members.append(member["accountId"])

                # Check if there are more members to fetch
                if data.get("size", 0) + start >= data.get("totalSize", 0):
                    break

                start += limit

            except requests.RequestException as e:
                raise Exception(f"Error fetching group members for group '{group_id}': {e}")

        return group_members
