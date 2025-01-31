# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

import os
import warnings
from typing import List

from llama_index.core import Document
from llama_index.readers.jira import JiraReader
from pangea_multipass import JiraAuth, JiraME, PangeaMetadataKeys, enrich_metadata
from pangea_multipass_llama_index import LIDocument, LIDocumentReader

# Suppress specific warning
warnings.filterwarnings("ignore", message='Field "model_name" has conflict with protected namespace')


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


documents = jira_read_docs()

# Inference
from pangea_multipass_llama_index import LlamaIndexJiraProcessor

# Create JIRA filter
jira_user_token = os.getenv("JIRA_USER_TOKEN")
assert jira_user_token
jira_user_email = os.getenv("JIRA_USER_EMAIL")
assert jira_user_email
jira_url = os.getenv("JIRA_BASE_URL")
assert jira_url

jira_processor = LlamaIndexJiraProcessor(JiraAuth(jira_user_email, jira_user_token, jira_url))
authorized_docs = jira_processor.filter(documents)

print(f"\nAuthorized issues: {len(authorized_docs)}")
for doc in authorized_docs:
    print(f"\t{doc.metadata.get(PangeaMetadataKeys.JIRA_ISSUE_ID, '')}")
