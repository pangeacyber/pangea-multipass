# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

from typing import Any, List, Optional

from google.oauth2.credentials import Credentials
from llama_index.core import Document as LIDocument
from llama_index.core.bridge.pydantic import Field
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.core.vector_stores import (FilterCondition, FilterOperator,
                                            MetadataFilter, MetadataFilters)
from pangea_multipass import (ConfluenceAuth, ConfluenceProcessor,
                              DocumentReader, GDriveProcessor, JiraAuth,
                              JiraProcessor)
from pangea_multipass import MetadataFilter as PangeaMetadataFilter
from pangea_multipass import (PangeaGenericNodeProcessor,
                              PangeaNodeProcessorMixer)


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
        return doc.get_content()


# pangea-metadata-llama-index
def get_doc_id(doc: LIDocument) -> str:
    """Fetches the document ID from a Llama Index document.

    Args:
        doc (LIDocument): The Llama Index document.

    Returns:
        str: The document ID.
    """
    return doc.doc_id


def get_node_metadata(node: NodeWithScore) -> dict[str, Any]:
    """Fetches metadata from a node with a score.

    Args:
        node (NodeWithScore): The node from which metadata is retrieved.

    Returns:
        dict[str, Any]: A dictionary containing node metadata.
    """
    return node.metadata


class LlamaIndexJiraProcessor(JiraProcessor[NodeWithScore]):
    """Processor for Jira integration with Llama Index nodes.

    Uses Jira authentication to access nodes in the Llama Index.

    Args:
        auth (JiraAuth): Jira authentication credentials.
    """

    def __init__(self, auth: JiraAuth):
        super().__init__(auth, get_node_metadata=get_node_metadata)


class LlamaIndexConfluenceProcessor(ConfluenceProcessor[NodeWithScore]):
    """Processor for Confluence integration with Llama Index nodes.

    Uses Confluence authentication to access nodes in the Llama Index.

    Args:
        auth (ConfluenceAuth): Confluence authentication credentials.
    """

    def __init__(self, auth: ConfluenceAuth):
        super().__init__(auth, get_node_metadata=get_node_metadata)


class LlamaIndexGDriveProcessor(GDriveProcessor[NodeWithScore]):
    """Processor for Google Drive integration with Llama Index nodes.

    Uses Google Drive credentials to access nodes in the Llama Index.

    Args:
        creds (Credentials): Google OAuth2 credentials.
    """

    def __init__(self, creds: Credentials):
        super().__init__(creds, get_node_metadata=get_node_metadata)


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

    node_processor: PangeaNodeProcessorMixer[NodeWithScore] = Field(default=None)

    def __init__(self, node_processors: List[PangeaGenericNodeProcessor]):
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
            query_bundle (Optional[QueryBundle], optional): Query context for processing. Defaults to None.

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
