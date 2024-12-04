# Pangea Auth Core

Pangea Auth Core is a Python library for enriching metadata of documents from Google Drive, JIRA, and Confluence. This library is designed with a flexible architecture, particularly useful for Retrieval-Augmented Generation (RAG) applications and can function in a framework-less environment.

## Features

- **Document Reading**: Supports document content extraction for use in processing and enrichment.
- **Metadata Enrichment**: Includes enrichers for hashing, constant value setting, and custom metadata.
- **Metadata Filtering**: Provides flexible operators to filter document metadata for customized queries.
- **Authorization Processing**: Manages authorized and unauthorized nodes with customizable node processors.
- **Extensible**: Built on abstract base classes, allowing easy extension and customization of functionality.

## Installation

To install `pangea-auth-core`, you can use [Poetry](https://python-poetry.org/) for dependency management:

```bash
poetry add pangea-auth-core
```

Alternatively, if installing directly from the source:
- Clone the repository and run the following commands:

```bash
cd pangea-auth-core
poetry install
```

## Usage
### Core Components

- Metadata Enrichment: Use classes like HasherSHA256 and Constant to add enriched metadata to documents. 
- Metadata Enrichers are applied through `enrich_metadata` method to all the documents.
- DocumentReader: Implement custom readers for extracting document content.
- MetadataUpdater: Apply enriched metadata to documents.
- Filter Operators: Use FilterOperator for applying various metadata filters (e.g., EQ, GT, CONTAINS, etc.).


## Extend file sources

In order to extend the file sources provided by this package, here it's explain how new classes should be implemented. In this case GDrive source is used as an example and documented in detail.
New sources implementation should have, at least, 2 parts:
- Metadata Enricher: Used on ingestion time to add metadata to the documents.
- Processors/Filters: Used on inference time to process enriched medatada and filter documents based on logged user. 

### Metadata Enricher

CustomSource metadata enricher implementation should inherite from `MetadataEnricher` class.

```python
class GDriveME(MetadataEnricher):
```

This inheration will require that `extract_metadata` method is implemented with this next signature:

```
extract_metadata(self, doc: Any, file_content: str) -> dict[str, Any]:
```

This method will receive the document itself, so it's possible to access to the document metadata and another attributes if needed, and it will also receive document content, so it's possible so process it for whatever it's needed (hash it, process by another llm in order to get further information about it, etc.)

```python
    def extract_metadata(self, doc: Any, file_content: str) -> dict[str, Any]:
        metadata: dict[str, Any] = {}

        # This step is to normalize some attributes across platforms
        # Optional: If CustomSource has an attribute that it's related to the file name, title, etc. It would be nice to copy it to 
        # PangeaMetadataKeys.FILE_NAME in order to unify this key/value.
        metadata[PangeaMetadataKeys.FILE_NAME] = doc.metadata.get("file name", "")

        # Required: Metadata enricher should set data source key as follow
        metadata[PangeaMetadataKeys.DATA_SOURCE] = PangeaMetadataValues.DATA_SOURCE_GDRIVE

        # Required: at least for this use case, it's required that this metadata enricher set the file id, so it will be used
        # in inference time to request the permissions of this file.
        # In this case there is a function to get the id from the metadata due to each source Langchain/LlamaIndex use different
        # key names to save it into the metadata.
        id = self._get_id_from_metadata(doc.metadata)
        if not id:
            raise Exception("empty doc_id")
        metadata[PangeaMetadataKeys.GDRIVE_FILE_ID] = id

        # New metadata is returned so it will be used by `enrich_metadata` method implemented in core package
        return metadata
```

NOTE: In this case GDrive metadata enricher have to be initialized with admin credentials to access the data source, so it is able to request all the files and their metadata.

### Processor/Filter

CustomProcessor should inherit from `PangeaGenericNodeProcessor` and `Generic[T]`. 

```python
class GDriveProcessor(PangeaGenericNodeProcessor, Generic[T]):
```

`PangeaGenericNodeProcessor` will require that `filter` and `get_filter` methods are implemented.

`filter()` method will take care of filter available node in run time. In order to do this, this `Processor` should be initialized with user credentials, so it's able to check what files this user has access to. 

```python
    def filter(
        self,
        nodes: List[T],
    ) -> List[T]:

        filtered: List[T] = []
        for node in nodes:
            if self._is_authorized(node):
                filtered.append(node)
        return filtered
```

`get_filter()` method will return a `MetadataFilter` to be used in LlamaIndex or Langchain retriever filters. In this case it request all the permission of all the files, so it's not performing for really long dataset. It's recommended to use `filter` so only are requested those files of interest to the current prompt.

```python
    def get_filter(
        self,
    ):

        if not self.files_ids:
            self.files_ids = GDriveAPI.list_all_file_ids(self.creds)

        return MetadataFilter(key=PangeaMetadataKeys.GDRIVE_FILE_ID, value=self.files_ids, operator=FilterOperator.IN)
```

### API 

This third class is used just to group all the API request related to this particular data source. It's not required but it's a nice way to group all these required methods used internally for the above descrived classes. 

```python
class GDriveAPI:
    _SCOPES = [
        ...
    ]

    _user_token_filepath: str = "gdrive_access_token.json"

    @staticmethod
    def get_and_save_access_token(credentials_filepath, token_filepath, scopes):
        pass

    @staticmethod
    def get_user_info(creds: Credentials):
        pass

    @staticmethod
    def get_user_credentials(
        credentials_filepath: str, user_token_filepath: str = _user_token_filepath, scopes=_SCOPES
    ):
        pass

    @staticmethod
    def check_file_access(creds: Credentials, file_id: str) -> bool:
        pass

    @staticmethod
    def list_all_file_ids(creds: Credentials) -> List[str]:
        pass
```


## Roadmap

At release, this library supports Google Workspace, Confluence, and Jira. For adding systems, our top priorities are:

- Slack
- Github
- Salesforce
- Box

Other we plan to support or are looking for contributions are:

- Office 365
- Zoom
- Dropbox
- Gitlab
- Zendesk
- Notion
- Sharepoint
- Asana
- Hubspot
