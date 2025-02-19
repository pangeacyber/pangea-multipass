# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

from typing import Any, List, Optional

from google.oauth2.credentials import Credentials
from llama_index.core import Document as LIDocument
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.core.vector_stores import FilterCondition, FilterOperator, MetadataFilter, MetadataFilters
from pangea_multipass import (
    ConfluenceAuth,
    ConfluenceProcessor,
    DocumentReader,
    DropboxProcessor,
    GDriveProcessor,
    GitHubProcessor,
    GitLabProcessor,
    JiraAuth,
    JiraProcessor,
)
from pangea_multipass import MetadataFilter as PangeaMetadataFilter
from pangea_multipass import MultipassDocument, PangeaGenericNodeProcessor, PangeaNodeProcessorMixer, SlackProcessor


class LIDocumentReader(DocumentReader):
    """Document reader for Llama Index documents.

    Provides methods for reading content from a Llama Index document.

    Methods:
        read(doc: LIDocument) -> str: Reads and returns the content of a Llama Index document.
    """

    def read(self, doc: LIDocument) -> str:
        """Reads and returns the content of the given Llama Index document.

        Args:
            doc (LIDocument): The Llama Index document to read.

        Returns:
            str: The content of the document.
        """
        return str(doc.get_content())


# pangea-metadata-llama-index
def get_doc_id(doc: LIDocument) -> str:
    """Fetches the document ID from a Llama Index document.

    Args:
        doc (LIDocument): The Llama Index document.

    Returns:
        str: The document ID.
    """
    return str(doc.doc_id)


def get_node_metadata(node: NodeWithScore) -> dict[str, Any]:
    """Fetches metadata from a node with a score.

    Args:
        node (NodeWithScore): The node from which metadata is retrieved.

    Returns:
        dict[str, Any]: A dictionary containing node metadata.
    """
    return dict(node.metadata)


def from_multipass(documents: List[MultipassDocument]) -> List[LIDocument]:
    li_documents: List[LIDocument] = []
    for doc in documents:
        li_doc = LIDocument(doc_id=doc.id, text=doc.content)
        li_doc.metadata = doc.metadata
        li_documents.append(li_doc)

    return li_documents


class LlamaIndexJiraProcessor(JiraProcessor[NodeWithScore]):
    """Processor for Jira integration with Llama Index nodes.

    Uses Jira authentication to access nodes.

    Args:
        auth (JiraAuth): Jira authentication credentials.
        account_id (Optional[str]): Jira user's account id to check issues permissions.
    """

    def __init__(self, auth: JiraAuth, account_id: Optional[str] = None):
        super().__init__(auth, get_node_metadata=get_node_metadata, account_id=account_id)


class LlamaIndexConfluenceProcessor(ConfluenceProcessor[NodeWithScore]):
    """Processor for Confluence integration with Llama Index nodes.

    Uses Confluence authentication to check nodes access.

    Args:
        auth (ConfluenceAuth): Confluence authentication credentials.
        space_id (Optional[int]): The space ID to filter pages by.
        account_id (Optional[str]): User account id to check permissions using admin token.

    """

    def __init__(self, auth: ConfluenceAuth, space_id: Optional[int] = None, account_id: Optional[str] = None):
        super().__init__(auth, get_node_metadata=get_node_metadata, space_id=space_id, account_id=account_id)


class LlamaIndexGDriveProcessor(GDriveProcessor[NodeWithScore]):
    """Processor for Google Drive integration with Llama Index nodes.

    Uses Google Drive credentials to check nodes access.

    Args:
        creds (Credentials): Google OAuth2 credentials.
        user_email (Optional[str]): User email to check access to files.
    """

    def __init__(self, creds: Credentials, user_email: Optional[str] = None):
        super().__init__(creds, get_node_metadata=get_node_metadata, user_email=user_email)


class LlamaIndexGitHubProcessor(GitHubProcessor[NodeWithScore]):
    """Processor for GitHub integration with Llama Index nodes.

    Uses GitHub token to check node access.

    Args:
        token (str): GitHub classic token.
        username (Optional[str]): GitHub username to check permissions.
    """

    def __init__(self, token: str, username: Optional[str] = None):
        super().__init__(token, get_node_metadata=get_node_metadata, username=username)


