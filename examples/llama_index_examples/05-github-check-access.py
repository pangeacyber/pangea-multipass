# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

import os

from pangea_multipass import GitHubReader, PangeaMetadataKeys
from pangea_multipass_llama_index import LlamaIndexGitHubProcessor, from_multipass

# Ingestion time
admin_token = os.getenv("GITHUB_ADMIN_TOKEN")
assert admin_token

reader = GitHubReader(admin_token)
documents = reader.load_data()
print(f"Loaded {len(documents)} docs:")

# Convert documents to Llama Index format
documents = from_multipass(documents)
for doc in documents:
    print(doc.metadata.get(PangeaMetadataKeys.FILE_NAME), "")

# Inference time
user_token = os.getenv("GITHUB_USER_TOKEN")
assert user_token

username = "bob_example"

processor = LlamaIndexGitHubProcessor(user_token, username=username)
authorized_docs = processor.filter(documents)

print(f"\nAuthorized docs: {len(authorized_docs)}")
for doc in authorized_docs:
    print(doc.metadata.get(PangeaMetadataKeys.FILE_NAME), "")
