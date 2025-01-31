from typing import List

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .core import MultipassDocument, PangeaMetadataKeys, PangeaMetadataValues, generate_id
from .sources import SlackAPI


class SlackReader:
    _token: str
    _client: WebClient
    _max_messages: int

    def __init__(self, token: str, max_messages=1000):
        self._token = token
        self._client = WebClient(token=self._token)
        self._max_messages = max_messages

    def load_data(self) -> List[MultipassDocument]:
        documents: List[MultipassDocument] = []
        channels = SlackAPI.list_channels(token=self._token)
        for channel in channels:
            channel_id = channel["id"]  # type: ignore[index]
            channel_name = channel["name"]  # type: ignore[index]

            # Fetch messages for each channel
            messages = self._fetch_messages(channel["id"])  # type: ignore[index]
            # print(f"Channel has {len(messages)} messages")
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

    def _fetch_messages(self, channel_id: str, max_messages: int = 1000) -> List:
        """
        Fetch the messages from a given channel.
        """

        page_size = 100
        page_size = page_size if page_size < max_messages else max_messages
        messages = []
        total_messages = 0
        latest = None

        try:
            while total_messages < max_messages:
                response = self._client.conversations_history(channel=channel_id, latest=latest, limit=page_size)
                new_messages: List[dict] = response.get("messages", [])
                total_messages += len(new_messages)
                messages.extend(new_messages)

                if not new_messages or len(new_messages) < page_size:
                    break

                message = new_messages[-1]
                latest = message.get("ts", "")
                page_size = (
                    page_size if (max_messages - total_messages) > page_size else (max_messages - total_messages)
                )

        except SlackApiError as e:
            print(f"Error fetching messages for channel {channel_id}: {e.response['error']}")
            return []

        return messages
