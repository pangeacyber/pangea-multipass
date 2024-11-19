# Copyright 2021 Pangea Cyber Corporation
# Author: Pangea Cyber Corporation

import boto3
from langchain_aws import ChatBedrock
from langchain_aws import BedrockEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_google_community import GoogleDriveLoader
from langchain.document_loaders import ConfluenceLoader
from pathlib import Path
import os
from io import BytesIO
from typing import List
from pangea_auth_core import GDriveME, enrich_metadata, GDriveAPI, ConfluenceME
from google.oauth2.credentials import Credentials
from pangea_auth_langchain import LangChainDocumentReader, DocumentFilterMixer, get_doc_id, LangChainConfluenceFilter, ConfluenceAuth


# Initialization
bedrock_client = boto3.client("bedrock-runtime", region_name="us-west-2")
model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
model_kwargs = {
    "max_tokens": 512,
    "temperature": 0.5,
}

## Setup the LLM paramaters
llm = ChatBedrock(
    client=bedrock_client,
    model_id=model_id,
    model_kwargs=model_kwargs,
)

## Setup the Embedding model paramaters
embedding_model = BedrockEmbeddings(model_id="amazon.titan-embed-g1-text-02", client=bedrock_client)


class TextLoader():
    file: BytesIO
    
    def __init__(self, file):
        self.file = file

    def load(self) -> List[Document]:
        return [Document(page_content=self.file.read().decode("utf-8"))]

## Data ingestion pipeline

def load_gdrive_documents() -> List[Document]:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = ""
    # Google Drive Data Ingestion
    admin_token_filepath = "admin_access_token.json"

    loader = GoogleDriveLoader(
        folder_id="1Kj77oi2QGEOPKcIo_hKZPiHDJyKKFVgR",
        token_path=Path(admin_token_filepath),
        credentials_path=Path("../../credentials.json"),
        recursive=True,
        load_extended_metadata=True,
        file_loader_cls=TextLoader,
    )

    docs = loader.load()    
    print(f"GDrive docs loaded: {len(docs)}.")

    # Metadata enricher library
    SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/drive.metadata.readonly",
    ]
    creds = Credentials.from_authorized_user_file(admin_token_filepath, SCOPES)
    gdrive_me = GDriveME(creds, {})
    enrich_metadata(docs, [gdrive_me], reader=LangChainDocumentReader())
    # Finish metadata enrichement
    return docs 


def confluence_read_docs() -> List[Document]:
    """Fetch all documents from Confluence using ConfluenceLoader."""

    token = os.getenv("CONFLUENCE_ADMIN_TOKEN")
    assert token
    email = os.getenv("CONFLUENCE_ADMIN_EMAIL")
    assert email
    url = os.getenv("CONFLUENCE_BASE_URL")
    assert url

    confluence_space_key = "~71202041f9bfec117041348629ccf3e3c751b3"
    # confluence_space_id = 393230

    # Create a ConfluenceReader instance
    print("Loading Confluence docs...")
    loader = ConfluenceLoader(
        url=url,
        username=email,
        api_key=token,
        space_key=confluence_space_key,
    )
    documents = loader.load()

    # Enrich metadata process
    print(f"Processing {len(documents)} Confluence docs...")
    confluence_me = ConfluenceME()
    enrich_metadata(documents, [confluence_me], reader=LangChainDocumentReader())

    return documents


PERSIST_DIR = "./storage/data/langchain/faiss_index"
if not os.path.exists(PERSIST_DIR):
    # gdrive_docs = load_gdrive_documents()
    confluence_docs = confluence_read_docs()
    docs = confluence_docs
    # docs = gdrive_docs + jira_docs

    # Initialize the vector store https://faiss.ai
    vectorstore = FAISS.from_documents(documents=docs, embedding=embedding_model)

    # Store to file system
    vectorstore.save_local(PERSIST_DIR)
else:
    vectorstore = FAISS.load_local(folder_path=PERSIST_DIR, embeddings=embedding_model, allow_dangerous_deserialization=True)


## Inference pipeline

from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from pangea_auth_langchain import LangChainGDriveFilter

# Create GDrive filter
credentials_filepath = os.path.abspath("../../credentials.json")
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]
creds = GDriveAPI.get_user_credentials(credentials_filepath, scopes=SCOPES)
gdrive_filter = LangChainGDriveFilter(creds)

# Create Confluence filter
confluence_user_token = os.getenv("CONFLUENCE_USER_TOKEN")
assert confluence_user_token
confluence_user_email = os.getenv("CONFLUENCE_USER_EMAIL")
assert confluence_user_email
confluence_url = os.getenv("CONFLUENCE_BASE_URL")
assert confluence_url
confluence_filter = LangChainConfluenceFilter(
    ConfluenceAuth(confluence_user_email, confluence_user_token, confluence_url),
)

# Create mixed filter
filter_mixer = DocumentFilterMixer(document_filters=[gdrive_filter, confluence_filter])

# Use indexed store as a reteriver to create qa chain
retriever = vectorstore.as_retriever()

# Prompt template with System, Context and User prompt
template = """"System: Answer the following question based only on the provided context:

<context>
{context}
</context>

Question: {input}
"""
prompt = ChatPromptTemplate.from_template(template)

# Document chain using the LLM and prompt template
qa_chain = create_stuff_documents_chain(llm, prompt)

while True:
    user_prompt = input("Enter your question: ")
    similar_docs = retriever.invoke(user_prompt)

    print(f"similar_docsilar: {len(similar_docs)}")

    filtered_docs = filter_mixer.filter(similar_docs)
    print(f"filtered_docs: {len(filtered_docs)}")
    count = len(filter_mixer.get_unauthorized_documents())

    response = qa_chain.invoke({"input": user_prompt, "context": filtered_docs})
    print(f"\n{response}")
    print("\n=================")
    print(
        f"Warning: This answer could be inaccurate as its missing context from {count} out of {len(similar_docs)} data sources. Include {len(filtered_docs)} sources."
    )
    print("=================\n")