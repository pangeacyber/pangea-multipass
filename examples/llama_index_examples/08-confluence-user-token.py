# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

import os
from typing import List

from llama_index.readers.confluence import ConfluenceReader
from pangea_multipass import ConfluenceAuth, ConfluenceME, PangeaMetadataKeys, enrich_metadata
from pangea_multipass_llama_index import LIDocument, LIDocumentReader

# Fetch documents from Confluence
confluence_space_key = "~71202041f9bfec117041348629ccf3e3c751b3"
confluence_space_id = 393230

admin_token = os.getenv("CONFLUENCE_ADMIN_TOKEN")
assert admin_token
admin_email = os.getenv("CONFLUENCE_ADMIN_EMAIL")
assert admin_email
url = os.getenv("CONFLUENCE_BASE_URL")
assert url


def confluence_read_docs() -> List[LIDocument]:
    """Fetch all documents from Confluence using ConfluenceReader."""

    # Create a ConfluenceReader instance
    print("Loading Confluence docs...")
    reader = ConfluenceReader(
        base_url=url,
        user_name=admin_email,
        password=admin_token,
    )
    documents: List[LIDocument] = reader.load_data(space_key=confluence_space_key, include_attachments=True)

    # Enrich metadata process
    print(f"Processing {len(documents)} Confluence docs...")
    confluence_me = ConfluenceME()
    enrich_metadata(documents, [confluence_me], reader=LIDocumentReader())

    return documents


documents = confluence_read_docs()
print(f"Loaded {len(documents)} pages.")

# Inference
from pangea_multipass_llama_index import LlamaIndexConfluenceProcessor

user_token = os.getenv("CONFLUENCE_USER_TOKEN")
assert user_token
user_email = os.getenv("CONFLUENCE_USER_EMAIL")
assert user_email
url = os.getenv("CONFLUENCE_BASE_URL")
assert url

# Create Confluence filter with user token
confluence_processor = LlamaIndexConfluenceProcessor(ConfluenceAuth(user_email, user_token, url))

authorized_docs = confluence_processor.filter(documents)

print(f"\nAuthorized pages: {len(authorized_docs)}")
for doc in authorized_docs:
    print(f"\t{doc.metadata.get(PangeaMetadataKeys.CONFLUENCE_PAGE_ID, '')}")
    print(f"\t{doc.metadata.get(PangeaMetadataKeys.FILE_NAME, '')}")
