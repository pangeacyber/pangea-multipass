# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

from abc import ABC, abstractmethod
from typing import Any, Sequence, List, Callable, Generic, TypeVar
import hashlib
import enum
import dataclasses

T = TypeVar("T")
_PANGEA_METADATA_KEY_PREFIX = "_pangea_"


class FilterOperator(str, enum.Enum):
    """Defines operators for filtering metadata."""

    IN = "in"  # In array (string or number)
    CONTAINS = "contains"  # metadata array contains value (string or number)
    EQ = "=="  # default operator (string, int, float)
    GT = ">"  # greater than (int, float)
    LT = "<"  # less than (int, float)
    NE = "!="  # not equal to (string, int, float)
    GTE = ">="  # greater than or equal to (int, float)
    LTE = "<="  # less than or equal to (int, float)
    NIN = "nin"  # Not in array (string or number)
    ANY = "any"  # Contains any (array of strings)
    ALL = "all"  # Contains all (array of strings)
    TEXT_MATCH = "text_match"  # full text match (allows you to search for a specific substring, token or phrase within the text field)
    IS_EMPTY = "is_empty"  # the field is not exist or empty (null or empty array)


class PangeaMetadataKeys(str, enum.Enum):
    DATA_SOURCE = f"{_PANGEA_METADATA_KEY_PREFIX}data_source"
    FILE_NAME = f"{_PANGEA_METADATA_KEY_PREFIX}file_name"
    CONFLUENCE_PAGE_ID = f"{_PANGEA_METADATA_KEY_PREFIX}confluence_page_id"
    JIRA_ISSUE_ID = f"{_PANGEA_METADATA_KEY_PREFIX}jira_issue_id"
    GDRIVE_FILE_ID = f"{_PANGEA_METADATA_KEY_PREFIX}gdrive_file_id"


class PangeaMetadataValues(str, enum.Enum):
    DATA_SOURCE_CONFLUENCE = "confluence"
    DATA_SOURCE_GDRIVE = "gdrive"
    DATA_SOURCE_JIRA = "jira"


@dataclasses.dataclass
class MetadataFilter:
    """Represents a filter for document metadata."""

    key: str
    value: Any
    operator: FilterOperator


class DocumentReader(ABC):
    """Interface for reading documents."""

    @abstractmethod
    def read(self, doc: Any) -> str:
        """Reads and returns content of the document as a string."""
        pass


class PangeaGenericNodeProcessor(ABC, Generic[T]):
    """Abstract processor for handling nodes with filtering and processing methods."""

    @abstractmethod
    def filter(self, nodes: List[T]) -> List[T]:
        """Processes nodes and applies filtering."""
        pass

    @abstractmethod
    def get_filter(self) -> MetadataFilter:
        """Returns a filter based on the processed nodes' metadata."""
        pass


class MetadataEnricher(ABC):
    """Interface for generating additional metadata for documents."""

    _key: str
    """Key used in the metadata dictionary for the enrichment. """

    def __init__(self, key: str):
        if not key.startswith(_PANGEA_METADATA_KEY_PREFIX):
            key = f"{_PANGEA_METADATA_KEY_PREFIX}{key}"

        self._key = key

    @abstractmethod
    def extract_metadata(self, doc: Any, file_content: str) -> dict[str, Any]:
        """Generates metadata based on document and its content."""
        pass


class MetadataUpdater(ABC):
    """Interface for updating document metadata."""

    @abstractmethod
    def update_metadata(self, doc: Any, metadata: dict[str, Any]):
        """Updates document with provided metadata."""
        pass


class GenericMetadataUpdater(MetadataUpdater):
    """Updates metadata of a Llama Index or Lang Chain Document."""

    def update_metadata(self, doc: Any, metadata: dict[str, Any]):
        """Updates document metadata with given key-value pairs."""
        doc.metadata.update(metadata)


