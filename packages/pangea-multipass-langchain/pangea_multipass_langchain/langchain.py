# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

from typing import Any, List, Optional

from google.oauth2.credentials import Credentials
from langchain_core.documents import Document
from pangea_multipass import (
    ConfluenceAuth,
    ConfluenceProcessor,
    DocumentReader,
    DropboxProcessor,
    FilterOperator,
    GDriveProcessor,
    GitHubProcessor,
    GitLabProcessor,
    JiraAuth,
    JiraProcessor,
)
from pangea_multipass import MetadataFilter as PangeaMetadataFilter
from pangea_multipass import MultipassDocument, PangeaGenericNodeProcessor, PangeaNodeProcessorMixer, SlackProcessor


class LangChainDocumentReader(DocumentReader):
    """Lang chain document reader"""

    def read(self, doc: Document) -> str:
        return str(doc.page_content)


def get_doc_id(doc: Document) -> str:
    return doc.id if doc.id is not None else ""


def get_doc_metadata(doc: Document) -> dict[str, Any]:
    return dict(doc.metadata)


def from_multipass(documents: List[MultipassDocument]) -> List[Document]:
    lc_documents: List[Document] = []
    for doc in documents:
        lc_doc = Document(id=doc.id, page_content=doc.content)
        lc_doc.metadata = doc.metadata
        lc_documents.append(lc_doc)

    return lc_documents


class LangChainJiraFilter(JiraProcessor[Document]):
    """Filter for Jira integration with LangChain documents.

    Uses Jira authentication to check document access in the LangChain.

    Args:
        auth (JiraAuth): Jira authentication credentials.
        account_id (Optional[str]): Jira user's account id to check issues permissions.
    """

    def __init__(self, auth: JiraAuth, account_id: Optional[str] = None):
        super().__init__(auth, get_node_metadata=get_doc_metadata, account_id=account_id)


class LangChainConfluenceFilter(ConfluenceProcessor[Document]):
    """Filter for Confluence integration with LangChain documents.

    Uses Confluence authentication to check document access in the LangChain.

    Args:
        auth (ConfluenceAuth): Confluence authentication credentials.
        space_id (Optional[int]): The space ID to filter pages by.
        account_id (Optional[str]): User account id to check permissions using admin token.

    """

    def __init__(self, auth: ConfluenceAuth, space_id: Optional[int] = None, account_id: Optional[str] = None):
        super().__init__(auth, get_node_metadata=get_doc_metadata, space_id=space_id, account_id=account_id)


class LangChainGDriveFilter(GDriveProcessor[Document]):
    """Filter for Google Drive integration with LangChain documents.

    Uses Google Drive credentials to check document access in the LangChain.

    Args:
        creds (Credentials): Google OAuth2 credentials.
        user_email (Optional[str]): User email to check access to files.
    """

    def __init__(self, creds: Credentials, user_email: Optional[str] = None):
        super().__init__(creds, get_node_metadata=get_doc_metadata, user_email=user_email)


class LangChainGitHubFilter(GitHubProcessor[Document]):
    """Filter for GitHub integration with LangChain documents.

    Uses GitHub classic token to check document access in the LangChain.

    Args:
        token (str): GitHub classic token.
        username (Optional[str]): GitHub username to check permissions.
    """

    def __init__(self, token: str, username: Optional[str] = None):
        super().__init__(token, get_node_metadata=get_doc_metadata, username=username)


class LangChainSlackFilter(SlackProcessor[Document]):
    """Filter for Slack integration with LangChain documents.

    Uses Slack token to check access to channels in the LangChain.

    Args:
        token (str): Slack token.
        user_email (Optional[str]): User email to check access to channels.
    """

    def __init__(self, token: str, user_email: Optional[str] = None):
        super().__init__(token, get_node_metadata=get_doc_metadata, user_email=user_email)


class LangChainGitLabFilter(GitLabProcessor[Document]):
    """Filter for GitLab integration with LangChain documents.

    Uses GitLab token to access nodes in the LangChain.

    Args:
        token (str): GitLab token.
        username (str): Username to check access to files.
    """

    def __init__(self, admin_token: str, username: str):
        super().__init__(admin_token=admin_token, username=username, get_node_metadata=get_doc_metadata)


class LangChainDropboxFilter(DropboxProcessor[Document]):
    """Filter for Dropbox integration with LangChain documents.

    Uses Dropbox token to check access to documents in the LangChain.

    Args:
        token (str): Dropbox token.
        user_email (str): User email to check access to files.
    """

    def __init__(self, token: str, user_email: str):
        super().__init__(token, get_node_metadata=get_doc_metadata, user_email=user_email)


class DocumentFilterMixer:
    node_processor: PangeaNodeProcessorMixer[Document] = PangeaNodeProcessorMixer(get_doc_metadata, [])

    def __init__(self, document_filters: List[PangeaGenericNodeProcessor[Document]]):
        super().__init__()
        self.node_processor = PangeaNodeProcessorMixer[Document](
            get_node_metadata=get_doc_metadata,
            node_processors=document_filters,
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
