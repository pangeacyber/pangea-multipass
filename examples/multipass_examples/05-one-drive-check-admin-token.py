import os

import requests
from pangea_multipass import OauthFlow
from pangea_multipass.utils import data_load, data_save


class OneDriveAPI:
    AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"


class OneDriveReader:
    """
    A class to read and download all files from a specified OneDrive folder.
    """

    def __init__(self, access_token: str, folder_path: str = "Documents/MyFolder"):
        """
        Initializes the OneDriveReader with an access token.

        :param access_token: OAuth2 access token for authentication.
        """
        self.access_token = access_token
        self.base_url = "https://graph.microsoft.com/v1.0/me/drive/root:/"
        self._folder_path = folder_path
        self._url = self._get_url()

    def restart(
        self,
    ) -> None:
        self._url = self._get_url()

    def has_more(
        self,
    ) -> bool:
        return self._url is not None

    def load_data(
        self,
    ) -> None:
        """
        Requests and downloads all files in a OneDrive folder, handling pagination.

        :param folder_path: Path to the OneDrive folder (e.g., "Documents/MyFolder").
        :param download_path: Local directory to save the downloaded files.
        """
        headers = {"Authorization": f"Bearer {self.access_token}"}

        while self._url is not None:
            response = requests.get(self._url, headers=headers)
            if response.status_code != 200:
                print("Error fetching files:", response.json())
                return

            data = response.json()
            for item in data.get("value", []):
                print("Downloading:", item["name"])
                # if item.get("file"):  # Ensure it's a file and not a folder
                #     self.download_file(item["@microsoft.graph.downloadUrl"], item["name"], download_path)

            # Handle pagination
            self._url = data.get("@odata.nextLink")

    def _download_file(self, file_url: str) -> str:
        """
        Downloads a file from OneDrive.

        :param file_url: The direct download URL for the file.
        """
        response = requests.get(file_url, stream=True)
        return str(response.content)

    def _get_url(self) -> str:
        return f"{self.base_url}{self._folder_path}:/children"


# Pangea-Multipass Azure App Apllication ID
client_id = "a49112ad-1738-4a9e-bc62-1c4201f6f859"

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
        code_verifier=code_verifier, code_challenge=code_challenge, scope="files.read.all offline_access"
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
folder_path = "Documents/MyFolder"
download_path = "./downloads"  # Local directory to save files

reader = OneDriveReader(access_token, folder_path)
reader.load_data()
