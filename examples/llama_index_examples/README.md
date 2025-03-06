# Pangea Auth Llama Index Example App

These examples application demonstrates the integration of `PangeaAuth` with `LlamaIndex` to perform secure document retrieval and metadata enrichment from multiple data sources. The app connects to Google Drive, Confluence, and JIRA, retrieves documents, enriches metadata for authorization, and performs query-based searches using vector indexing.

## Configuration

### Environment Variables

Set the following environment variables to configure access to Confluence and JIRA:

- **Confluence**:
  - `CONFLUENCE_ADMIN_TOKEN`: Admin token for Confluence authentication.
  - `CONFLUENCE_ADMIN_EMAIL`: Admin email for Confluence authentication.
  - `CONFLUENCE_BASE_URL`: Base URL of the Confluence server.
  - `CONFLUENCE_USER_TOKEN`: User token for accessing Confluence.
  - `CONFLUENCE_USER_EMAIL`: User email for accessing Confluence.

- **JIRA**:
  - `JIRA_BASE_URL`: Base URL of the JIRA server.
  - `JIRA_ADMIN_EMAIL`: Admin email for JIRA authentication.
  - `JIRA_ADMIN_TOKEN`: Admin token for JIRA authentication.
  - `JIRA_USER_TOKEN`: User token for accessing JIRA.
  - `JIRA_USER_EMAIL`: User email for accessing JIRA.

<ADMIN> environment variables are used in ingestion time and this `admin` should have access to all the cloud files/issues/pages that are desired to be included in the vector store.
<USER> environment variables are used in inference time and in this case, `user` could have restricted access to some files/issues/pages that are going to be checked on runtime.

### Required Config Files

1. **Google OAuth2 Credentials**: `credentials.json`
   This file should contain your OAuth2 credentials for Google Drive API access. Download it from your Google Cloud Console and place it in the `examples` directory.

2. **Admin Access Token for Google Drive**: `admin_access_token.json`
   This file stores the access token for the Google Drive admin user and is generated through OAuth2.

## Installation and Setup

### Prerequisites

Ensure you have [Poetry](https://python-poetry.org/docs/#installation) installed for dependency management and virtual environment setup.

### Installing Dependencies

Run the following command to install all dependencies:

```bash
poetry install --no-root
```

## Running the Application
- Set Up Environment Variables: Set all required environment variables in your terminal or in a .env file in the root directory.
- Run the App:

```bash
poetry run python 07-2-rag-LlamaIndex-all-sources-processor
```

## How It Works
### Document Retrieval and Enrichment
The app connects to Google Drive, Confluence, and JIRA to retrieve documents based on the provided credentials and metadata filters. Documents are enriched with metadata through the PangeaAuth framework, ensuring enhanced access control.

### Query Engine and Access Control
The app uses a vector store to index documents and enables query-based retrieval. The query engine notifies users if certain sources were unauthorized, ensuring that answers reflect accessible data only.

### Unauthorized Document Warning
If documents from any source are unauthorized for the user, a warning is displayed, indicating missing context due to access restrictions.

## License
This project is licensed under the MIT License.