class LlamaIndexSlackProcessor(SlackProcessor[NodeWithScore]):
    """Processor for Slack integration with Llama Index nodes.

    Uses Slack token to check node access.

    Args:
        token (str): Slack token.
        user_email (Optional[str]): User email to check access to files.
    """

    def __init__(self, token: str, user_email: Optional[str] = None):
        super().__init__(token, get_node_metadata=get_node_metadata, user_email=user_email)


class LlamaIndexGitLabProcessor(GitLabProcessor[NodeWithScore]):
    """Processor for GitLab integration with Llama Index nodes.

    Uses GitLab token to access nodes in the Llama Index.

    Args:
        token (str): GitLab token.
        username (str): Username to check access to files.
    """

    def __init__(self, admin_token: str, username: str):
        super().__init__(admin_token=admin_token, username=username, get_node_metadata=get_node_metadata)


class LlamaIndexDropboxProcessor(DropboxProcessor[NodeWithScore]):
    """Processor for Dropbox integration with Llama Index nodes.

    Uses Dropbox token to check node access.

    Args:
        token (str): Dropbox token.
        user_email (str): User email to check access to files.
    """

    def __init__(self, token: str, user_email: str):
        super().__init__(token, get_node_metadata=get_node_metadata, user_email=user_email)


class NodePostprocessorMixer(BaseNodePostprocessor):
    """Postprocessor mixer for processing nodes with multiple processors.

    This class mixes multiple node processors and applies them to Llama Index nodes.

    Attributes:
        node_processor (PangeaNodeProcessorMixer[NodeWithScore]): A mixer of node processors.

    Methods:
        _postprocess_nodes(nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None) -> List[NodeWithScore]:
            Postprocesses a list of nodes with the mixed processors.
        get_filter() -> MetadataFilters: Gets the metadata filters used for processing nodes.
        get_unauthorized_nodes() -> List[NodeWithScore]: Retrieves nodes that are unauthorized for access.
        get_authorized_nodes() -> List[NodeWithScore]: Retrieves nodes that are authorized for access.
    """

    node_processor: PangeaNodeProcessorMixer[NodeWithScore] = PangeaNodeProcessorMixer(get_node_metadata, [])

    def __init__(self, node_processors: List[PangeaGenericNodeProcessor[NodeWithScore]]):
        """Initializes the NodePostprocessorMixer with a list of node processors.

        Args:
            node_processors (List[PangeaGenericNodeProcessor]): List of node processors to mix and apply.
        """

        super().__init__()
        self.node_processor = PangeaNodeProcessorMixer[NodeWithScore](
            get_node_metadata=get_node_metadata,
            node_processors=node_processors,
        )

    def _postprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        """Applies postprocessing to a list of nodes using the mixed node processors.

        Args:
            nodes (List[NodeWithScore]): The nodes to be postprocessed.
            query_bundle (Optional[QueryBundle]): Query context for processing. Defaults to None.

        Returns:
            List[NodeWithScore]: The list of postprocessed nodes.
        """

        return self.node_processor.filter(nodes)

    def get_filter(
        self,
    ) -> MetadataFilters:
        """Generates metadata filters for processing nodes.

        Returns:
            MetadataFilters: A set of metadata filters with an OR condition applied.
        """

        filters: List[MetadataFilter | MetadataFilters] = []
        for filter in self.node_processor.get_filters():
            filters.append(_convert_metadata_filter_to_llama_index(filter))

        return MetadataFilters(filters=filters, condition=FilterCondition.OR)

    def get_unauthorized_nodes(
        self,
    ) -> List[NodeWithScore]:
        """Retrieves nodes that are unauthorized for access.

        Returns:
            List[NodeWithScore]: List of unauthorized nodes.
        """
        return self.node_processor.get_unauthorized_nodes()

    def get_authorized_nodes(
        self,
    ) -> List[NodeWithScore]:
        """Retrieves nodes that are authorized for access.

        Returns:
            List[NodeWithScore]: List of authorized nodes.
        """
        return self.node_processor.get_authorized_nodes()


def _convert_metadata_filter_to_llama_index(input: PangeaMetadataFilter) -> MetadataFilter:
    """Converts a Pangea metadata filter to a Llama Index-compatible filter.

    Args:
        input (PangeaMetadataFilter): The Pangea metadata filter to convert.

    Returns:
        MetadataFilter: The converted Llama Index metadata filter.
    """
    return MetadataFilter(key=input.key, value=input.value, operator=FilterOperator(input.operator))
