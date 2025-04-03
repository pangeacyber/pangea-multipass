# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

import os

from pangea_multipass import GitHubReader, PangeaMetadataKeys
from pangea_multipass_langchain import LangChainGitHubFilter, from_multipass

# Ingestion time
admin_token = os.getenv("GITHUB_ADMIN_TOKEN")
assert admin_token

reader = GitHubReader(admin_token)
mp_documents = reader.load_data()
print(f"Loaded {len(mp_documents)} docs:")

# Convert documents to LangChain format
documents = from_multipass(mp_documents)
for doc in documents:
    print(doc.metadata.get(PangeaMetadataKeys.FILE_NAME), "")

# Inference time
user_token = os.getenv("GITHUB_USER_TOKEN")
assert user_token

username = "bob_example"

processor = LangChainGitHubFilter(user_token, username=username)
authorized_docs = processor.filter(documents)

print(f"\nAuthorized docs: {len(authorized_docs)}")
for doc in authorized_docs:
    print(doc.metadata.get(PangeaMetadataKeys.FILE_NAME), "")
