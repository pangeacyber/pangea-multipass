import json
import os
from typing import List, Optional

import requests
from pangea_multipass import (
    MultipassDocument,
    OauthFlow,
    OneDriveClient,
    OneDriveProcessor,
    PangeaMetadataKeys,
    PangeaMetadataValues,
    generate_id,
    get_document_metadata,
)
from pangea_multipass.utils import data_load, data_save


class OneDriveAPI:
    AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"


class OneDriveFile:
    def __init__(self, item: dict):  # noqa
        self.name = item["name"]
        self.url = item["@microsoft.graph.downloadUrl"]
        self.metadata = {}
        self.metadata["name"] = self.name
        self.metadata[PangeaMetadataKeys.DATA_SOURCE] = PangeaMetadataValues.DATA_SOURCE_ONEDRIVE
        self.metadata[PangeaMetadataKeys.ONEDRIVE_ID] = item["id"]
        self.metadata[PangeaMetadataKeys.ONEDRIVE_PATH] = item["parentReference"]["path"]


class OneDriveReader:
    """
    A class to read and download all files from a specified OneDrive folder.
    """

    access_token: str
    base_url: str
    _folder_path: str
    _file_counter: int
    _files_list: Optional[List[OneDriveFile]]

    def __init__(self, access_token: str, folder_path: str = "Documents/MyFolder"):
        """
        Initializes the OneDriveReader with an access token.

        :param access_token: OAuth2 access token for authentication.
        """
        self.access_token = access_token
        self.base_url = "https://graph.microsoft.com/v1.0/me/drive/root:/"
        self._folder_path = folder_path
        self.restart()

    def restart(
        self,
    ) -> None:
        self._file_counter = 0
        self._files_list = None

    @property
    def has_more(
        self,
    ) -> bool:
        return self._files_list is None or self._file_counter < len(self._files_list)

    def load_data(
        self,
        page_size: int = 100,
    ) -> List[MultipassDocument]:
        """
        Requests and downloads page_size files in a OneDrive folder, handling pagination.
        """

        documents: List[MultipassDocument] = []

        if self._files_list is None:
            self.restart()
            self._files_list = self._load_files(self._folder_path)

        values = range(self._file_counter, min(self._file_counter + page_size, len(self._files_list)))

        for i in values:
            item = self._files_list[i]
            content = self._download_file(item.url)
            documents.append(MultipassDocument(generate_id(), content, item.metadata))

        self._file_counter += len(values)
        return documents

    def _load_files(self, path: str) -> List[OneDriveFile]:
        """
        Loads all files from a OneDrive folder.
        """

        headers = {"Authorization": f"Bearer {self.access_token}"}
        files: List[OneDriveFile] = []
        url = self._get_path_children_url(path)

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print("Error fetching files:", response.json())
            return files

        data = response.json()
        for item in data.get("value", []):
            if item.get("file"):
                files.append(OneDriveFile(item))
            elif item.get("folder"):
                name = item["name"]
                files.extend(self._load_files(f"{path}/{name}"))

        return files

    def _download_file(self, file_url: str) -> str:
        """
        Downloads a file from OneDrive.

        :param file_url: The direct download URL for the file.
        """
        response = requests.get(file_url, stream=True)
        return str(response.content)

    def _get_path_children_url(self, path) -> str:
        return f"{self.base_url}{path}:/children"


# Pangea-Multipass Azure App Apllication ID
client_id = "a2cb307a-356a-4308-adfb-db563d8f1406"

# File to store tokens
ONE_DRIVE_TOKEN_FILE = "one_drive_tokens.json"

if not os.path.exists(ONE_DRIVE_TOKEN_FILE):
    code_verifier, code_challenge = OauthFlow.generate_pkce_pair()

    flow = OauthFlow(
        auth_url=OneDriveAPI.AUTH_URL,
        token_url=OneDriveAPI.TOKEN_URL,
        client_id=client_id,
    )
    tokens = flow.run_pkce(
        code_verifier=code_verifier,
        code_challenge=code_challenge,
        scope="files.read.all user.read.all directory.read.all offline_access",
    )
else:
    tokens = data_load(ONE_DRIVE_TOKEN_FILE)
    access_token = OauthFlow.refresh_access_token(
        url=OneDriveAPI.TOKEN_URL, refresh_token=tokens["refresh_token"], client_id=client_id
    )
    tokens.update(access_token)

data_save(ONE_DRIVE_TOKEN_FILE, tokens)
access_token = tokens["access_token"]


# Example usage
folder_path = "MyFolder"
download_path = "./downloads"  # Local directory to save files

reader = OneDriveReader(access_token, folder_path)
page = 1

documents = []

while reader.has_more:
    docs = reader.load_data(page_size=10)
    print(f"Page {page}.")
    page += 1
    documents.extend(docs)

print("Total files:", len(documents))

# Inference time
user_email = os.getenv("ONEDRIVE_USER_EMAIL")
# user_email = "andres.tournour@pangeagondwana.onmicrosoft.com"
assert user_email

client = OneDriveClient()

user_id = client.get_user_id(access_token, user_email)
assert user_id

processor = OneDriveProcessor(access_token, user_id, get_document_metadata)
allowed_files = processor.filter(documents)
print("Allowed files:", len(allowed_files))
