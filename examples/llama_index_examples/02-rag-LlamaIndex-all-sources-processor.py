# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

import os
import warnings
from typing import List

from google.oauth2.credentials import Credentials
from llama_index.core import Document, Settings, StorageContext, VectorStoreIndex, load_index_from_storage
from llama_index.embeddings.bedrock import BedrockEmbedding
from llama_index.llms.bedrock import Bedrock
from llama_index.readers.confluence import ConfluenceReader
from llama_index.readers.google import GoogleDriveReader
from llama_index.readers.jira import JiraReader
from pangea_multipass import ConfluenceAuth, ConfluenceME, GDriveAPI, GDriveME, JiraAuth, JiraME, enrich_metadata
from pangea_multipass_llama_index import LIDocument, LIDocumentReader

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


def google_drive_read_docs() -> List[LIDocument]:
    print("Loading Google Drive docs...")
    # Google Drive Data Ingestion
    credentials_filepath = os.path.abspath("../credentials.json")

    # Sample folder data folder owned by apurv@gondwana.cloud https://drive.google.com/drive/u/1/folders/1Kj77oi2QGEOPKcIo_hKZPiHDJyKKFVgR
    gdrive_fid = "1Kj77oi2QGEOPKcIo_hKZPiHDJyKKFVgR"

    # File name for the admin user
    admin_token_filepath = "admin_access_token.json"

    # # Invoke Google /auth endpoint and save he token for later use
    # GDrive.get_and_save_access_token(credentials_filepath, admin_token_filepath, SCOPES)

    # load the documents and create the index
    print("Login to GDrive as admin...")
    gdrive_reader = GoogleDriveReader(
        folder_id=gdrive_fid, token_path=admin_token_filepath, credentials_path=credentials_filepath
    )
    documents: List[LIDocument] = gdrive_reader.load_data(folder_id=gdrive_fid)

    print(f"Processing {len(documents)} docs...")

    # Metadata enricher library
    creds = Credentials.from_authorized_user_file(admin_token_filepath, SCOPES)
    gdrive_me = GDriveME(creds, {})
    enrich_metadata(documents, [gdrive_me], reader=LIDocumentReader())
    # Finish metadata enrichement

    return documents


# Fetch documents from Confluence
confluence_space_key = "~71202041f9bfec117041348629ccf3e3c751b3"
confluence_space_id = 393230


def confluence_read_docs() -> List[LIDocument]:
    """Fetch all documents from Confluence using ConfluenceReader."""

    token = os.getenv("CONFLUENCE_ADMIN_TOKEN")
    assert token
    email = os.getenv("CONFLUENCE_ADMIN_EMAIL")
    assert email
    url = os.getenv("CONFLUENCE_BASE_URL")
    assert url

    # Create a ConfluenceReader instance
    print("Loading Confluence docs...")
    reader = ConfluenceReader(
        base_url=url,
        user_name=email,
        password=token,
    )
    documents: List[LIDocument] = reader.load_data(space_key=confluence_space_key, include_attachments=True)

    # Enrich metadata process
    print(f"Processing {len(documents)} Confluence docs...")
    confluence_me = ConfluenceME()
    enrich_metadata(documents, [confluence_me], reader=LIDocumentReader())

    return documents


def jira_load_data(reader: JiraReader, query: str = "") -> List[Document]:
    max_results = 100
    start_at = 0
    keep_iterating = True
    all_documents: List[Document] = []

    while keep_iterating:
        documents = reader.load_data(query, start_at=start_at, max_results=max_results)
        all_documents.extend(documents)
        l = len(documents)
        start_at = start_at + l
        keep_iterating = l >= max_results

    return all_documents


def jira_read_docs() -> List[LIDocument]:
    # Jira credentials and base URL
    JIRA_BASE_URL = os.getenv("JIRA_BASE_URL") or ""
    assert JIRA_BASE_URL
    jira_admin_email = os.getenv("JIRA_ADMIN_EMAIL") or ""
    assert jira_admin_email
    jira_api_token = os.getenv("JIRA_ADMIN_TOKEN") or ""
    assert jira_api_token

    # Initialize LlamaIndex JiraReader
    print("Loading Jira docs...")
    jira_reader = JiraReader(server_url=JIRA_BASE_URL, email=jira_admin_email, api_token=jira_api_token)

    documents = jira_load_data(jira_reader, "")

    # Metadata enricher library
    print(f"Processing {len(documents)} Jira docs...")
    jira_me = JiraME(JIRA_BASE_URL, jira_admin_email, jira_api_token)
    enrich_metadata(documents, [jira_me], reader=LIDocumentReader())

    return documents


# Load data from Gdrive or from the disk
PERSIST_DIR = "./storage/rbac/llamaindex/all_sources"
if not os.path.exists(PERSIST_DIR):
    # Load documents
    gdrive_documents = google_drive_read_docs()
    confluence_documents = confluence_read_docs()
    jira_documents = jira_read_docs()

    # Combine documents
    documents = gdrive_documents + confluence_documents + jira_documents

    print("Create and save index...")
    index = VectorStoreIndex.from_documents(documents)
    # store it for later
    index.storage_context.persist(persist_dir=PERSIST_DIR)
else:
    # load the existing index
    print("Loading index...")
    storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
    index = load_index_from_storage(storage_context)


# Inference

from pangea_multipass_llama_index import (
    LlamaIndexConfluenceProcessor,
    LlamaIndexGDriveProcessor,
    LlamaIndexJiraProcessor,
    NodePostprocessorMixer,
)

# Create GDrive filter
credentials_filepath = os.path.abspath("../credentials.json")
print("Login to GDrive as user...")
creds = GDriveAPI.get_user_credentials(credentials_filepath, scopes=SCOPES)
gdrive_processor = LlamaIndexGDriveProcessor(creds)

# Create Confluence filter
confluence_admin_token = os.getenv("CONFLUENCE_ADMIN_TOKEN")
assert confluence_admin_token
confluence_admin_email = os.getenv("CONFLUENCE_ADMIN_EMAIL")
assert confluence_admin_email
confluence_url = os.getenv("CONFLUENCE_BASE_URL")
assert confluence_url
confluence_account_id = os.getenv("CONFLUENCE_USER_ACCOUNT_ID")
assert confluence_account_id
confluence_processor = LlamaIndexConfluenceProcessor(
    ConfluenceAuth(confluence_admin_email, confluence_admin_token, confluence_url), account_id=confluence_account_id
)

# Create JIRA filter
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL") or ""
assert JIRA_BASE_URL
jira_admin_email = os.getenv("JIRA_ADMIN_EMAIL") or ""
assert jira_admin_email
jira_admin_token = os.getenv("JIRA_ADMIN_TOKEN") or ""
assert jira_admin_token
jira_account_id = os.getenv("JIRA_USER_ACCOUNT_ID") or ""
assert jira_account_id
jira_processor = LlamaIndexJiraProcessor(
    JiraAuth(jira_admin_email, jira_admin_token, JIRA_BASE_URL), account_id=jira_account_id
)

# Initialize query engine and the reteriver to send prompts
# query_engine = index.as_query_engine(similarity_top_k=10, streaming=True, filters=metadata_filters)
node_processor = NodePostprocessorMixer(
    [
        gdrive_processor,
        jira_processor,
        confluence_processor,
    ]
)

query_engine = index.as_query_engine(
    streaming=True,
    similarity_top_k=10,
    node_postprocessors=[node_processor],
)

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
