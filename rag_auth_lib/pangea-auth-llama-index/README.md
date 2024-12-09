# Pangea Multipass for Llama Index

This library extends the Pangea Mutlipass package to integrate metadata enrichment and document processing with Llama Index. It enables seamless use of authorization checks, metadata filtering, and custom processors on documents from Google Drive, JIRA, and Confluence, utilizing Llama Index structures for Retrieval-Augmented Generation (RAG) applications.

## Features

- **Document Integration**: Adapts Pangea processors and enrichers to handle Llama Index documents.
- **Llama Index-Compatible Filtering**: Provides metadata filtering with operators for fine-grained document access control.
- **Authorization Processing**: Aggregates and applies multiple authorization checks on Llama Index nodes with custom, combinable node processors.

## Installation

Use [Poetry](https://python-poetry.org/) to install dependencies:

```bash
poetry add pangea-multipass-llama-index
```

If installing directly from the source, clone the repository and run:

```bash
cd pangea-multipass-llama-index
poetry install
```

## Usage
### Core Components
- Document Reader: LIDocumentReader reads content from Llama Index documents for enrichment.
- Processors for Llama Index:
    - LlamaIndexJiraProcessor — Handles JIRA documents within Llama Index.
    - LlamaIndexConfluenceProcessor — Processes Confluence documents in Llama Index.
    - LlamaIndexGDriveProcessor — Manages Google Drive documents in Llama Index.
    - Node Postprocessor Mixer: Combines multiple processors for complex, multi-source document filtering.
- Metadata Filters: Filter documents based on metadata using operators like EQ, CONTAINS, and custom metadata keys.

## License
This project is licensed under the MIT License.
