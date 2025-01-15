# Pangea Multipass: Your Authorization Helper

Pangea Multipass is a Python library for checking user access to upstream data sources.

In practice, you can use it to check if a specific user has access to a file in a Google Drive, a ticket in Jira, or a page in Confluence. In concept, we've built this library to be extensible to eventually support Slack channels, GitHub repositories, Salesforce opportunities, and more. 

We originally built this to support our customers' Retrieval-Augmented Generation (RAG) applications to mitigate data leaks. In a RAG architecture, the application inserts additional context at inference time. If you don't check the user's authorization to that context, you could inadvertently leak sensitive information. 

While this is useful in AI/LLM apps, we've abstracted this to work independently so you can use it in any app.
