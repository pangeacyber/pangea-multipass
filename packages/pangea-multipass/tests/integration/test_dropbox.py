import os
import time
import unittest

from pangea_multipass import DropboxAPI, DropboxProcessor, DropboxReader, OauthFlow, get_document_metadata

_TOTAL_FILES = 10
_AUTHORIZED_FILES = 5
_AUTHORIZED_FOLDERS = 3


class TestDropbox(unittest.TestCase):
    def setUp(self) -> None:
        refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN") or ""
        assert refresh_token
        app_key = os.getenv("DROPBOX_APP_KEY") or ""
        assert app_key
        self.user_email = os.getenv("DROPBOX_USER_EMAIL") or ""
        assert self.user_email
        token_data = OauthFlow.refresh_access_token(
            url=DropboxAPI.TOKEN_URL, refresh_token=refresh_token, client_id=app_key
        )
        self.access_token = token_data["access_token"]
        assert self.access_token

    def test_dropbox(self) -> None:
        reader = DropboxReader(token=self.access_token)
        files = reader.load_data()
        assert len(files) == _TOTAL_FILES

        processor = DropboxProcessor(
            token=self.access_token, user_email=self.user_email, get_node_metadata=get_document_metadata
        )
        filter = processor.get_filter()
        assert len(filter.value) == _AUTHORIZED_FOLDERS

        authorized_files = processor.filter(files)
        assert len(authorized_files) == _AUTHORIZED_FILES

    def test_dropbox_pagination(self) -> None:
        reader = DropboxReader(token=self.access_token)
        has_more_files = True
        all_files = []

        while has_more_files:
            files = reader.read_page(page_size=1)
            all_files.extend(files)
            has_more_files = reader.has_more_files

        assert len(all_files) == _TOTAL_FILES
