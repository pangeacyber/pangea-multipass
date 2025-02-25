from typing import List, Optional

import requests

from .core import MultipassDocument, PangeaMetadataKeys, PangeaMetadataValues, generate_id
from .sources import DropboxAPI


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
    ) -> List[MultipassDocument]:
        """
        Retrieves all files in Dropbox.
        It download and return just files, skipping folders.
        """

        documents: List[MultipassDocument] = []

        while self._has_more:
            documents.extend(self.read_page(page_size=50))

        return documents

    def read_page(self, page_size: int = 50) -> List[MultipassDocument]:
        """
        Read a page of files from Dropbox
        Page size is an approximate number of files to read.
        It could be more due to Drobox API limitations or it could be less due to folders being skipped.
        """

        documents: List[MultipassDocument] = []

        url = DropboxAPI.LIST_FILES_URL if self._cursor is None else DropboxAPI.LIST_CONTINUE_URL
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

            file_path: str = entrie.get("path_lower", None)
            if not file_path:
                continue

            name = entrie.get("name", "")
            path = file_path.removesuffix(f"/{name}")

            file = DropboxAPI.download_file(token=self._token, file_path=file_path)
            metadata: dict[str, str] = {
                PangeaMetadataKeys.DATA_SOURCE: PangeaMetadataValues.DATA_SOURCE_DROPBOX,
                PangeaMetadataKeys.DROPBOX_ID: entrie.get("id", ""),
                PangeaMetadataKeys.DROPBOX_PATH: path,
                PangeaMetadataKeys.DROPBOX_FILE_PATH: file_path,
                PangeaMetadataKeys.FILE_PATH: file_path,
                PangeaMetadataKeys.FILE_NAME: name,
            }
            documents.append(MultipassDocument(id=generate_id(), content=file, metadata=metadata))

        self._has_more = result.get("has_more", False)
        self._cursor = result.get("cursor")
        return documents
