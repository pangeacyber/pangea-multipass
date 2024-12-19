# Trying Pangea Multipass

Pangea Multipass is a general purpose library for checking a user's access to resources in an upstream system. While we (Pangea) originally built this for our AI/LLM apps, you can use this library independently. To see that in action, check out the `simple` folder, otherwise explore your framework of choice.


Each directory has its own README to get setup though many of the steps overlap.

Using these examples

## Set up the code

In each of the directories, you can run the installer. We recommend using a virtual environment:

```
poetry install
```

## Set up the environment

### Google Drive

In order to use Google Drive as a source in the examples you need to:

- Download the `credentials.json` file from Google console and save it in `<repo-root-directory>/examples/` folder.
- On the example script update `gdrive_fid` variable value with the Google Drive folder ID to process.


### Jira

In order to use Jira as a source, it's needed to set some environment variables:
- `JIRA_BASE_URL`: Jira project base URL. Its format is `<your-project-id>.atlassian.net/`. Take care of remove `https://` part.
- `JIRA_ADMIN_EMAIL`: Admin email used in the ingestion time. System will process all the tickets this user has access to.
- `JIRA_ADMIN_TOKEN`: Access token of the admin email set above. [Learn more](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)
- `JIRA_USER_EMAIL`: User email used in inference time. This email will be used to validate which tickets returned by the LLM the user has access to.
- `JIRA_USER_TOKEN`: Access token of the user email set above. [Learn more](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)


### Confluence

In order to use Confluence as a source it's needed to set some environment variables:
- `CONFLUENCE_BASE_URL`: Confluence project base URL. Its format is `https://<your-project-id>.atlassian.net/`.
- `CONFLUENCE_ADMIN_EMAIL`: Admin email used in the ingestion time. System will process all the files this user has access to.
- `CONFLUENCE_ADMIN_TOKEN`: Access token of the admin email set above. [Learn more](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)
- `CONFLUENCE_USER_EMAIL`: User email used in inference time. This email will be used to validate which files returned by the LLM the user has access to.
- `CONFLUENCE_USER_TOKEN`: Access token of the user email set above. [Learn more](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)


## Using the Code

### Simple example

It's possible to run some examples without connecting any LLM. On the `packages/examples` folder you can find:
- `llama_index_examples/04-gdrive-check.py`

To run one of this examples make sure to [set up the environment](#set-up-the-environment), then move to the example folder and run:
```bash
poetry run python 04-gdrive-check.py 
```


## LangChain Example

- todo: connect to bedrock
- todo: run the code

## Llama Index Example

- todo: connect to bedrock
- todo: run the code
