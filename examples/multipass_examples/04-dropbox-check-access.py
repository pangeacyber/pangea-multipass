import os

from pangea_multipass import DropboxClient, DropboxReader, OauthFlow, data_load, data_save
from requests.exceptions import HTTPError

app_key = os.getenv("DROPBOX_APP_KEY")
assert app_key

# File to store tokens
DROPBOX_TOKEN_FILE = "dropbox_tokens.json"

if not os.path.exists(DROPBOX_TOKEN_FILE):
    code_verifier, code_challenge = OauthFlow.generate_pkce_pair()

    flow = OauthFlow(
        auth_url=DropboxClient.AUTH_URL,
        token_url=DropboxClient.TOKEN_URL,
        client_id=app_key,
    )
    tokens = flow.run_pkce(code_verifier=code_verifier, code_challenge=code_challenge)
else:
    tokens = data_load(DROPBOX_TOKEN_FILE)
    assert tokens
    access_token = OauthFlow.refresh_access_token(
        url=DropboxClient.TOKEN_URL, refresh_token=tokens["refresh_token"], client_id=app_key
    )
    tokens.update(access_token)

data_save(DROPBOX_TOKEN_FILE, tokens)
access_token = tokens["access_token"]
reader = DropboxReader(access_token)
documents = []

print("Loading documents from Dropbox...")
try:
    documents = reader.load_data()

except HTTPError as e:
    if e.response:
        print(e.response.text)
    else:
        print(e)

print(f"Loaded {len(documents)} docs")


# Inference time
from pangea_multipass import DropboxProcessor, get_document_metadata

user_email = os.getenv("DROPBOX_USER_EMAIL")
assert user_email

processor = DropboxProcessor(access_token, user_email=user_email, get_node_metadata=get_document_metadata)
print("Filtering authorized documents...")
authorized_docs = processor.filter(documents)

print(f"Authorized docs: {len(authorized_docs)}")
