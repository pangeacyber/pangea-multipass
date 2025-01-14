# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

import os

from pangea_multipass import (GitHubProcessor, GitHubReader,
                              PangeaMetadataKeys, get_document_metadata)

# Ingestion time
admin_token = os.getenv("GITHUB_ADMIN_TOKEN")
assert admin_token

reader = GitHubReader(admin_token)
documents = reader.load_data()
print(f"Loaded {len(documents)} docs:")

for doc in documents:
    print(doc.metadata.get(PangeaMetadataKeys.FILE_NAME), "")

# Inference time
user_token = os.getenv("GITHUB_USER_TOKEN")
assert user_token

processor = GitHubProcessor(user_token, get_document_metadata)
authorized_docs = processor.filter(documents)

print(f"\nAuthorized docs: {len(authorized_docs)}")
for doc in authorized_docs:
    print(doc.metadata.get(PangeaMetadataKeys.FILE_NAME), "")
