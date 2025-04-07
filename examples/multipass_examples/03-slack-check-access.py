# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

import logging
import os

from pangea_multipass import SlackReader
from pangea_multipass.utils import set_logger_to_stdout

set_logger_to_stdout("multipass", logging.INFO)

admin_token = os.getenv("SLACK_ADMIN_TOKEN")
assert admin_token

reader = SlackReader(token=admin_token)
documents = reader.load_data(max_messages_per_channel=1000)
print(f"Loaded {len(documents)} messages.")

# Inference time
from pangea_multipass import SlackProcessor, get_document_metadata

user_email = os.getenv("SLACK_USER_EMAIL")
assert user_email

processor = SlackProcessor(token=admin_token, get_node_metadata=get_document_metadata, user_email=user_email)
filter = processor.get_filter()
print("User has access to channel ids:")
for id in filter.value:
    print(f"\t{id}")

filtered_docs = processor.filter(nodes=documents)
print(f"User has access to {len(filtered_docs)} messages")
