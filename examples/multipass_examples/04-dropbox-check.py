import os

from pangea_multipass import DropboxAPI, DropboxReader, OauthFlow, data_load, data_save
from requests.exceptions import HTTPError

app_key = os.getenv("DROPBOX_APP_KEY")
assert app_key
app_secret = os.getenv("DROPBOX_APP_SECRET")
assert app_secret


# File to store tokens
DROPBOX_TOKEN_FILE = "dropbox_tokens.json"

if not os.path.exists(DROPBOX_TOKEN_FILE):
    flow = OauthFlow(
        auth_url=DropboxAPI.AUTH_URL, token_url=DropboxAPI.TOKEN_URL, client_id=app_key, client_secret=app_secret
    )
    tokens = flow.run()
else:
    tokens = data_load(DROPBOX_TOKEN_FILE)
    access_token = OauthFlow.refresh_access_token(
        url=DropboxAPI.TOKEN_URL, refresh_token=tokens["refresh_token"], client_id=app_key, client_secret=app_secret
    )
    tokens.update(access_token)

data_save(DROPBOX_TOKEN_FILE, tokens)
access_token = tokens["access_token"]
reader = DropboxReader(access_token, page_size=4)
page = 0
documents = []

try:
    while reader.has_more:
        docs = reader.load_data()
        documents.extend(docs)
        page += 1
        print(f"Loaded page: {page}. Docs: {len(docs)}")

except HTTPError as e:
    if e.response:
        print(e.response.text)
    else:
        print(e)


print(f"Loaded {len(documents)} docs")
