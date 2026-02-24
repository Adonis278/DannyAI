"""
DynamoDB persistence for Danny AI.
Stores session state, consent flags, call metadata, and conversation logs.

Tables created on first use (for dev/MVP). In production deploy via CloudFormation / CDK.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Table names (overridable via env)
# ---------------------------------------------------------------------------
SESSIONS_TABLE = os.getenv("DYNAMO_SESSIONS_TABLE", "danny_sessions")
CALL_LOG_TABLE = os.getenv("DYNAMO_CALL_LOG_TABLE", "danny_call_log")


class DynamoDBStore:
    """Manages DynamoDB tables for session state and call logging."""

    def __init__(self, region: Optional[str] = None):
        self.region = region or os.getenv("AWS_REGION", "us-west-2")
        self.ddb = boto3.resource("dynamodb", region_name=self.region)
        self._ensure_tables()

    # ------------------------------------------------------------------
    # Table bootstrap (idempotent)
    # ------------------------------------------------------------------
    def _ensure_tables(self):
        """Create tables if they don't exist (dev convenience)."""
        existing = [t.name for t in self.ddb.tables.all()]

        if SESSIONS_TABLE not in existing:
            self._create_table(
                SESSIONS_TABLE,
                key_schema=[{"AttributeName": "session_id", "KeyType": "HASH"}],
                attributes=[{"AttributeName": "session_id", "AttributeType": "S"}],
            )

        if CALL_LOG_TABLE not in existing:
            self._create_table(
                CALL_LOG_TABLE,
                key_schema=[
                    {"AttributeName": "contact_id", "KeyType": "HASH"},
                    {"AttributeName": "timestamp", "KeyType": "RANGE"},
                ],
                attributes=[
                    {"AttributeName": "contact_id", "AttributeType": "S"},
                    {"AttributeName": "timestamp", "AttributeType": "S"},
                ],
            )

    def _create_table(self, name, key_schema, attributes):
        try:
            self.ddb.create_table(
                TableName=name,
                KeySchema=key_schema,
                AttributeDefinitions=attributes,
                BillingMode="PAY_PER_REQUEST",
            )
            logger.info("Created DynamoDB table: %s", name)
        except ClientError as e:
            if e.response["Error"]["Code"] != "ResourceInUseException":
                raise

    # ------------------------------------------------------------------
    # Session operations
    # ------------------------------------------------------------------
    def save_session(
        self,
        session_id: str,
        *,
        contact_id: str = "",
        caller_number: str = "",
        consent_given: bool = False,
        language: str = "en-US",
        intent: str = "",
        context: Optional[dict] = None,
    ):
        """Create or update a call session."""
        table = self.ddb.Table(SESSIONS_TABLE)
        now = datetime.now(timezone.utc).isoformat()
        item = {
            "session_id": session_id,
            "contact_id": contact_id,
            "caller_number": caller_number,
            "consent_given": consent_given,
            "language": language,
            "intent": intent,
            "context": json.dumps(context or {}),
            "created_at": now,
            "updated_at": now,
        }
        table.put_item(Item=item)
        logger.debug("Saved session %s", session_id)

    def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve a session by id."""
        table = self.ddb.Table(SESSIONS_TABLE)
        resp = table.get_item(Key={"session_id": session_id})
        item = resp.get("Item")
        if item and "context" in item:
            try:
                item["context"] = json.loads(item["context"])
            except (json.JSONDecodeError, TypeError):
                pass
        return item

    def update_session(self, session_id: str, **kwargs):
        """Merge fields into an existing session."""
        table = self.ddb.Table(SESSIONS_TABLE)
        kwargs["updated_at"] = datetime.now(timezone.utc).isoformat()
        update_expr_parts = []
        expr_values = {}
        expr_names = {}
        for i, (k, v) in enumerate(kwargs.items()):
            alias = f"#k{i}"
            val_alias = f":v{i}"
            update_expr_parts.append(f"{alias} = {val_alias}")
            expr_names[alias] = k
            expr_values[val_alias] = v
        table.update_item(
            Key={"session_id": session_id},
            UpdateExpression="SET " + ", ".join(update_expr_parts),
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )

    def delete_session(self, session_id: str):
        table = self.ddb.Table(SESSIONS_TABLE)
        table.delete_item(Key={"session_id": session_id})

    # ------------------------------------------------------------------
    # Call log operations
    # ------------------------------------------------------------------
    def log_call_event(
        self,
        contact_id: str,
        event_type: str,
        *,
        session_id: str = "",
        data: Optional[dict] = None,
    ):
        """Append an event to the call log (immutable audit trail)."""
        table = self.ddb.Table(CALL_LOG_TABLE)
        now = datetime.now(timezone.utc).isoformat()
        table.put_item(
            Item={
                "contact_id": contact_id,
                "timestamp": now,
                "event_type": event_type,
                "session_id": session_id,
                "data": json.dumps(data or {}),
            }
        )
        logger.debug("Logged event %s for contact %s", event_type, contact_id)

    def get_call_log(self, contact_id: str) -> list[dict]:
        """Get all events for a contact."""
        table = self.ddb.Table(CALL_LOG_TABLE)
        resp = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("contact_id").eq(contact_id)
        )
        items = resp.get("Items", [])
        for item in items:
            if "data" in item:
                try:
                    item["data"] = json.loads(item["data"])
                except (json.JSONDecodeError, TypeError):
                    pass
        return items


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_store: Optional[DynamoDBStore] = None


def get_dynamodb_store() -> DynamoDBStore:
    global _store
    if _store is None:
        _store = DynamoDBStore()
    return _store
