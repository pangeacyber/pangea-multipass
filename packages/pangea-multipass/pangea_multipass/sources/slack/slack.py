from typing import Any, Callable, Generic, List, Tuple

import requests
from pangea_multipass.core import (FilterOperator, MetadataFilter,
                                   PangeaGenericNodeProcessor,
                                   PangeaMetadataKeys, PangeaMetadataValues, T)
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

class SlackAPI:

    @staticmethod
    def list_channels(token: str):
        """
        List all channels the authenticated user has access to.
        """

        client = WebClient(token=token)
        try:
            response = client.conversations_list(types="public_channel,private_channel")
            channels = response.get('channels', [])
            return channels
        except SlackApiError as e:
            print(f"Error listing channels: {e.response['error']}")
            return []


class SlackProcessor(PangeaGenericNodeProcessor, Generic[T]):
    _channels_id_cache: dict[tuple, bool] = {}
    _token: str

    def __init__(self, token: str, get_node_metadata: Callable[[T], dict[str, Any]]):
        super().__init__()
        self._token = token
        self._channels_id_cache = {}
        self.get_node_metadata = get_node_metadata

    def _has_access(self, metadata: dict[str, Any]) -> bool:
        """Check if the authenticated user has access to a channel."""

        channel_id = metadata.get(PangeaMetadataKeys.SLACK_CHANNEL_ID, None)
        if channel_id is None:
            raise KeyError(f"Invalid metadata key: {PangeaMetadataKeys.SLACK_CHANNEL_ID}")

        if not self._channels_id_cache:
            self._load_channels_id_cache()

        return self._channels_id_cache.get(channel_id, False)


    def filter(
        self,
        nodes: List[T],
    ) -> List[T]:
        """Filter Slack channels by access permissions.

        Args:
            nodes (List[T]): List of nodes to process.

        Returns:
            List[Any]: Nodes that have authorized access.
        """

        filtered: List[T] = []
        for node in nodes:
            if self._is_authorized(node):
                filtered.append(node)
        return filtered

    def get_filter(
        self,
    ) -> MetadataFilter:
        """Generate a filter based on accessible Slack channel IDs.

        Returns:
            MetadataFilter: Filter for Slack channel IDs.
        """

        if not self._channels_id_cache:
            self._load_channels_id_cache()

        channels = list(self._channels_id_cache.keys())

        return MetadataFilter(
            key=PangeaMetadataKeys.SLACK_CHANNEL_ID, value=channels, operator=FilterOperator.IN
        )

    def _load_channels_id_cache(self):
        channels = SlackAPI.list_channels(self._token)

        for channel in channels:
            self._channels_id_cache[channel['id']] = True

    def _is_authorized(self, node: T) -> bool:
        metadata = self.get_node_metadata(node)
        return metadata[PangeaMetadataKeys.DATA_SOURCE] == PangeaMetadataValues.DATA_SOURCE_SLACK and self._has_access(
            metadata
        )