class HasherSHA256(MetadataEnricher):
    """Generates SHA-256 hash for the document and adds it to metadata."""

    def extract_metadata(self, doc: Any, file_content: str) -> dict[str, Any]:
        """Returns SHA-256 hash of the document content."""
        return {self._key: hashlib.sha256(file_content.encode()).hexdigest()}


class Constant(MetadataEnricher):
    """Sets a constant value as metadata for the document."""

    value: str

    def __init__(self, key: str, value: str):
        super().__init__(f"{key}")
        self.value = value

    def extract_metadata(self, doc: Any, file_content: str) -> dict[str, Any]:
        """Sets a constant value in the metadata."""
        return {self._key: self.value}


def enrich_metadata(
    documents: Sequence[Any],
    metadata_enrichers: List[MetadataEnricher],
    reader: DocumentReader,
    updater: MetadataUpdater = GenericMetadataUpdater(),
):
    """Enriches metadata of documents by applying specified enrichers.

    Args:
        documents: A sequence of documents to enrich.
        metadata_enrichers: List of metadata enrichers to apply.
        reader: A reader instance to obtain document content.
        updater: Optional updater instance to apply metadata changes.
    """

    for doc in documents:
        file_content = reader.read(doc)
        for enricher in metadata_enrichers:
            updater.update_metadata(doc, enricher.extract_metadata(doc, file_content))

        reader.read(doc)


class PangeaNodeProcessorMixer(Generic[T]):
    """Combines multiple node processors for authorization filtering.

    Aggregates results from various node processors to create a unified view of authorized and unauthorized nodes.

    Attributes:
        _node_processors (List[PangeaGenericNodeProcessor]): List of node processors.
        _get_node_metadata (Callable): Function to get node metadata.
        _get_node_id (Callable): Function to retrieve node ID.
        _unauthorized_nodes (List[T]): Cached list of unauthorized nodes.
        _authorized_nodes (List[T]): Cached list of authorized nodes.
    """

    _node_processors: List[PangeaGenericNodeProcessor] = []
    _get_node_metadata: Callable[[T], dict[str, Any]]
    _get_node_id: Callable[[T], str]
    _unauthorized_nodes: List[T] = []
    _authorized_nodes: List[T] = []

    def __init__(
        self,
        get_node_metadata: Callable[[T], dict[str, Any]],
        get_node_id: Callable[[T], str],
        node_processors: List[PangeaGenericNodeProcessor],
    ):
        self._node_processors = node_processors
        self._get_node_id = get_node_id
        self._get_node_metadata = get_node_metadata

    def filter(
        self,
        nodes: List[T],
    ) -> List[T]:
        """Process nodes through each processor to filter authorized nodes.

        Args:
            nodes (List[T]): List of nodes to process.

        Returns:
            List[T]: Nodes that have been authorized across all processors.
        """

        authorized: dict[str, T] = {}
        unauthorized: dict[str, T] = {}
        for node in nodes:
            unauthorized[self._get_node_id(node)] = node

        # This works as an OR operator among all node post processors
        for npp in self._node_processors:
            for node in npp.filter(list(unauthorized.values())):
                id = self._get_node_id(node)
                authorized[id] = unauthorized.pop(id)

        self._unauthorized_nodes = list(unauthorized.values())
        self._authorized_nodes = list(authorized.values())
        return self._authorized_nodes

    def get_filters(self) -> List[MetadataFilter]:
        """Retrieve filters from all node processors.

        Returns:
            List[MetadataFilter]: List of filters from each processor.
        """

        filters = []
        for np in self._node_processors:
            filters.append(np.get_filter())

        return filters

    def get_unauthorized_nodes(
        self,
    ) -> List[T]:
        """Retrieve nodes that were unauthorized after processing.

        Returns:
            List[T]: Unauthorized nodes.
        """

        return self._unauthorized_nodes

    def get_authorized_nodes(
        self,
    ) -> List[T]:
        """Retrieve nodes that were authorized after processing.

        Returns:
            List[T]: Authorized nodes.
        """

        return self._authorized_nodes
