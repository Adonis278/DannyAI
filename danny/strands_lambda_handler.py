"""
AWS Lambda handler for Danny AI (Strands Framework).

Supports two invocation modes:

 1. **Simple (Connect ContactFlow)** — Connect invokes the Lambda with
    ``customer_input`` in Parameters.  Danny returns a text response and
    Connect plays it via Polly.  This is the existing "get customer input →
    invoke Lambda → play prompt" loop defined in the contact flow.

 2. **Streaming pipeline** — When Connect starts KVS live media streaming,
    the Lambda receives a ``stream_arn``.  It launches the full pipeline
    (KVS → Transcribe Streaming → Agent → Polly → callback).  This mode
    handles the entire call in a single Lambda invocation.

The handler auto-detects the mode based on the presence of ``stream_arn``.
"""

import json
import os
import sys
import asyncio
import logging

# Add the parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    """
    Main Lambda handler for Amazon Connect integration.

    Event structure from Connect:
    {
        "Details": {
            "ContactData": {
                "ContactId": "...",
                "CustomerEndpoint": {"Address": "+1234567890", "Type": "TELEPHONE_NUMBER"},
                "InitialContactId": "...",
                "InstanceARN": "...",
                "MediaStreams": {
                    "Customer": {
                        "Audio": {
                            "StreamARN": "arn:aws:kinesisvideo:...",
                            "StartFragmentNumber": "...",
                            "StartTimestamp": "...",
                            "StreamingStatus": "STARTED"
                        }
                    }
                },
                "Attributes": {}
            },
            "Parameters": {
                "customer_input": "What the caller said",
                "action": "greeting | streaming"
            }
        },
        "Name": "ContactFlowEvent"
    }

    Returns:
    {
        "response": "Danny's response text",
        "transfer_requested": "true" or "false"
    }
    """
    print(f"[Danny Lambda] Received event: {json.dumps(event)}")

    try:
        parameters = event.get("Details", {}).get("Parameters", {})
        contact_data = event.get("Details", {}).get("ContactData", {})

        action = parameters.get("action", "")
        contact_id = contact_data.get("ContactId", "unknown")
        caller_number = contact_data.get("CustomerEndpoint", {}).get("Address", "unknown")

        # ---- Detect streaming mode ----
        media_streams = contact_data.get("MediaStreams", {})
        customer_audio = media_streams.get("Customer", {}).get("Audio", {})
        stream_arn = customer_audio.get("StreamARN", "") or parameters.get("stream_arn", "")

        if stream_arn and action == "streaming":
            return _handle_streaming(contact_id, stream_arn, caller_number, context)

        # ---- Simple (text-based) mode ----
        customer_input = parameters.get("customer_input", "")
        attributes = contact_data.get("Attributes", {})
        session_id = attributes.get("session_id", contact_id)

        print(f"[Danny Lambda] Contact: {contact_id}, Caller: {caller_number}")
        print(f"[Danny Lambda] Customer said: {customer_input}")
        print(f"[Danny Lambda] Action: {action}")

        response_text = process_with_strands(customer_input, caller_number, action)

        transfer_requested = "[TRANSFER_REQUESTED]" in response_text

        if transfer_requested:
            response_text = response_text.split("[TRANSFER_REQUESTED]")[0].strip()
            if not response_text:
                response_text = "Let me transfer you to a staff member who can help with that."

        if len(response_text) > 3000:
            response_text = response_text[:2900] + "... Would you like me to continue?"

        response_text = clean_for_speech(response_text)

        result = {
            "response": response_text,
            "transfer_requested": "true" if transfer_requested else "false",
            "should_end": "true" if transfer_requested else "false",
            "session_id": session_id,
        }

        print(f"[Danny Lambda] Response: {result}")
        return result

    except Exception as e:
        print(f"[Danny Lambda] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "response": "I apologize, but I'm experiencing some technical difficulties. Let me transfer you to a staff member who can help.",
            "transfer_requested": "true",
            "should_end": "true",
            "error": str(e),
        }


# =============================================================================
# Streaming pipeline mode
# =============================================================================

def _handle_streaming(contact_id: str, stream_arn: str, caller_number: str, context):
    """
    Launch the full voice pipeline for a KVS-streamed call.

    The pipeline runs asynchronously until the caller hangs up
    or the session time limit is reached.
    """
    from danny.voice.voice_pipeline import VoicePipeline, PipelineConfig, handle_connect_call

    print(f"[Danny Lambda] Streaming mode — contact={contact_id}, stream={stream_arn}")

    # Accumulate responses so the Lambda can still return useful data
    responses: list[str] = []

    async def _on_text(text: str):
        responses.append(text)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        session = loop.run_until_complete(
            handle_connect_call(
                contact_id=contact_id,
                stream_arn=stream_arn,
                caller_number=caller_number,
                on_response_text=_on_text,
            )
        )

        transfer = session.transfer_requested if session else False

        return {
            "response": responses[-1] if responses else "Call ended.",
            "transfer_requested": "true" if transfer else "false",
            "should_end": "true",
            "session_id": session.session_id if session else contact_id,
            "turns": len(session.turns) if session else 0,
        }
    except Exception as e:
        logger.error("Streaming pipeline error: %s", e, exc_info=True)
        return {
            "response": "I apologize, but I experienced a technical issue during our call. Please call back and we'll be happy to help.",
            "transfer_requested": "true",
            "should_end": "true",
            "error": str(e),
        }
    finally:
        loop.close()


# =============================================================================
# Simple (text) mode processing
# =============================================================================

def process_with_strands(user_input: str, caller_number: str = "", action: str = "") -> str:
    """
    Process user input through the Strands Danny agent.

    Args:
        user_input: What the caller said
        caller_number: The caller's phone number
        action: Optional action (e.g., "greeting" for initial call)

    Returns:
        Danny's response text
    """
    from danny.strands_agent import get_danny_agent

    agent = get_danny_agent()

    if action == "greeting" or not user_input.strip():
        prompt = "A patient is calling. Please greet them warmly and ask how you can help."
        if caller_number:
            prompt += f" Their phone number is {caller_number}."
    else:
        prompt = user_input

    response = agent(prompt)

    response_text = ""

    if hasattr(response, "message") and response.message:
        msg = response.message
        if isinstance(msg, dict):
            content = msg.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        response_text += item["text"]
            elif isinstance(content, str):
                response_text = content
        elif hasattr(msg, "content"):
            response_text = str(msg.content)
        else:
            response_text = str(msg)
    elif hasattr(response, "content"):
        response_text = str(response.content)
    else:
        response_text = str(response)

    if response_text.startswith("{'role':"):
        try:
            parsed = eval(response_text)
            content = parsed.get("content", [])
            if isinstance(content, list) and content:
                response_text = content[0].get("text", response_text)
        except Exception:
            pass

    return response_text


def clean_for_speech(text: str) -> str:
    """Clean text for text-to-speech output."""
    import re

    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*]\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n\s*\n", "\n", text)
    text = re.sub(r"```[^`]*```", "", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)

    return text.strip()


# Alias for Connect
handler = lambda_handler


# =============================================================================
# Local Testing
# =============================================================================

if __name__ == "__main__":
    print("Danny Lambda Handler - Local Test")
    print("=" * 50)

    # Test 1: Initial greeting (simple mode)
    print("\nTest 1: Initial Call (simple mode)")
    event1 = {
        "Details": {
            "ContactData": {
                "ContactId": "test-123",
                "CustomerEndpoint": {"Address": "+15551234567", "Type": "TELEPHONE_NUMBER"},
                "Attributes": {},
            },
            "Parameters": {"action": "greeting"},
        }
    }
    result1 = lambda_handler(event1, None)
    print(f"Response: {result1['response'][:200]}...")

    # Test 2: Appointment request (simple mode)
    print("\nTest 2: Appointment Request (simple mode)")
    event2 = {
        "Details": {
            "ContactData": {
                "ContactId": "test-123",
                "CustomerEndpoint": {"Address": "+15551234567", "Type": "TELEPHONE_NUMBER"},
                "Attributes": {},
            },
            "Parameters": {"customer_input": "I'd like to schedule a cleaning appointment"},
        }
    }
    result2 = lambda_handler(event2, None)
    print(f"Response: {result2['response'][:200]}...")

    # Test 3: Insurance question (simple mode)
    print("\nTest 3: Insurance Question (simple mode)")
    event3 = {
        "Details": {
            "ContactData": {
                "ContactId": "test-123",
                "CustomerEndpoint": {"Address": "+15551234567", "Type": "TELEPHONE_NUMBER"},
                "Attributes": {},
            },
            "Parameters": {"customer_input": "Do you accept Delta Dental insurance?"},
        }
    }
    result3 = lambda_handler(event3, None)
    print(f"Response: {result3['response'][:200]}...")

    print("\nAll tests completed!")
