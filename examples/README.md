# Trying Pangea Multipass

Pangea Multipass is a general purpose library for checking a user's access to resources in an upstream system. While we (Pangea) originally built this for our AI/LLM apps, you can use this library independently. To see that in action, check out the `multipass_examples` folder, otherwise explore your LLM framework of choice.

Each directory has its own README to get setup though many of the steps overlap.

## Set up the environment

These are the upstream data sources the core library currently supports. Configure the ones you need and store the credentials for the examples. Most of these will require administrator access to get the credentials.


### Google Drive

In order to use Google Drive as a source in the examples you need to:

- Download the `credentials.json` file from Google console and save it in `<repo-root-directory>/examples/` folder.
- On the example script update `gdrive_fid` variable value with the Google Drive folder ID to process.


### Jira

In order to use Jira as a source, it's needed to set some environment variables:
- `JIRA_BASE_URL`: Jira project base URL. Its format is `<your-project-id>.atlassian.net/`. Take care of remove `https://` part.
- `JIRA_ADMIN_EMAIL`: Admin email used in the ingestion time. System will process all the tickets this user has access to.
- `JIRA_ADMIN_TOKEN`: Access token of the admin email set above. [Learn more](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/).
- `JIRA_USER_EMAIL`: User email used in inference time. This email will be used to validate which tickets returned by the LLM the user has access to.
- `JIRA_USER_TOKEN`: Access token of the user email set above. [Learn more](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/).
- `JIRA_USER_ACCOUNT_ID`: Set it to use `JIRA_ADMIN_TOKEN` and `JIRA_ADMIN_EMAIL` at inference time to check user permissions. This way it's not needed to set `JIRA_USER_EMAIL` and `JIRA_USER_TOKEN`.


### Confluence

In order to use Confluence as a source it's needed to set some environment variables:
- `CONFLUENCE_BASE_URL`: Confluence project base URL. Its format is `https://<your-project-id>.atlassian.net/`.
- `CONFLUENCE_ADMIN_EMAIL`: Admin email used in the ingestion time. System will process all the files this user has access to.
- `CONFLUENCE_ADMIN_TOKEN`: Access token of the admin email set above. [Learn more](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)
- `CONFLUENCE_USER_EMAIL`: User email used in inference time. This email will be used to validate which files returned by the LLM the user has access to.
- `CONFLUENCE_USER_TOKEN`: Access token of the user email set above. [Learn more](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)


### Github

In order to use Github as a source it's needed to set some environment variables:
- `GITHUB_ADMIN_TOKEN`: Access token used in the ingestion time. System will process all the repositories this token has access to. [Learn more](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token). This could be a `Fine-grained personal access token` with access to all the respositories owned by the admin account and `repository permission` to `read access to code and metadata`.
- `GITHUB_USER_TOKEN`: Token user in inference time. It will be used to validate which files returned by the LLM the user has access to. [Learn more](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token-classic). This must be a `classic personal access token` with scoped access to (at least) all the `repo` items.


### Slack

In order to use Slack as a source it's needed to set some environment variables, those are `SLACK_ADMIN_TOKEN` and `SLACK_USER_TOKEN`.

To get these tokens, you must create a Slack App and generate the tokens. The default app settings are sufficient. For further instructions about how to get slack tokens you could [click here](https://api.slack.com/tutorials/tracks/getting-a-token).

For this particular application the token's scope should be at least: `channels:history`, `groups:history`, `users:read`, `users:read.email` to process all public and private channels and access to user emails to check its permissions.

- `SLACK_ADMIN_TOKEN`: Access token used in the ingestion time. System will process all the channels this token has access to.
- `SLACK_USER_TOKEN`: Token user in inference time. It will be used to validate which files returned by the LLM the user has access to.
