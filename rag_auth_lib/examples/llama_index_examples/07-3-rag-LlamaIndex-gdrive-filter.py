# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

from llama_index.readers.google import GoogleDriveReader
from llama_index.llms.bedrock import Bedrock
from llama_index.embeddings.bedrock import BedrockEmbedding
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core import Settings
import os
from google.oauth2.credentials import Credentials
from typing import List
import warnings

from pangea_auth_core import GDriveME, GDriveAPI, enrich_metadata
from pangea_auth_llama_index import LIDocumentReader, get_doc_id


# Suppress specific warning
warnings.filterwarnings("ignore", message='Field "model_name" has conflict with protected namespace')

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

# import logging
# import sys

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
# logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))


# Initialize LLM, anthropic deployed on bedrock
llm = Bedrock(
    model="anthropic.claude-3-5-sonnet-20240620-v1:0",
    profile_name="dev",
    region_name="us-west-2",
    temperature=0.5,
    max_tokens=512,
)

# Initialize Embedding model, amazon titan deployed on bedrock
embed_model = BedrockEmbedding(model="amazon.titan-embed-g1-text-02", region_name="us-west-2", profile_name="dev")

# Set up the models
Settings.llm = llm
Settings.embed_model = embed_model

# Set up chunking parameters
Settings.chunk_size = 1000
Settings.chunk_overlap = 100


def google_drive_read_docs() -> List:
    print("Loading Google Drive docs...")
    # Google Drive Data Ingestion
    credentials_filepath = os.path.abspath("../../credentials.json")

    # Sample folder data folder owned by apurv@gondwana.cloud https://drive.google.com/drive/u/1/folders/1Kj77oi2QGEOPKcIo_hKZPiHDJyKKFVgR
    rbac_fid = "1Kj77oi2QGEOPKcIo_hKZPiHDJyKKFVgR"

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
    gdrive_me = GDriveME(creds, {}, get_doc_id)
    enrich_metadata(documents, [gdrive_me], reader=LIDocumentReader())
    # Finish metadata enrichement

    return documents


# Load data from Gdrive or from the disk
PERSIST_DIR = "./storage/rbac/llamaindex/gdrive"
if not os.path.exists(PERSIST_DIR):
    # Load documents
    documents = google_drive_read_docs()

    print("Create and save index...")
    index = VectorStoreIndex.from_documents(documents)
    # store it for later
    index.storage_context.persist(persist_dir=PERSIST_DIR)
else:
    # load the existing index
    storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
    index = load_index_from_storage(storage_context)  # type: ignore


# Inference
from pangea_auth_llama_index import NodePostprocessorMixer, LlamaIndexGDriveProcessor

# Create GDrive filter
credentials_filepath = os.path.abspath("../../credentials.json")
creds = GDriveAPI.get_user_credentials(credentials_filepath, scopes=SCOPES)

node_processor = NodePostprocessorMixer([LlamaIndexGDriveProcessor(creds)])
metadata_filters = node_processor.get_filter()

# Using filters
query_engine = index.as_query_engine(similarity_top_k=10, streaming=True, filters=metadata_filters)
retriever = index.as_retriever(similarity_top_k=10)


# Inference pipeline
while True:
    user_prompt = input("Enter your question:")

    nodes = retriever.retrieve(user_prompt)
    count = len(node_processor.get_unauthorized_nodes())
    count_authorized = len(node_processor.get_authorized_nodes())

    answer = query_engine.query(user_prompt)
    # print("Assistant: ", answer)
    answer.print_response_stream()

    print("\n=================\n")
    print(
        f"\nWarning: This answer could be inaccurate as its missing context from {count} out of {len(nodes)} data sources. Include {count_authorized} sources."
    )
    print("\n++++++++++++++++++")
