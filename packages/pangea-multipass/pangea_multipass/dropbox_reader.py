from typing import List, Optional

import requests

from .core import MultipassDocument, PangeaMetadataKeys, PangeaMetadataValues, generate_id
from .sources import DropboxAPI

DROPBOX_AUTH_URL = "https://www.dropbox.com/oauth2/authorize"
DROPBOX_TOKEN_URL = "https://api.dropbox.com/oauth2/token"
DROPBOX_LIST_FILES_URL = "https://api.dropboxapi.com/2/files/list_folder"
DROPBOX_LIST_CONTINUE_URL = "https://api.dropboxapi.com/2/files/list_folder/continue"


class DropboxReader:
    _token: str
    """Dropbox access token"""

    _has_more: bool
    _cursor: Optional[str]
    _folder_path: str
    _recursive: bool

    def __init__(self, token: str, folder_path: str = "", recursive: bool = True):
        self._token = token
        self._folder_path = folder_path
        self._recursive = recursive
        self.restart()

    def restart(self):
        self._has_more = True
        self._cursor = None

    @property
    def has_more_files(self):
        """Check if there are more files to read"""
        return self._has_more

    def load_data(
        self,
        page_size: int = 50,
    ) -> List[MultipassDocument]:
        """
        Retrieves files in Dropbox using pagination.
        Call iteratively while has_more() is True to retrieves all files.
        It download and return just files, skipping folders.
        It could return less document than the page size.
        """
        documents: List[MultipassDocument] = []

        if self._has_more:
            url = DROPBOX_LIST_FILES_URL if self._cursor is None else DROPBOX_LIST_CONTINUE_URL
            data = {"path": self._folder_path, "recursive": self._recursive, "limit": page_size}
            if self._cursor:
                data = {"cursor": self._cursor}

            headers = {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()

            result = response.json()
            entries = result.get("entries", [])

            for entrie in entries:
                if entrie.get(".tag", "") != "file":
                    continue
                path = entrie.get("path_lower", None)
                if not path:
                    continue
                file = DropboxAPI.download_file(token=self._token, file_path=path)
                metadata: dict[str, str] = {
                    PangeaMetadataKeys.DATA_SOURCE: PangeaMetadataValues.DATA_SOURCE_DROPBOX,
                    PangeaMetadataKeys.DROPBOX_ID: entrie.get("id", ""),
                    PangeaMetadataKeys.DROPBOX_FILE_PATH: path,
                    PangeaMetadataKeys.FILE_PATH: path,
                    PangeaMetadataKeys.FILE_NAME: entrie.get("name", ""),
                }
                documents.append(MultipassDocument(id=generate_id(), content=file, metadata=metadata))

            self._has_more = result.get("has_more", False)
            self._cursor = result.get("cursor")

        return documents
