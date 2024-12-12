# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

from typing import Any, List, Callable, Generic
import requests
import dataclasses
from requests.exceptions import HTTPError
from requests.auth import HTTPBasicAuth
from pangea_auth_core.core import (
    MetadataEnricher,
    PangeaMetadataKeys,
    PangeaMetadataValues,
    PangeaGenericNodeProcessor,
    MetadataFilter,
    FilterOperator,
    T,
    _PANGEA_METADATA_KEY_PREFIX,
)


@dataclasses.dataclass
class JiraAuth:
    """Holds authentication details for Jira API."""

    email: str
    token: str
    url: str


class JiraME(MetadataEnricher):
    """Jira Metadata Enricher.

    Enriches metadata for documents using data fetched from Jira, like issue assignments and reporter details.

    Attributes:
        _url (str): URL for the Jira instance.
        _email (str): Email for authenticating with Jira.
        _api_token (str): API token for Jira access.
        _auth (JiraAuth): Authentication details for Jira.
    """

    _url: str
    _email: str
    _api_token: str
    _auth: JiraAuth

    def __init__(self, url: str, email: str, api_token: str):
        self._url = url
        self._email = email
        self._api_token = api_token
        self._auth = JiraAuth(email, api_token, url)

    def extract_metadata(self, doc: Any, file_content: str) -> dict[str, Any]:
        """Fetch Jira-related metadata for the document.

        Args:
            doc (Any): The document to enrich with metadata.
            file_content (str): The content of the file.

        Returns:
            dict[str, Any]: Extracted metadata including issue ID, assignee, and reporter details.
        """

        metadata: dict[str, Any] = {}

        # This step is to normalize some attributes across platforms
        metadata[PangeaMetadataKeys.DATA_SOURCE] = PangeaMetadataValues.DATA_SOURCE_JIRA
        metadata[PangeaMetadataKeys.FILE_NAME] = doc.metadata.get("title", "")

        id = doc.metadata.get("id", "")
        if not id:
            raise Exception("invalid metadata key")

        metadata[PangeaMetadataKeys.JIRA_ISSUE_ID] = id

        # New metadata
        issue = JiraAPI.get_issue(self._auth, id)
        metadata[f"{_PANGEA_METADATA_KEY_PREFIX}jira_assignee_account_id"] = (
            issue.get("fields", {}).get("assignee", {}).get("accountId", "")
        )
        metadata[f"{_PANGEA_METADATA_KEY_PREFIX}jira_assignee_name"] = (
            issue.get("fields", {}).get("assignee", {}).get("displayName", "")
        )
        metadata[f"{_PANGEA_METADATA_KEY_PREFIX}jira_reporter_account_id"] = (
            issue.get("fields", {}).get("reporter", {}).get("accountId", "")
        )
        metadata[f"{_PANGEA_METADATA_KEY_PREFIX}jira_reporter_name"] = (
            issue.get("fields", {}).get("reporter", {}).get("displayName", "")
        )

        return metadata


