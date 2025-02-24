import os
import unittest

from pangea_multipass import GitLabProcessor, GitLabReader, get_document_metadata

token = os.getenv("GITLAB_ADMIN_TOKEN") or ""
username = os.getenv("GITLAB_USERNAME") or ""

_TOTAL_FILES = 8
_AUTHORIZED_FILES = 5
_AUTHORIZED_PROJECTS = 2


class TestGitLab(unittest.TestCase):
    def setUp(self) -> None:
        assert token
        assert username

    def test_gitlab(self) -> None:
        reader = GitLabReader(token=token, page_size=10)
        files = reader.load_data()
        assert len(files) == _TOTAL_FILES

        processor = GitLabProcessor(admin_token=token, username=username, get_node_metadata=get_document_metadata)
        filter = processor.get_filter()
        assert len(filter.value) == _AUTHORIZED_PROJECTS

        authorized_files = processor.filter(files)
        assert len(authorized_files) == _AUTHORIZED_FILES
