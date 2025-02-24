import os
import unittest

from pangea_multipass import GitHubProcessor, GitHubReader, get_document_metadata

token = os.getenv("GITHUB_ADMIN_TOKEN") or ""
username = os.getenv("GITHUB_USERNAME") or ""

_TOTAL_FILES = 8
_AUTHORIZED_FILES = 5
_AUTHORIZED_PROJECTS = 2


class TestGitHub(unittest.TestCase):
    def setUp(self) -> None:
        assert token
        assert username

    def test_github(self) -> None:
        reader = GitHubReader(token=token)
        files = reader.load_data()
        assert len(files) == _TOTAL_FILES

        processor = GitHubProcessor(token=token, username=username, get_node_metadata=get_document_metadata)
        filter = processor.get_filter()
        assert len(filter.value) == _AUTHORIZED_PROJECTS

        authorized_files = processor.filter(files)
        assert len(authorized_files) == _AUTHORIZED_FILES

    def test_github_pagination(self) -> None:
        reader = GitHubReader(token=token)

        repos = reader.get_repos()
        assert len(repos) == 3

        all_files = []

        for repo in repos:
            has_more_files = True
            while has_more_files:
                files = reader.read_repo_files(repo, page_size=1)
                all_files.extend(files)
                has_more_files = reader.has_more_files
                assert len(files) == 1

        assert len(all_files) == _TOTAL_FILES
