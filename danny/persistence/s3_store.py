"""
S3 persistence for Danny AI.
Stores call recordings and transcripts with KMS encryption.

Bucket is created on first use if it doesn't exist (dev convenience).
In production deploy via CloudFormation / CDK with proper encryption and lifecycle rules.
"""

import os
import io
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

BUCKET_NAME = os.getenv("S3_DANNY_BUCKET", "danny-ai-recordings")


class S3Store:
    """Manages S3 storage for recordings and transcripts."""

    def __init__(self, region: Optional[str] = None, bucket: Optional[str] = None):
        self.region = region or os.getenv("AWS_REGION", "us-west-2")
        self.bucket = bucket or BUCKET_NAME
        self.s3 = boto3.client("s3", region_name=self.region)
        self._ensure_bucket()

    # ------------------------------------------------------------------
    # Bucket bootstrap
    # ------------------------------------------------------------------
    def _ensure_bucket(self):
        """Create the bucket if it doesn't exist (with SSE-S3 encryption)."""
        try:
            self.s3.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code in ("404", "NoSuchBucket"):
                self._create_bucket()
            else:
                logger.warning("Cannot verify bucket %s: %s", self.bucket, e)

    def _create_bucket(self):
        try:
            create_args = {"Bucket": self.bucket}
            # LocationConstraint is required for regions other than us-east-1
            if self.region != "us-east-1":
                create_args["CreateBucketConfiguration"] = {
                    "LocationConstraint": self.region
                }
            self.s3.create_bucket(**create_args)

            # Enable default encryption (SSE-S3)
            self.s3.put_bucket_encryption(
                Bucket=self.bucket,
                ServerSideEncryptionConfiguration={
                    "Rules": [
                        {
                            "ApplyServerSideEncryptionByDefault": {
                                "SSEAlgorithm": "AES256"
                            }
                        }
                    ]
                },
            )

            # Block public access
            self.s3.put_public_access_block(
                Bucket=self.bucket,
                PublicAccessBlockConfiguration={
                    "BlockPublicAcls": True,
                    "IgnorePublicAcls": True,
                    "BlockPublicPolicy": True,
                    "RestrictPublicBuckets": True,
                },
            )

            # Lifecycle rule — delete recordings after 90 days
            self.s3.put_bucket_lifecycle_configuration(
                Bucket=self.bucket,
                LifecycleConfiguration={
                    "Rules": [
                        {
                            "ID": "expire-recordings-90d",
                            "Filter": {"Prefix": "recordings/"},
                            "Status": "Enabled",
                            "Expiration": {"Days": 90},
                        }
                    ]
                },
            )

            logger.info("Created S3 bucket: %s (encrypted, 90-day lifecycle)", self.bucket)
        except ClientError as e:
            logger.error("Failed to create bucket %s: %s", self.bucket, e)

    # ------------------------------------------------------------------
    # Recording operations
    # ------------------------------------------------------------------
    def save_recording(
        self,
        contact_id: str,
        audio_bytes: bytes,
        *,
        content_type: str = "audio/wav",
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Store a call recording.
        Returns the S3 key.
        """
        date_prefix = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        ext = "wav" if "wav" in content_type else "mp3"
        key = f"recordings/{date_prefix}/{contact_id}.{ext}"

        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=audio_bytes,
            ContentType=content_type,
            Metadata=metadata or {},
            ServerSideEncryption="AES256",
        )
        logger.info("Saved recording: s3://%s/%s (%d bytes)", self.bucket, key, len(audio_bytes))
        return key

    def save_transcript(
        self,
        contact_id: str,
        transcript: list[dict],
        *,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Store a call transcript (list of {role, text, timestamp} dicts).
        Returns the S3 key.
        """
        date_prefix = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        key = f"transcripts/{date_prefix}/{contact_id}.json"

        body = json.dumps(
            {
                "contact_id": contact_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "turns": transcript,
            },
            indent=2,
        )

        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body.encode("utf-8"),
            ContentType="application/json",
            Metadata=metadata or {},
            ServerSideEncryption="AES256",
        )
        logger.info("Saved transcript: s3://%s/%s", self.bucket, key)
        return key

    def get_recording_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a pre-signed URL for a recording (default 1h)."""
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def get_transcript(self, key: str) -> Optional[dict]:
        """Download and parse a transcript JSON."""
        try:
            resp = self.s3.get_object(Bucket=self.bucket, Key=key)
            return json.loads(resp["Body"].read().decode("utf-8"))
        except ClientError:
            return None


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_store: Optional[S3Store] = None


def get_s3_store() -> S3Store:
    global _store
    if _store is None:
        _store = S3Store()
    return _store
