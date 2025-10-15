"""DynamoDB client wrapper with enhanced functionality.

This module provides a high-level wrapper around the boto3 DynamoDB client
with improved type safety, error handling, and convenience methods.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Unpack

import boto3
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from botocore.config import Config

if TYPE_CHECKING:
    from collections.abc import Iterator

    from mypy_boto3_dynamodb.client import DynamoDBClient
    from mypy_boto3_dynamodb.type_defs import QueryInputPaginateTypeDef

logger = logging.getLogger(__name__)


class FloatTypeDeserializer(TypeDeserializer):
    """Custom deserializer that converts number to float/int rather than Decimal."""

    def _deserialize_n(self, value: Any) -> int | float:
        data = float(value)
        return int(data) if data.is_integer() else data


class DynamoDBWrapper:
    _serializer = TypeSerializer()
    _deserializer = FloatTypeDeserializer()
    _default_config = Config(
        read_timeout=60,
        connect_timeout=60,
        region_name="us-east-1",
        retries={"max_attempts": 5},
    )

    def __init__(self, client: DynamoDBClient) -> None:
        self._client = client

    @classmethod
    def us_east1_client(cls) -> DynamoDBWrapper:
        return cls(boto3.client("dynamodb", config=cls._default_config))

    @property
    def client(self) -> DynamoDBClient:
        """Get the underlying DynamoDB client."""
        return self._client

    def query(
        self, **kwargs: Unpack[QueryInputPaginateTypeDef]
    ) -> Iterator[dict[str, Any]]:
        paginator = self._client.get_paginator("query")
        response_iterator = paginator.paginate(**kwargs)
        for page in response_iterator:
            items = page.get("Items", [])
            for item in items:
                yield self._deserialize(item)

    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        """Serialize a Python dictionary to DynamoDB format."""
        return {k: self._serializer.serialize(v) for k, v in row.items()}

    def _deserialize(self, row: dict[str, Any]) -> dict[str, Any]:
        """Deserialize a DynamoDB item to Python format."""
        return {k: self._deserializer.deserialize(v) for k, v in row.items()}
