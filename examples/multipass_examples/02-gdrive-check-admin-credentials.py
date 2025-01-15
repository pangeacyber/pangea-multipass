# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

import os
import sys
from typing import List

from google.oauth2.credentials import Credentials
from llama_index.readers.google import GoogleDriveReader
from pangea_multipass import (GDriveAPI, GDriveME, PangeaMetadataKeys,
                              enrich_metadata)
from pangea_multipass_llama_index import LIDocumentReader

if len(sys.argv) != 2:
    print(f"usage: {sys.argv[0]} <gdrive_folder_id>")
    exit(1)


SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Sample folder data folder owned by apurv@gondwana.cloud https://drive.google.com/drive/u/1/folders/1Kj77oi2QGEOPKcIo_hKZPiHDJyKKFVgR

# gdrive_fid = "1Kj77oi2QGEOPKcIo_hKZPiHDJyKKFVgR"
gdrive_fid = sys.argv[1]

# File name for the admin user
admin_token_filepath = "admin_access_token.json"


def google_drive_read_docs() -> List:
    print(f"Loading Google Drive docs. Folder ID: {gdrive_fid}.")
    # Google Drive Data Ingestion
    credentials_filepath = os.path.abspath("../credentials.json")

    # Invoke Google /auth endpoint and save the token for later use
    if not os.path.isfile(admin_token_filepath):
        print("Sign in with the admin user account:")
        GDriveAPI.get_and_save_access_token(credentials_filepath, admin_token_filepath, SCOPES)

    # load the documents and create the index
    gdrive_reader = GoogleDriveReader(
        folder_id=gdrive_fid, token_path=admin_token_filepath, credentials_path=credentials_filepath
    )
    documents = gdrive_reader.load_data(folder_id=gdrive_fid)

    print(f"Processing {len(documents)} docs...")

    # Metadata enricher library
    creds = Credentials.from_authorized_user_file(admin_token_filepath, SCOPES)
    gdrive_me = GDriveME(creds, {})
    enrich_metadata(documents, [gdrive_me], reader=LIDocumentReader())
    # Finish metadata enrichement

    return documents


documents = google_drive_read_docs()

# Inference
from pangea_multipass import GDriveAPI
from pangea_multipass_llama_index import (LlamaIndexGDriveProcessor,
                                          NodePostprocessorMixer)

# Create GDrive filter
creds = Credentials.from_authorized_user_file(admin_token_filepath, SCOPES)

# User email to check permissions
user_email = "alice@gondwana.cloud"

gdrive_processor = LlamaIndexGDriveProcessor(creds, user_email=user_email)
node_processor = NodePostprocessorMixer([gdrive_processor])

# Process documents
authorized_docs = node_processor.postprocess_nodes(documents)
unauthorized_docs = node_processor.get_unauthorized_nodes()

if len(authorized_docs):
    print(f"User: '{user_email}' has access to the next files in folder '{gdrive_fid}'")
    for docs in authorized_docs:
        file_id = docs.metadata.get(PangeaMetadataKeys.GDRIVE_FILE_ID, "")
        name = docs.metadata.get(PangeaMetadataKeys.FILE_NAME, "")
        print(f"id: {file_id:44} filename: {name}.")
else:
    print(f"User '{user_email}' has NO access to any file in folder '{gdrive_fid}'")

if len(unauthorized_docs):
    print(f"\nUser '{user_email}' has NO access to the next files in folder '{gdrive_fid}'")
    for docs in unauthorized_docs:
        file_id = docs.metadata.get(PangeaMetadataKeys.GDRIVE_FILE_ID, "")
        name = docs.metadata.get(PangeaMetadataKeys.FILE_NAME, "")
        print(f"id: {file_id:44} filename: {name}.")
else:
    print(f"\nUser '{user_email}' has access to all the files in folder '{gdrive_fid}'")
