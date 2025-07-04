# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

import os

from pangea_multipass import GitHubReader, PangeaMetadataKeys
from pangea_multipass_llama_index import LlamaIndexGitHubProcessor, from_multipass

# Ingestion time
admin_token = os.getenv("GITHUB_ADMIN_TOKEN")
assert admin_token

reader = GitHubReader(admin_token)
print("Loading data...")
documents = reader.load_data()
print(f"Loaded {len(documents)} docs:")

# Convert documents to Llama Index format
documents = from_multipass(documents)  # type: ignore
for doc in documents:
    print(doc.metadata.get(PangeaMetadataKeys.FILE_NAME), "")

# Inference time


username = os.getenv("GITHUB_USERNAME")
assert username, "GITHUB_USERNAME is not set"

processor = LlamaIndexGitHubProcessor(admin_token, username=username)
authorized_docs = processor.filter(documents)  # type: ignore

print(f"\nAuthorized docs: {len(authorized_docs)}")
for d in authorized_docs:
    print(d.metadata.get(PangeaMetadataKeys.FILE_NAME), "")
