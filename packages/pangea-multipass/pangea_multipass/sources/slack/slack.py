import json
import logging
from typing import Any, Callable, Generic, List, Optional

import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from pangea_multipass.core import (
    FilterOperator,
    MetadataFilter,
    PangeaGenericNodeProcessor,
    PangeaMetadataKeys,
    PangeaMetadataValues,
    T,
)


class SlackClient:
    _actor = "slack_client"

    def __init__(self, logger_name: str = "multipass"):
        self.logger = logging.getLogger(logger_name)

    def list_channels(self, token: str) -> List[dict[str, Any]]:
        """
        List all channels the authenticated user has access to.

        Args:
            token (str): Slack token.

        Returns:
            List of channel ids that the authenticated user has access to.
        """

        client = WebClient(token=token)
        try:
            response = client.conversations_list(types="public_channel,private_channel")
            channels: List[dict[str, Any]] = response.get("channels", [])
            return channels
        except SlackApiError as e:
            self._log_error("list_channels", "conversations.list", {}, e.response)
            return []

    def get_channel_members(self, token: str, channel_id: str) -> Optional[List[str]]:
        """
        Retrieve the list of members in a Slack channel.

        Args:
            token (str): Slack token.
            channel_id (str): Channel id to request members.

        Returns:
            List of user IDs in the channel.
        """

        client = WebClient(token=token)
        try:
            response = client.conversations_members(channel=channel_id)
            return response["members"]
        except SlackApiError as e:
            self._log_error("get_channel_members", "conversations.members", {"channel": channel_id}, e.response)
            return None

    def get_all_channels(self, token: str) -> Optional[List[str]]:
        """
        Retrieve all channels in the workspace.

        Args:
            token (str): Slack token

        Returns:
            List of channel IDs.
        """

        client = WebClient(token=token)
        channels: List[dict[str, Any]] = []
        try:
            response = client.conversations_list(types="public_channel,private_channel", limit=1000)
            channels = response.get("channels", [])
            return [channel["id"] for channel in channels]
        except SlackApiError as e:
            self._log_error("get_all_channels", "conversations.list", {}, e.response)
            return None

    def get_user_id(self, token: str, user_email: str) -> Optional[str]:
        """
        Retrieve the Slack user ID for a given email address.

        Args:
            token (str): Slack token.
            user_email (str): User email to request user id.

        Returns:
            User ID or None if the user does not exist.
        """

        client = WebClient(token=token)
        try:
            response = client.users_lookupByEmail(email=user_email)
            return response["user"]["id"]
        except SlackApiError as e:
            self._log_error("get_user_id", "users.lookupByEmail", {"email": user_email}, e.response)
            return None

    def get_channels_for_user(self, token: str, user_id: str, channel_ids: List[str]) -> List[str]:
        """
        Check which channels a user has access to.

        Args:
            token (str): Slack token.
            user_id (str): Slack user id.
            channels_ids (List[str]): Channels id to check access for user_id.

        Returns:
            List of channel IDs the user has access to.
        """
        client = WebClient(token=token)
        accessible_channels = []
        for channel_id in channel_ids:
            try:
                response = client.conversations_members(channel=channel_id)
                members: List[str] = response.get("members", [])
                if user_id in members:
                    accessible_channels.append(channel_id)
            except SlackApiError as e:
                if e.response["error"] == "not_in_channel":
                    continue  # User is not in this channel
                else:
                    self._log_error(
                        "get_channels_for_user", "conversations.members", {"channel": channel_id}, e.response
                    )
                    pass
        return accessible_channels

    def _log_error(self, function_name: str, url: str, data: dict, response: requests.Response):
        self.logger.error(
            json.dumps(
                {
                    "actor": SlackClient._actor,
                    "fn": function_name,
                    "url": url,
                    "data": data,
                    "status_code": response.status_code,
                    "reason": response.reason,
                    "text": response.text,
                }
            )
        )


class SlackProcessor(PangeaGenericNodeProcessor[T], Generic[T]):
    _channels_id_cache: dict[str, bool] = {}
    _token: str
    _user_email: Optional[str] = None
    _user_id: Optional[str] = None

    def __init__(
        self,
        token: str,
        get_node_metadata: Callable[[T], dict[str, Any]],
        user_email: Optional[str] = None,
        logger_name: str = "multipass",
    ):
        super().__init__()
        self._token = token
        self._channels_id_cache = {}
        self.get_node_metadata = get_node_metadata
        self._user_email = user_email
        self._client = SlackClient(logger_name)

    def _has_access(self, metadata: dict[str, Any]) -> bool:
        """Check if the authenticated user has access to a channel."""

        channel_id = metadata.get(PangeaMetadataKeys.SLACK_CHANNEL_ID, None)
        if channel_id is None:
            raise KeyError(f"Invalid metadata key: {PangeaMetadataKeys.SLACK_CHANNEL_ID}")

        if not self._channels_id_cache:
            self._load_channels_from_token()
        else:
            self._load_channels_with_email()

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

        if not self._user_email:
            self._load_channels_from_token()
        else:
            self._load_channels_with_email()

        channels = list(self._channels_id_cache.keys())

        return MetadataFilter(key=PangeaMetadataKeys.SLACK_CHANNEL_ID, value=channels, operator=FilterOperator.IN)

    def check_user_access(self, token: str, channel_id: str, user_email: str) -> bool:
        """
        Check if a user has access to a specific Slack channel.

        Args:
            token (str): Slack token.
            channel_id (srt): ID of the Slack channel.
            user_email (str): Email of the user to check.

        Returns:
            True if the user is a member of the channel, False otherwise.
        """

        user_id = self._client.get_user_id(token, user_email)
        if not user_id:
            return False

        channel_members = self._client.get_channel_members(token, channel_id)
        if channel_members is None:
            return False

        return user_id in channel_members

    def _load_channels_with_email(self) -> None:
        if self._channels_id_cache:
            return

        if not self._user_id and self._user_email is not None:
            self._user_id = self._client.get_user_id(self._token, self._user_email)

        if not self._user_id:
            return

        all_channels = self._client.get_all_channels(self._token)
        if all_channels is None:
            return

        channels = self._client.get_channels_for_user(self._token, user_id=self._user_id, channel_ids=all_channels)
        for channel in channels:
            self._channels_id_cache[channel] = True

    def _load_channels_from_token(self) -> None:
        if self._channels_id_cache:
            return

        for channel in self._client.list_channels(self._token):
            self._channels_id_cache[channel["id"]] = True

    def _is_authorized(self, node: T) -> bool:
        metadata = self.get_node_metadata(node)
        return metadata[PangeaMetadataKeys.DATA_SOURCE] == PangeaMetadataValues.DATA_SOURCE_SLACK and self._has_access(
            metadata
        )