class JiraProcessor(PangeaGenericNodeProcessor, Generic[T]):
    """Processes Jira documents for access control.

    Filters Jira documents based on issue ID permissions and caches access results.

    Attributes:
        auth (JiraAuth): Jira authentication details.
        issue_ids_cache (dict[str, bool]): Cache of access status for Jira issue IDs.
        issue_ids_list (List[str]): List of authorized Jira issue IDs.
        get_node_metadata (Callable): Function to retrieve metadata for nodes.
    """

    auth: JiraAuth
    issue_ids_cache: dict[str, bool]
    issue_ids_list: List[str]
    get_node_metadata: Callable[[T], dict[str, Any]]

    def __init__(self, auth: JiraAuth, get_node_metadata: Callable[[T], dict[str, Any]]):
        super().__init__()
        self.auth = auth
        self.issue_ids_cache = {}
        self.get_node_metadata = get_node_metadata

    def filter(
        self,
        nodes: List[T],
    ) -> List[Any]:
        """Filter Jira nodes by access permissions.

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

        if not self.issue_ids_list:
            self.issue_ids_list = JiraAPI.get_issue_ids(self.auth)
        return MetadataFilter(
            key=PangeaMetadataKeys.JIRA_ISSUE_ID, value=self.issue_ids_list, operator=FilterOperator.IN
        )

    def _is_authorized(self, node: T) -> bool:
        metadata = self.get_node_metadata(node)
        return metadata[PangeaMetadataKeys.DATA_SOURCE] == PangeaMetadataValues.DATA_SOURCE_JIRA and self._has_access(
            metadata
        )

    def _has_access(self, metadata: dict[str, Any]) -> bool:
        id = metadata.get(PangeaMetadataKeys.JIRA_ISSUE_ID, None)
        if id is None:
            raise KeyError("Invalid metadata key")

        access = self.issue_ids_cache.get(id, None)
        if access is not None:
            return access

        try:
            JiraAPI.get_issue(self.auth, id)
            access = True
        except HTTPError as e:
            if e.response.status_code == 404:
                access = False

        if access is None:
            return False

        self.issue_ids_cache[id] = access
        return access


class JiraAPI:
    @staticmethod
    def _request(auth: JiraAuth, path: str, params: dict = {}) -> dict:
        """
        Makes a request to the Jira API.

        Args:
            auth (JiraAuth): The authentication credentials for Jira.
            path (str): The API path to send the request to.
            params (dict, optional): The query parameters for the request.

        Returns:
            dict: The JSON response from the Jira API.
        """

        basic_auth = HTTPBasicAuth(auth.email, auth.token)
        url = f"https://{auth.url}{path}"
        response = requests.get(url, headers={"Accept": "application/json"}, params=params, auth=basic_auth)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def get_issue(auth: JiraAuth, issue_id: str) -> dict:
        """
        Retrieves details of a specific Jira issue.

        Args:
            auth (JiraAuth): The authentication credentials for Jira.
            issue_id (str): The ID of the Jira issue to retrieve.

        Returns:
            dict: The JSON response containing issue details.
        """

        return JiraAPI._request(auth, f"/rest/api/3/issue/{issue_id}")

    @staticmethod
    def myself(auth: JiraAuth) -> dict:
        """
        Retrieves the profile information of the currently authenticated user in Jira.

        Args:
            auth (JiraAuth): The authentication credentials for Jira.

        Returns:
            dict: A dictionary containing the authenticated user's profile information.

        Raises:
            HTTPError: If the request to Jira fails.
        """
        return JiraAPI._request(auth, "/rest/api/3/myself")

    @staticmethod
    def search(auth: JiraAuth, params: dict = {}) -> dict:
        """
        Searches for issues in Jira using specified query parameters.

        This method provides a way to search for issues in Jira, returning a paginated list
        of issues based on search criteria defined in the `params` argument. The parameters
        can be customized to filter issues based on various criteria such as project, status,
        labels, etc.

        Args:
            auth (JiraAuth): The authentication credentials for Jira.
            params (dict, optional): A dictionary of query parameters for customizing the search.
                                     Default is an empty dictionary.

        Returns:
            dict: A dictionary containing the search results, including issue details and pagination info.

        Raises:
            HTTPError: If the request to Jira fails.
        """
        return JiraAPI._request(auth, "/rest/api/3/search", params)

    @staticmethod
    def get_issue_ids(auth: JiraAuth) -> List[str]:
        """
        Retrieves the IDs of all issues in Jira.

        This method iterates through all issues in the Jira instance and retrieves their IDs.
        It paginates through results if there are more issues than the `max_results` limit.

        Args:
            auth (JiraAuth): The authentication credentials for Jira.

        Returns:
            List[str]: A list of all issue IDs in the Jira instance.
        """

        max_results = 50
        start_at = 0
        keep_iterating = True
        issue_ids: List[str] = []

        while keep_iterating:
            params = {
                "query": "",
                "maxResults": max_results,
                "startAt": start_at,
                "fields": ["id"],
            }

            resp = JiraAPI.search(auth, params)
            issues = resp.get("issues", [])
            total = resp.get("total", 0)

            ids = [issue["id"] for issue in issues]
            issue_ids.extend(ids)  # type: ignore

            start_at = start_at + len(ids)
            keep_iterating = start_at < total

        return issue_ids
