# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

from llama_index.readers.google import GoogleDriveReader
import os
from google.oauth2.credentials import Credentials
from typing import List
import warnings

from pangea_multipass import GDriveME, enrich_metadata, PangeaMetadataKeys
from pangea_multipass_llama_index import LIDocumentReader

# Suppress specific warning
warnings.filterwarnings("ignore", message='Field "model_name" has conflict with protected namespace')

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

# Sample folder data folder owned by apurv@gondwana.cloud https://drive.google.com/drive/u/1/folders/1Kj77oi2QGEOPKcIo_hKZPiHDJyKKFVgR
rbac_fid = "1Kj77oi2QGEOPKcIo_hKZPiHDJyKKFVgR"

def google_drive_read_docs() -> List:
    print("Loading Google Drive docs...")
    # Google Drive Data Ingestion
    credentials_filepath = os.path.abspath("../../credentials.json")

    # File name for the admin user
    admin_token_filepath = "admin_access_token.json"

    # # Invoke Google /auth endpoint and save he token for later use
    # GDrive.get_and_save_access_token(credentials_filepath, admin_token_filepath, SCOPES)

    # load the documents and create the index
    gdrive_reader = GoogleDriveReader(
        folder_id=rbac_fid, token_path=admin_token_filepath, credentials_path=credentials_filepath
    )
    documents = gdrive_reader.load_data(folder_id=rbac_fid)

    print(f"Processing {len(documents)} docs...")

    # Metadata enricher library
    creds = Credentials.from_authorized_user_file(admin_token_filepath, SCOPES)
    gdrive_me = GDriveME(creds, {})
    enrich_metadata(documents, [gdrive_me], reader=LIDocumentReader())
    # Finish metadata enrichement

    return documents


documents = google_drive_read_docs()

# Inference

from pangea_multipass_llama_index import LlamaIndexGDriveProcessor, NodePostprocessorMixer
from pangea_multipass import GDriveAPI

# Create GDrive filter
credentials_filepath = os.path.abspath("../../credentials.json")
creds = GDriveAPI.get_user_credentials(credentials_filepath, scopes=SCOPES)
user_info = GDriveAPI.get_user_info(creds)
user = user_info.get("name", "default_name")

gdrive_processor = LlamaIndexGDriveProcessor(creds)
node_processor = NodePostprocessorMixer([gdrive_processor])

# Proccess documents
authorized_docs = node_processor.postprocess_nodes(documents)
unauthorized_docs = node_processor.get_unauthorized_nodes()

if len(authorized_docs):
    print(f"User: '{user}' has access to the next files in folder '{rbac_fid}'")
    for docs in authorized_docs:
        file_id = docs.metadata.get(PangeaMetadataKeys.GDRIVE_FILE_ID, "")
        name = docs.metadata.get(PangeaMetadataKeys.FILE_NAME, "")
        print(f"id: {file_id:44} filename: {name}.")
else:
    print(f"User '{user}' has NO access to any file in folder '{rbac_fid}'")

if len(unauthorized_docs):
    print(f"\nUser '{user}' has NO access to the next files in folder '{rbac_fid}'")
    for docs in unauthorized_docs:
        file_id = docs.metadata.get(PangeaMetadataKeys.GDRIVE_FILE_ID, "")
        name = docs.metadata.get(PangeaMetadataKeys.FILE_NAME, "")
        print(f"id: {file_id:44} filename: {name}.")
else:
    print(f"\nUser '{user}' has access to all the files in folder '{rbac_fid}'")
