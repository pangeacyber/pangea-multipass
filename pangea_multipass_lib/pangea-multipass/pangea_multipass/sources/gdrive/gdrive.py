# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

from typing import Any, List, Callable, Generic
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import enum
from pangea_multipass.core import (
    MetadataEnricher,
    PangeaMetadataKeys,
    PangeaMetadataValues,
    PangeaGenericNodeProcessor,
    MetadataFilter,
    FilterOperator,
    T,
)


class GDriveME(MetadataEnricher):
    """Google Drive Metadata Enricher.

    Enriches document metadata with Google Drive-specific attributes by accessing file metadata from the
    Google Drive API. Fields can include file permissions, parent folder names, file extensions, MIME types, etc.

    Attributes:
        _creds (Credentials): Credentials for authenticating with Google Drive.
        _files (dict): Cached file metadata from Google Drive.
        _fields (dict): Mappings of FileField attributes to metadata keys.
        _fields_param (str): Parameter for specifying fields to retrieve in Google Drive API requests.
    """

    class FileField(str, enum.Enum):
        PARENT = "parents"
        FILE_EXTENSION = "fileExtension"
        MIME_TYPE = "mimeType"
        SIZE = "size"
        MD5 = "md5Checksum"
        SHA1 = "sha1Checksum"
        SHA256 = "sha256Checksum"

        """Google Drive file fields"""

        def __str__(self):
            return str(self.value)

        def __repr__(self):
            return str(self.value)

    _creds: Credentials
    _files: dict[str, dict]
    _fields: dict[FileField, str]
    _fields_param: str

    def __init__(self, creds: Credentials, fields: dict[FileField, str]):
        # TODO: Add authz instance to upload permission tuples
        self._creds = creds
        self._fields = fields
        # Overwrite this value if exists
        self._set_fields_param()
        self._files = {}

    def extract_metadata(self, doc: Any, file_content: str) -> dict[str, Any]:
        """Extract Google Drive-specific metadata for the document.

        Args:
            doc (Any): The document to process.
            file_content (str): The content of the file.

        Returns:
            dict[str, Any]: Extracted metadata including attributes like file name, permissions, and parent folder.
        """

        metadata: dict[str, Any] = {}

        # This step is to normalize some attributes across platforms
        name = doc.metadata.get("file name", doc.metadata.get("file path", ""))
        metadata[PangeaMetadataKeys.FILE_NAME] = name
        metadata[PangeaMetadataKeys.DATA_SOURCE] = PangeaMetadataValues.DATA_SOURCE_GDRIVE

        id = self._get_id_from_metadata(doc.metadata)
        if not id:
            raise Exception("empty doc_id")
        metadata[PangeaMetadataKeys.GDRIVE_FILE_ID] = id

        # No fields to ask, so return empty
        if not self._fields:
            return metadata

        # If no files information, request it
        if not self._files:
            self._getGDrivePermissions()

        # If failed to request or no files at all, just return empty metadata
        if not self._files:
            return metadata

        # Process files
        file = self._files.get(id, None)
        if not file:
            return metadata

        for k, metadata_key in self._fields.items():
            if k == GDriveME.FileField.PARENT:
                value: Any = self._get_parent(file)
            else:
                value = file.get(k, None)

            if not value:
                continue

            metadata[metadata_key] = value

        return metadata
    
    def _get_id_from_metadata(self, metadata: dict[str, Any]) -> str:
        # Llama index "file_id" key
        value = metadata.get("file id", None)
        if value:
            return value

        # Langchain does not have id in metadata, it need to be extracted from "source"
        # "source": f"https://docs.google.com/document/d/{id}/edit",
        source = metadata.get("source", None)
        if source and type(source) is str:
            value = self._get_id_from_source(source) 
            if value:
                return value

        return ""

    def _get_id_from_source(self, source: str) -> str:
            parts = source.split("/")
            if len(parts) < 2:
                return ""

            return parts[-2]

    def _get_parent(self, file: dict[str, Any]) -> str:
        parents = file.get(GDriveME.FileField.PARENT, [])
        if not parents:
            return ""

        parent_id = parents[0]  # Asumming single parent
        parent_file = self._files.get(parent_id, None)
        if not parent_file:
            return ""

        return parent_file.get("name", "")

    def _set_fields_param(
        self,
    ):
        if not self._fields:
            self._fields_param = "nextPageToken, files(id)"
            return

        keys = "id, name"
        for k, _ in self._fields.items():
            keys = f"{keys}, {k}"

        self._fields_param = f"nextPageToken, files({keys})"

    # Get all the files belonging to the user (only top 10 for this example)
    def _getGDrivePermissions(self):
        # Create the Google Drive API service
        service = build("drive", "v3", credentials=self._creds)

        # Check if I need folders or not (would be a minor improvement)
        # query = "mimeType != 'application/vnd.google-apps.folder'"  # Query to search all files (exclude folders)
        query = ""

        files_dict = {}

        # Call the Drive v3 API
        page_size = 10

        results = (
            service.files()
            .list(
                spaces="drive",
                q=query,
                pageSize=page_size,
                fields=self._fields_param,
            )
            .execute()
        )

        while True:
            files = results.get("files", [])
            for file in files:
                id = file.get("id", None)
                if not id:
                    continue

                files_dict[id] = file

            next_page_token = results.get("nextPageToken", None)
            if not next_page_token:
                break

            # Keep requesting files until there is no more
            results = (
                service.files()
                .list(
                    spaces="drive",
                    q=query,
                    pageToken=next_page_token,
                    pageSize=page_size,
                    fields=self._fields_param,
                )
                .execute()
            )

        self._files = files_dict


