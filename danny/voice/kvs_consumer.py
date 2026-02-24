"""
Kinesis Video Streams consumer for Danny AI.

Reads real-time audio from Amazon Connect's live media streaming
(via KVS) and yields PCM audio chunks for transcription.

Architecture:
  Connect → Start Media Streaming → KVS → This consumer → Transcribe Streaming

The consumer uses the GetMedia API to pull audio fragments in MKV format,
extracts the raw PCM audio, and feeds it to a callback or async queue.
"""

import os
import io
import struct
import logging
import asyncio
from typing import Optional, AsyncGenerator, Callable

import boto3

logger = logging.getLogger(__name__)


class KVSConsumer:
    """
    Consumes audio from an Amazon Kinesis Video Stream.

    Amazon Connect streams caller audio to KVS in near real-time.
    This consumer reads the MKV-wrapped PCM audio and extracts
    raw audio bytes for downstream processing (Transcribe).
    """

    def __init__(
        self,
        stream_arn: str,
        *,
        region: Optional[str] = None,
        fragment_selector_type: str = "PRODUCER_TIMESTAMP",
        start_timestamp: Optional[float] = None,
    ):
        self.stream_arn = stream_arn
        self.region = region or os.getenv("AWS_REGION", "us-west-2")
        self.fragment_selector_type = fragment_selector_type
        self.start_timestamp = start_timestamp

        # KVS requires a data-plane endpoint, obtained from the control plane
        self._kvs_client = boto3.client(
            "kinesisvideo", region_name=self.region
        )
        self._data_endpoint: Optional[str] = None
        self._media_client = None
        self._running = False

    def _get_data_endpoint(self) -> str:
        """Get the KVS data-plane endpoint for GetMedia."""
        if self._data_endpoint:
            return self._data_endpoint

        resp = self._kvs_client.get_data_endpoint(
            StreamARN=self.stream_arn,
            APIName="GET_MEDIA",
        )
        self._data_endpoint = resp["DataEndpoint"]
        logger.info("KVS data endpoint: %s", self._data_endpoint)
        return self._data_endpoint

    def _get_media_client(self):
        """Create a KVS media client for GetMedia calls."""
        endpoint = self._get_data_endpoint()
        return boto3.client(
            "kinesis-video-media",
            region_name=self.region,
            endpoint_url=endpoint,
        )

    # ------------------------------------------------------------------
    # Synchronous chunk-based reader (suitable for Lambda / threads)
    # ------------------------------------------------------------------
    def read_audio_chunks(
        self,
        chunk_duration_ms: int = 100,
        sample_rate: int = 8000,
    ):
        """
        Generator that yields raw PCM audio chunks from the KVS stream.

        Each chunk is `chunk_duration_ms` ms of 16-bit mono PCM at `sample_rate`.
        The MKV container wrapping is stripped, yielding only audio bytes.

        Yields:
            bytes: Raw PCM audio chunk
        """
        import datetime as dt

        media_client = self._get_media_client()

        start_selector = {"StartSelectorType": "NOW"}
        if self.start_timestamp:
            start_selector = {
                "StartSelectorType": self.fragment_selector_type,
                "StartTimestamp": dt.datetime.fromtimestamp(self.start_timestamp),
            }

        response = media_client.get_media(
            StreamARN=self.stream_arn,
            StartSelector=start_selector,
        )

        stream = response["Payload"]
        self._running = True

        chunk_size = int(sample_rate * (chunk_duration_ms / 1000) * 2)  # 16-bit = 2 bytes/sample
        buffer = b""

        logger.info(
            "KVS consumer started — stream=%s, chunk=%dms, rate=%dHz",
            self.stream_arn[-40:],
            chunk_duration_ms,
            sample_rate,
        )

        try:
            for raw_chunk in stream.iter_chunks(chunk_size=4096):
                if not self._running:
                    break

                # The payload from GetMedia is raw MKV.
                # For Connect audio the MKV often contains just one audio track
                # with raw PCM (L16).  We extract audio by collecting bytes
                # and emitting fixed-size chunks.  A production-grade parser
                # would use ebmlite or a custom MKV parser; here we rely on
                # the fact that Connect sends simple single-track containers.
                audio_bytes = self._extract_audio_from_mkv_chunk(raw_chunk)
                if not audio_bytes:
                    continue

                buffer += audio_bytes
                while len(buffer) >= chunk_size:
                    yield buffer[:chunk_size]
                    buffer = buffer[chunk_size:]

            # Flush remaining
            if buffer:
                yield buffer

        except Exception as e:
            logger.error("KVS read error: %s", e, exc_info=True)
        finally:
            self._running = False
            logger.info("KVS consumer stopped")

    # ------------------------------------------------------------------
    # Async wrapper for use with Transcribe streaming
    # ------------------------------------------------------------------
    async def async_audio_stream(
        self,
        chunk_duration_ms: int = 100,
        sample_rate: int = 8000,
    ) -> AsyncGenerator[bytes, None]:
        """
        Async generator wrapper around read_audio_chunks.
        Runs the synchronous KVS reader in a thread executor.
        """
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue[Optional[bytes]] = asyncio.Queue(maxsize=50)

        def _reader():
            try:
                for chunk in self.read_audio_chunks(chunk_duration_ms, sample_rate):
                    asyncio.run_coroutine_threadsafe(queue.put(chunk), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)  # sentinel

        # Run the blocking reader in a thread
        loop.run_in_executor(None, _reader)

        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk

    # ------------------------------------------------------------------
    # MKV audio extraction helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_audio_from_mkv_chunk(raw: bytes) -> bytes:
        """
        Best-effort extraction of audio bytes from an MKV fragment.

        Amazon Connect streams MKV with a single audio track (L16, 8kHz, mono).
        This simple extractor skips known EBML/MKV element headers and collects
        raw audio data.  For full MKV parsing, use ebmlite.

        A robust alternative is to use the Amazon KVS Parser Library (Java)
        or the connect-kvs-consumer npm package.
        """
        # EBML / Matroska element IDs we want to skip over
        SKIP_IDS = {
            b"\x1a\x45\xdf\xa3",  # EBML header
            b"\x18\x53\x80\x67",  # Segment
            b"\x16\x54\xae\x6b",  # Tracks
            b"\x1f\x43\xb6\x75",  # Cluster
            b"\xe7",              # Timestamp
            b"\xa3",              # SimpleBlock header
        }

        # For MVP we pass through all bytes after the first SimpleBlock marker
        # This is a simplification; in production use a proper parser
        idx = raw.find(b"\xa3")
        if idx >= 0 and idx + 4 < len(raw):
            # Skip the SimpleBlock header (element ID + size + track/flags)
            # Typically 4-8 bytes of header before raw PCM
            header_skip = min(idx + 8, len(raw))
            return raw[header_skip:]

        # If no SimpleBlock found, return raw bytes (may include headers)
        # This is acceptable for PCM where a few stray bytes cause minor noise
        return raw

    def stop(self):
        """Signal the consumer to stop reading."""
        self._running = False
