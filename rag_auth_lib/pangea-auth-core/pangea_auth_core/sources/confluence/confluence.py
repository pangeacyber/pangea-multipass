# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

from typing import Any, List, Callable, Optional, Generic
import requests
import json
from requests.exceptions import HTTPError
from requests.auth import HTTPBasicAuth
import dataclasses
from pangea_auth_core.core import (
    MetadataEnricher,
    PangeaMetadataKeys,
    PangeaMetadataValues,
    PangeaGenericNodeProcessor,
    MetadataFilter,
    FilterOperator,
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

    _get_doc_id: Callable[[Any], str]

    def __init__(self, get_doc_id: Callable[[Any], str]):
        self._get_doc_id = get_doc_id

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
        metadata[PangeaMetadataKeys.CONFLUENCE_PAGE_ID] = self._get_doc_id(doc)
        return metadata


class ConfluenceProcessor(PangeaGenericNodeProcessor, Generic[T]):
    """Processor for handling Confluence documents with authorization checks."""

    page_ids: List[str] = []
    page_ids_cache: dict[str, bool] = {}
    auth: ConfluenceAuth
    space_id: Optional[int] = None
    get_node_metadata: Callable[[T], dict[str, Any]]

    def __init__(
        self, auth: ConfluenceAuth, get_node_metadata: Callable[[T], dict[str, Any]], space_id: Optional[int] = None
    ):
        super().__init__()
        self.auth = auth
        self.space_id = space_id
        self.get_node_metadata = get_node_metadata

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
        if id is None:
            raise KeyError("Invalid metadata key")

        access = self.page_ids_cache.get(id, None)
        if access is not None:
            return access

        try:
            ConfluenceAPI.get_page(HTTPBasicAuth(self.auth.email, self.auth.token), self.auth.url, id)
            access = True
        except HTTPError as e:
            if e.response.status_code == 404:
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
    def get_page(auth, url: str, page_id: int | str) -> dict:
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
