import json

import requests


class DropboxAPI:
    AUTH_URL = "https://www.dropbox.com/oauth2/authorize"
    TOKEN_URL = "https://api.dropbox.com/oauth2/token"
    LIST_FILES_URL = "https://api.dropboxapi.com/2/files/list_folder"
    LIST_CONTINUE_URL = "https://api.dropboxapi.com/2/files/list_folder/continue"

    @staticmethod
    def download_file(file_path: str, token: str):
        """Download a file from Dropbox."""

        headers = {
            "Authorization": f"Bearer {token}",
            "Dropbox-API-Arg": json.dumps({"path": file_path}),
        }

        response = requests.post("https://content.dropboxapi.com/2/files/download", headers=headers, stream=True)
        response.raise_for_status()
        return response.content
