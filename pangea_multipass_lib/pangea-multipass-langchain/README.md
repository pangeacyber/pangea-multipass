# Pangea Multipass for LangChain

The `pangea-multipass-langchain` package extends Pangea Multipass to integrate with LangChain's document processing, providing enhanced security, metadata filtering, and access control for LangChain documents. This package supports integrations with Google Drive, JIRA, and Confluence, leveraging metadata-based filtering and authorization to control document access.

## Features

- **Document Reader**: Custom `LangChainDocumentReader` class reads content from LangChain documents, adapting to Pangea's document model.
- **Integration Processors**:
  - `LangChainJiraFilter`: Allows JIRA integration, authenticating and processing JIRA documents in LangChain.
  - `LangChainConfluenceFilter`: Provides Confluence integration for document access control in LangChain.
  - `LangChainGDriveFilter`: Uses Google OAuth credentials to access and filter Google Drive documents in LangChain.
- **Document Filter Mixer**: The `DocumentFilterMixer` aggregates multiple processors, applying customized filters for advanced access control across various sources.

## Installation

Use [Poetry](https://python-poetry.org/) to install dependencies:

```bash
poetry add pangea-multipass-langchain
```

## Usage 
### Core Components

- LangChainDocumentReader: The LangChainDocumentReader class enables reading content from LangChain documents for authorization and metadata filtering. This class acts as a bridge between LangChain documents and Pangea's authorization model.
- Processors for LangChain Integration: The package includes processors that integrate with specific data sources using authentication credentials. Each processor retrieves metadata from documents, allowing fine-grained control over document access:
    - LangChainJiraFilter: Authenticates with JIRA and processes JIRA documents.
    - LangChainConfluenceFilter: Processes Confluence documents, applying access control.
    - LangChainGDriveFilter: Integrates Google Drive documents into LangChain using OAuth2 credentials.
- DocumentFilterMixer: The DocumentFilterMixer aggregates multiple document processors, applying filters to handle complex document access control. It retrieves authorized and unauthorized documents based on the combined filters from each processor.
    - Filter Documents: filter() applies filters to a list of LangChain documents.
    - Retrieve Unauthorized Documents: get_unauthorized_documents() retrieves documents that fail authorization checks.
    - Retrieve Authorized Documents: get_authorized_documents() provides access to documents meeting authorization criteria.
- Metadata Filtering: The package includes metadata-based filtering, allowing users to apply filters with operators like EQ, GT, LT, CONTAINS, and more. Each filter can be customized to match document metadata for precise access control.

## License
This project is licensed under the MIT License.