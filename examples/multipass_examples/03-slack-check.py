# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

import os
import warnings
from typing import List
from pangea_multipass import SlackReader

# Suppress specific warning
warnings.filterwarnings("ignore", message='Field "model_name" has conflict with protected namespace')

admin_token = os.getenv("SLACK_ADMIN_TOKEN")
assert admin_token

reader = SlackReader(token=admin_token, max_messages=2)
documents = reader.load_data()
print(f"Loaded {len(documents)} messages.")

# for doc in documents:
#     print(doc)


# Inference time
from pangea_multipass import SlackProcessor, get_document_metadata

user_token = os.getenv("SLACK_USER_TOKEN")
assert user_token

processor = SlackProcessor(token=user_token, get_node_metadata=get_document_metadata)
filter = processor.get_filter()
print("User has acess to channel ids:")
for id in filter.value:
    print(f"\t{id}")

filtered_docs = processor.filter(nodes=documents)
print(f"User has access to {len(filtered_docs)} messages")