class GDriveProcessor(PangeaGenericNodeProcessor, Generic[T]):
    """Processes Google Drive documents to determine access permissions.

    Filters documents based on access permissions for Google Drive files.

    Attributes:
        files_access_cache (dict[str, bool]): Cache storing access status for file IDs.
        creds (Credentials): Google API credentials.
        files_ids (List[str]): List of accessible Google Drive file IDs.
        get_node_metadata (Callable): Function to retrieve metadata for nodes.
    """

    files_access_cache: dict[str, bool] = {}
    creds: Credentials
    files_ids: List[str] = []
    get_node_metadata: Callable[[T], dict[str, Any]]

    def __init__(self, creds: Credentials, get_node_metadata: Callable[[T], dict[str, Any]]):
        super().__init__()
        self.creds = creds
        self.get_node_metadata = get_node_metadata

    def filter(
        self,
        nodes: List[T],
    ) -> List[T]:
        """Filter nodes by access permissions.

        Args:
            nodes (List[T]): List of nodes to process.

        Returns:
            List[T]: Nodes that are authorized.
        """

        filtered: List[T] = []
        for node in nodes:
            if self._is_authorized(node):
                filtered.append(node)
        return filtered

    def get_filter(
        self,
    ):
        """Generate a filter for processing Google Drive file IDs.

        Returns:
            MetadataFilter: A filter based on accessible file IDs.
        """

        if not self.files_ids:
            self.files_ids = GDriveAPI.list_all_file_ids(self.creds)

        return MetadataFilter(key=PangeaMetadataKeys.GDRIVE_FILE_ID, value=self.files_ids, operator=FilterOperator.IN)

    def _is_authorized(self, node: T) -> bool:
        metadata = self.get_node_metadata(node)
        return metadata[PangeaMetadataKeys.DATA_SOURCE] == PangeaMetadataValues.DATA_SOURCE_GDRIVE and self._has_access(
            metadata
        )

    def _has_access(self, metadata: dict[str, Any]) -> bool:
        id = metadata.get(PangeaMetadataKeys.GDRIVE_FILE_ID, None)
        if not id:
            raise KeyError("Invalid metadata key")

        access = self.files_access_cache.get(id, None)
        if access is not None:
            return access

        access = GDriveAPI.check_file_access(self.creds, id)
        self.files_access_cache[id] = access
        return access


class GDriveAPI:
    _SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/drive.metadata.readonly",
    ]

    _user_token_filepath: str = "gdrive_access_token.json"

    @staticmethod
    def get_and_save_access_token(credentials_filepath, token_filepath, scopes):
        """
        Retrieves and saves the OAuth2 access token for Google Drive.

        Args:
            credentials_filepath (str): Path to the credentials file obtained from Google Cloud Console.
            token_filepath (str): Path to save the OAuth2 access token.
            scopes (list): List of OAuth2 scopes required for authentication.
        """

        flow = InstalledAppFlow.from_client_secrets_file(credentials_filepath, scopes)
        creds = flow.run_local_server(port=8080, authorization_prompt_message="", access_type="offline", prompt="consent")
        # Save the credentials for the next run
        with open(token_filepath, "w") as token:
            token.write(creds.to_json())

    @staticmethod
    def get_user_info(creds: Credentials):
        """
        Retrieves user profile information using the Google OAuth2 API.

        Args:
            creds (Credentials): The OAuth2 credentials object.

        Returns:
            dict: A dictionary containing user profile information.
        """

        service = build("oauth2", "v2", credentials=creds)
        user_info = service.userinfo().get().execute()
        return user_info

    @staticmethod
    def get_user_credentials(
        credentials_filepath: str, user_token_filepath: str = _user_token_filepath, scopes=_SCOPES
    ):
        """
        Retrieves and saves user credentials for Google Drive authentication.

        Args:
            credentials_filepath (str): Path to the credentials file obtained from Google Cloud Console.
            user_token_filepath (str): Path to save the OAuth2 access token.
            scopes (list): List of OAuth2 scopes required for authentication.

        Returns:
            Credentials: The OAuth2 credentials object.
        """

        # Invoke Google /auth endpoint and save he token for later use
        GDriveAPI.get_and_save_access_token(credentials_filepath, user_token_filepath, scopes)

        # Load the OAuth 2.0 credentials (ensure this file is generated from the OAuth flow)
        return Credentials.from_authorized_user_file(user_token_filepath, scopes)

    @staticmethod
    def check_file_access(creds: Credentials, file_id: str) -> bool:
        """
        Checks if the authenticated user has access to a specified Google Drive file.

        Args:
            creds (Credentials): The OAuth2 credentials object.
            file_id (str): The ID of the file to check access.

        Returns:
            bool: `True` if the user has access, `False` otherwise.
        """

        service = build("drive", "v3", credentials=creds)
        try:
            service.files().get(fileId=file_id, fields="id, name").execute()
            return True
        except:
            return False

    @staticmethod
    def list_all_file_ids(creds: Credentials) -> List[str]:
        """
        Lists all file IDs accessible by the authenticated user.

        Args:
            creds (Credentials): The OAuth2 credentials object.

        Returns:
            List[str]: A list of file IDs accessible by the user.
        """

        service = build("drive", "v3", credentials=creds)
        file_ids = []
        page_token = None

        while True:
            try:
                # List files, requesting only the file ID
                response = (
                    service.files()
                    .list(q="trashed=false", fields="nextPageToken, files(id)", pageToken=page_token)
                    .execute()
                )

                # Collect the file IDs
                for file in response.get("files", []):
                    file_ids.append(file["id"])

                # Break the loop if there are no more pages
                page_token = response.get("nextPageToken", None)
                if page_token is None:
                    break
            except Exception as error:
                print(f"An error occurred: {error}")
                break

        return file_ids
