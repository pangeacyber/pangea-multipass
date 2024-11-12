# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

from langchain_core.documents import Document
from typing import Any, List
from google.oauth2.credentials import Credentials
from pangea_auth_core import (
    JiraAuth,
    JiraProcessor,
    ConfluenceAuth,
    ConfluenceProcessor,
    GDriveProcessor,
    PangeaNodeProcessorMixer,
    FilterOperator,
    DocumentReader,
    PangeaGenericNodeProcessor,
)
from pangea_auth_core import MetadataFilter as PangeaMetadataFilter


class LangChainDocumentReader(DocumentReader):
    """Lang chain document reader"""

    def read(self, doc: Document) -> str:
        return doc.page_content


def get_doc_id(doc: Document) -> str:
    return doc.id if doc.id is not None else ""


def get_doc_metadata(doc: Document) -> dict[str, Any]:
    return doc.metadata


class LangChainJiraFilter(JiraProcessor[Document]):
    """Filter for Jira integration with LangChain documents.

    Uses Jira authentication to access documents in the LangChain.

    Args:
        auth (JiraAuth): Jira authentication credentials.
    """

    def __init__(self, auth: JiraAuth):
        super().__init__(auth, get_node_metadata=get_doc_metadata)


class LangChainConfluenceFilter(ConfluenceProcessor[Document]):
    """Filter for Confluence integration with LangChain documents.

    Uses Confluence authentication to access documents in the LangChain.

    Args:
        auth (ConfluenceAuth): Confluence authentication credentials.
    """

    def __init__(self, auth: ConfluenceAuth):
        super().__init__(auth, get_node_metadata=get_doc_metadata)


class LangChainGDriveFilter(GDriveProcessor[Document]):
    """Filter for Google Drive integration with LangChain documents.

    Uses Google Drive credentials to access documents in the LangChain.

    Args:
        creds (Credentials): Google OAuth2 credentials.
    """

    def __init__(self, creds: Credentials):
        super().__init__(creds, get_node_metadata=get_doc_metadata)


class DocumentFilterMixer:
    node_processor: PangeaNodeProcessorMixer[Document]

    def __init__(self, node_processors: List[PangeaGenericNodeProcessor]):
        super().__init__()
        self.node_processor = PangeaNodeProcessorMixer[Document](
            get_node_metadata=get_doc_metadata,
            get_node_id=get_doc_id,
            node_processors=node_processors,
        )

    def filter(
        self,
        documents: List[Document],
    ) -> List[Document]:
        return self.node_processor.filter(documents)

    def get_filter(
        self,
    ) -> dict[str, Any]:
        filters = []
        for filter in self.node_processor.get_filters():
            filters.append(_convert_metadata_filter_to_langchain(filter))
        return {"$or": filters}

    def get_unauthorized_documents(
        self,
    ) -> List[Document]:
        """Retrieves documents that are unauthorized for access.

        Returns:
            List[Document]: List of unauthorized documents.
        """
        return self.node_processor.get_unauthorized_nodes()

    def get_authorized_documents(
        self,
    ) -> List[Document]:
        """Retrieves documents that are authorized for access.

        Returns:
            List[Document]: List of authorized documents.
        """
        return self.node_processor.get_authorized_nodes()


def _convert_metadata_filter_to_langchain(input: PangeaMetadataFilter) -> dict[str, Any]:
    if input.operator == FilterOperator.EQ:
        filter = {input.key: input.value}
    elif input.operator == FilterOperator.IN:
        filter = {input.key: {"$in": input.value}}
    elif input.operator == FilterOperator.CONTAINS:
        filter = {input.key: {"$contain": input.value}}
    elif input.operator == FilterOperator.GT:
        filter = {input.key: {"$gt": input.value}}
    elif input.operator == FilterOperator.LT:
        filter = {input.key: {"$lt": input.value}}
    elif input.operator == FilterOperator.NE:
        filter = {input.key: {"$ne": input.value}}
    elif input.operator == FilterOperator.GTE:
        filter = {input.key: {"$gte": input.value}}
    elif input.operator == FilterOperator.LTE:
        filter = {input.key: {"$lte": input.value}}
    elif input.operator == FilterOperator.NIN:
        filter = {input.key: {"$nin": input.value}}
    else:
        raise TypeError(f"Invalid filter operator: {input.operator}")

    return filter
