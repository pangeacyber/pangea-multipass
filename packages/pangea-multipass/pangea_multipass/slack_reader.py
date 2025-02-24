from typing import Any, List, Optional, Tuple

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .core import MultipassDocument, PangeaMetadataKeys, PangeaMetadataValues, generate_id
from .sources import SlackAPI


class SlackReader:
    _token: str
    _client: WebClient
    _channel_id: Optional[str] = None
    _latest_ts: Optional[str] = None
    _has_more_messages: bool = True

    def __init__(self, token: str) -> None:
        self._token = token
        self._client = WebClient(token=self._token)
        self._restart()

    def load_data(self, max_messages_per_channel: int = 1000) -> List[MultipassDocument]:
        """Load all messages from all channels"""
        documents: List[MultipassDocument] = []
        channels = SlackAPI.list_channels(token=self._token)
        for channel in channels:
            messages, _, _ = self._fetch_messages(channel["id"], max_messages_per_channel)
            documents.extend(self._process_messages(messages, channel))

        return documents

    def get_channels(self) -> List[dict[str, Any]]:
        """Get all the channels token has access to"""
        return SlackAPI.list_channels(token=self._token)

    def read_messages(self, channel: dict, page_size: int = 100) -> List[MultipassDocument]:
        """
        Read messages from a given channel
        If the channel is different from the last one, it will restart the reader.
        If the channel is the same, it will continue reading from the last message.
        """
        new_channel_id = channel["id"]
        if self._channel_id is None or new_channel_id != self._channel_id:
            self._restart()
            self._channel_id = new_channel_id

        if self._channel_id is None:
            raise Exception("Channel ID is not set")

        messages, latest, more_messages = self._fetch_messages(self._channel_id, page_size, self._latest_ts)
        self._latest_ts = latest
        self._has_more_messages = more_messages
        return self._process_messages(messages, channel)

    @property
    def has_more_messages(self) -> bool:
        """Check if there are more messages to read"""
        return self._has_more_messages

    def _restart(self) -> None:
        self._channel_id = None
        self._latest_ts = None
        self._has_more_messages = True

    def _process_messages(self, messages: list[dict[str, Any]], channel: dict) -> List[MultipassDocument]:
        """Process the messages and create the documents"""
        channel_id = channel["id"]
        channel_name = channel["name"]
        documents: List[MultipassDocument] = []

        for message in messages:
            subtype = message.get("subtype", "")
            # Just ignore the channel join messages
            if subtype == "channel_join":
                continue
            user = message.get("user", "")
            text = message.get("text", "")
            ts = message.get("ts", "")
            metadata = {
                PangeaMetadataKeys.SLACK_CHANNEL_ID: channel_id,
                PangeaMetadataKeys.SLACK_CHANNEL_NAME: channel_name,
                PangeaMetadataKeys.SLACK_TIMESTAMP: ts,
                PangeaMetadataKeys.SLACK_USER: user,
                PangeaMetadataKeys.DATA_SOURCE: PangeaMetadataValues.DATA_SOURCE_SLACK,
            }
            documents.append(MultipassDocument(id=generate_id(), content=text, metadata=metadata))  # type: ignore[arg-type]

        return documents

    def _fetch_messages(
        self, channel_id: str, max_messages: int = 1000, latest: Optional[str] = None
    ) -> Tuple[List[dict[str, Any]], Optional[str], bool]:
        """
        Fetch the messages from a given channel.
        """

        page_size = 100
        page_size = page_size if page_size < max_messages else max_messages
        messages: List[dict[str, Any]] = []
        more_messages = True

        try:
            while len(messages) < max_messages:
                response = self._client.conversations_history(channel=channel_id, latest=latest, limit=page_size)
                new_messages: List[dict[str, Any]] = response.get("messages", [])
                messages.extend(new_messages)

                if not new_messages:
                    more_messages = False
                    break

                message = new_messages[-1]
                latest = message.get("ts", "")

                # We could delete this check and do another request and it should return an empty list.
                if len(new_messages) < page_size:
                    more_messages = False
                    break

                page_size = page_size if (max_messages - len(messages)) > page_size else (max_messages - len(messages))

        except SlackApiError as e:
            raise Exception(f"Error fetching messages for channel {channel_id}: {e.response['error']}")

        return (messages, latest, more_messages)
