# Ingestion time
import os

from pangea_multipass import GitLabProcessor, GitLabReader, get_document_metadata

token = os.getenv("GITLAB_ADMIN_TOKEN")
assert token

username = os.getenv("GITLAB_USERNAME")
assert username

reader = GitLabReader(token=token, page_size=10)
files = reader.load_data()
print(f"Loaded {len(files)} files.")


# Inference time
processor = GitLabProcessor(admin_token=token, username=username, get_node_metadata=get_document_metadata)

authorized_files = processor.filter(files)
print(f"User '{username}' has access to {len(authorized_files)} files.")
