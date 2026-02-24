"""
AWS Lambda handler for Danny AI.
This function is invoked by Amazon Connect when a call comes in.
"""

import json
import asyncio
import os
import sys

# Add the parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
                "Attributes": {}
            },
            "Parameters": {
                "customer_input": "What the caller said"
            }
        },
        "Name": "ContactFlowEvent"
    }
    
    Returns:
    {
        "danny_response": "Danny's response text",
        "transfer_requested": "true" or "false"
    }
    """
    print(f"[Danny Lambda] Received event: {json.dumps(event)}")
    
    try:
        # Extract customer input
        parameters = event.get("Details", {}).get("Parameters", {})
        contact_data = event.get("Details", {}).get("ContactData", {})
        
        customer_input = parameters.get("customer_input", "")
        contact_id = contact_data.get("ContactId", "unknown")
        caller_number = contact_data.get("CustomerEndpoint", {}).get("Address", "unknown")
        
        # Get existing conversation context from attributes
        attributes = contact_data.get("Attributes", {})
        session_id = attributes.get("session_id", contact_id)
        
        print(f"[Danny Lambda] Contact: {contact_id}, Caller: {caller_number}")
        print(f"[Danny Lambda] Customer said: {customer_input}")
        
        # Process with Danny
        response_text, transfer_requested = asyncio.get_event_loop().run_until_complete(
            process_with_danny(session_id, customer_input)
        )
        
        # Truncate response if too long for TTS (Connect limits)
        if len(response_text) > 3000:
            response_text = response_text[:2900] + "... Would you like me to continue?"
        
        result = {
            "response": response_text,
            "transfer_requested": "true" if transfer_requested else "false",
            "should_end": "true" if transfer_requested else "false",
            "session_id": session_id
        }
        
        print(f"[Danny Lambda] Response: {result}")
        return result
        
    except Exception as e:
        print(f"[Danny Lambda] Error: {str(e)}")
        return {
            "response": "I apologize, but I'm experiencing some technical difficulties. Let me transfer you to a staff member who can help.",
            "transfer_requested": "true",
            "should_end": "true",
            "error": str(e)
        }


async def process_with_danny(session_id: str, user_input: str) -> tuple[str, bool]:
    """
    Process user input through Danny and return response.
    
    Returns:
        Tuple of (response_text, transfer_requested)
    """
    from danny.agent import get_danny_agent
    
    agent = get_danny_agent()
    
    # If this is the start of a conversation (no input), get greeting
    if not user_input or user_input.strip() == "":
        response = await agent.start_conversation(session_id)
        return response, False
    
    # Process the user's message
    response = await agent.process_message(session_id, user_input)
    
    # Check if transfer was requested
    transfer_requested = "[TRANSFER_REQUESTED]" in response
    
    # Clean up the response for speech
    if transfer_requested:
        # Remove the transfer marker and keep just the message
        response = response.replace("[TRANSFER_REQUESTED]", "").strip()
        # Get just the first sentence for transfer message
        if "Reason:" in response:
            response = "Let me transfer you to a staff member who can help with that."
    
    return response, transfer_requested


# For local testing
if __name__ == "__main__":
    # Simulate a Connect event
    test_event = {
        "Details": {
            "ContactData": {
                "ContactId": "test-contact-123",
                "CustomerEndpoint": {
                    "Address": "+15551234567",
                    "Type": "TELEPHONE_NUMBER"
                },
                "InitialContactId": "test-contact-123",
                "Attributes": {}
            },
            "Parameters": {
                "customer_input": "I'd like to schedule a cleaning appointment"
            }
        },
        "Name": "ContactFlowEvent"
    }
    
    result = lambda_handler(test_event, None)
    print(f"\nFinal result: {json.dumps(result, indent=2)}")
