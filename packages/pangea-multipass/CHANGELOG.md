# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added 

- GitLabReader and GitLabProcessor

### Fixed

- Handle null fields on issues in JiraME
- Handle trailing slash in Jira URL


## 0.2.0 - 2025-01-15

### Added

- GitHub repository's reader and processor.
- Slack channel's reader and processor.
- `account_id` support on JiraProcessor.
- Check user email permissions with admin credentials in GDriveProcessor.
- Check username permissions with admin token in GitHubProcessor.
- Check user email permissions with admin token in SlackProcessor.
- `py.typed` marker file.
- Check user account id permissions with admin token in JiraProcessor.
- Check user account id permission with admin token in ConfluenceProcessor.

## 0.1.0 - 2024-12-24

### Added

- Medatata enritcher and processor for Google Drive, Jira and Confluence data sources.
