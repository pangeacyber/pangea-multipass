# Pangea Multipass: Your Authorization Helper

Pangea Multipass is a Python library for checking user access to upstream data sources.

In practice, you can use it to check if a specific user has access to a file in a Google Drive, a ticket in Jira, or a page in Confluence. In concept, we've built this library to be extensible to eventually support Slack channels, Github repositories, Salesforce opportunities, and more. 

We originally built this to support our customers' Retrieval-Augmented Generation (RAG) applications to mitigate data leaks. In a RAG architecture, the application inserts additional context at inference time. If you don't check the user's authorization to that context, you could inadvertently leak sensitive information. 

While this is useful in AI/LLM apps, we've abstracted this to work independently so you can use it in any app.

Check out the `pangea_multipass_lib/examples` folder for AI-specific and generic examples.  

## Features

- **Document Reading**: Supports document content extraction for use in processing and enrichment.
- **Metadata Enrichment**: Includes enrichers for hashing, constant value setting, and custom metadata.
- **Metadata Filtering**: Provides flexible operators to filter document metadata for customized queries.
- **Authorization Processing**: Manages authorized and unauthorized nodes with customizable node processors.
- **Extensible**: Built on abstract base classes, allowing easy extension and customization of functionality.

## Installation

To install `pangea-multipass`, you can use [Poetry](https://python-poetry.org/) for dependency management:

```bash
poetry add pangea-multipass
```

Alternatively, if installing directly from the source:
- Clone the repository and run the following commands:

```bash
cd pangea-multipass
poetry install
```

There are full runnable demos in the `pangea_multipass_lib\examples` directory but here are the key aspects.

Using a set of Google Drive credentials - follow the steps in the examples - you initialize the data source:

```python
    gdrive_reader = GoogleDriveReader(
        folder_id=rbac_fid, token_path=admin_token_filepath, credentials_path=credentials_filepath
    )
    documents = gdrive_reader.load_data(folder_id=rbac_fid)
```

This gives you a list of files which you can then use the processors to filter into the authorized and unauthorized resource lists:

```python
gdrive_processor = LlamaIndexGDriveProcessor(creds)
node_processor = NodePostprocessorMixer([gdrive_processor])

authorized_docs = node_processor.postprocess_nodes(documents)
unauthorized_docs = node_processor.get_unauthorized_nodes()
```

In general, the authorized list will be more important but you may log or notify an admin if a user is attempting to access a folder where they have limited access. It could be an attempt at data theft or their permissions are incomplete.

## Roadmap

At release, this library supports Google Workspace, Confluence, and Jira. For adding systems, our top priorities are:

- Slack
- Github
- Salesforce
- Box

Others we plan to support or are looking for contributions are:

- Office 365
- Zoom
- Dropbox
- Gitlab
- Zendesk
- Notion
- Sharepoint
- Asana
- Hubspot

Check out `EXTENDING.md` for the specific structure and requirements for extending Pangea Multipass for your data sources. Pull requests are welcome.
