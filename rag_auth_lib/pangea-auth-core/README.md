# Pangea Auth Core

Pangea Auth Core is a Python library for enriching metadata of documents from Google Drive, JIRA, and Confluence. This library is designed with a flexible architecture, particularly useful for Retrieval-Augmented Generation (RAG) applications and can function in a framework-less environment.

## Features

- **Metadata Enrichment**: Includes enrichers for hashing, constant value setting, and custom metadata.
- **Document Reading**: Supports document content extraction for use in processing and enrichment.
- **Authorization Processing**: Manages authorized and unauthorized nodes with customizable node processors.
- **Extensible**: Built on abstract base classes, allowing easy extension and customization of functionality.
- **Metadata Filtering**: Provides flexible operators to filter document metadata for customized queries.

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

## License
This project is licensed under the MIT License - see the LICENSE file for details.
