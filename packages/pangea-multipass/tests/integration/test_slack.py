import os
import unittest

from pangea_multipass import SlackProcessor, SlackReader, get_document_metadata

token = os.getenv("SLACK_ADMIN_TOKEN") or ""
user_email = os.getenv("SLACK_USER_EMAIL") or ""

_TOTAL_FILES = 12
_AUTHORIZED_FILES = 7
_AUTHORIZED_CHANNELS = 3


class TestSlack(unittest.TestCase):
    def setUp(self) -> None:
        assert token
        assert user_email

    def test_slack(self) -> None:
        reader = SlackReader(token=token, max_messages=2)
        documents = reader.load_data()
        assert len(documents) == _TOTAL_FILES

        processor = SlackProcessor(token=token, get_node_metadata=get_document_metadata, user_email=user_email)
        filter = processor.get_filter()
        assert len(filter.value) == _AUTHORIZED_CHANNELS

        filtered_docs = processor.filter(nodes=documents)
        assert len(filtered_docs) == _AUTHORIZED_FILES
