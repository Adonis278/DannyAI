"""
Amazon Connect handler for Danny AI.
Manages inbound call routing and contact flows.
"""

import boto3
import json
from typing import Optional
import os

from ..config import get_config


class ConnectHandler:
    """Handles Amazon Connect integration."""
    
    def __init__(self, instance_id: Optional[str] = None):
        self.config = get_config()
        
        # Set credentials
        os.environ["AWS_ACCESS_KEY_ID"] = self.config.aws.access_key_id or ""
        os.environ["AWS_SECRET_ACCESS_KEY"] = self.config.aws.secret_access_key or ""
        os.environ["AWS_DEFAULT_REGION"] = self.config.aws.region
        
        self.client = boto3.client(
            "connect",
            region_name=self.config.aws.region
        )
        
        self.instance_id = instance_id or os.getenv("CONNECT_INSTANCE_ID", "")

    def set_instance_id(self, instance_id: str):
        """Set the Connect instance ID."""
        self.instance_id = instance_id

    def list_contact_flows(self) -> list[dict]:
        """List all contact flows in the instance."""
        if not self.instance_id:
            raise ValueError("Connect instance ID not configured")
            
        response = self.client.list_contact_flows(
            InstanceId=self.instance_id,
            ContactFlowTypes=["CONTACT_FLOW"]
        )
        return response.get("ContactFlowSummaryList", [])

    def list_phone_numbers(self) -> list[dict]:
        """List phone numbers associated with the instance."""
        if not self.instance_id:
            raise ValueError("Connect instance ID not configured")
        
        # Use ListPhoneNumbersV2 which is the current API
        response = self.client.list_phone_numbers_v2(
            TargetArn=f"arn:aws:connect:us-east-1:{self._get_account_id()}:instance/{self.instance_id}"
        )
        return response.get("ListPhoneNumbersSummaryList", [])

    def _get_account_id(self) -> str:
        """Get the AWS account ID."""
        import boto3
        sts = boto3.client("sts", region_name=self.config.aws.region)
        return sts.get_caller_identity()["Account"]

    def associate_phone_number_to_flow(
        self,
        phone_number_id: str,
        contact_flow_id: str
    ) -> dict:
        """Associate a phone number with a contact flow."""
        response = self.client.associate_phone_number_contact_flow(
            PhoneNumberId=phone_number_id,
            InstanceId=self.instance_id,
            ContactFlowId=contact_flow_id
        )
        return response

    def get_contact_attributes(self, contact_id: str) -> dict:
        """Get attributes for a specific contact/call."""
        response = self.client.get_contact_attributes(
            InstanceId=self.instance_id,
            InitialContactId=contact_id
        )
        return response.get("Attributes", {})

    def update_contact_attributes(
        self,
        contact_id: str,
        attributes: dict
    ) -> dict:
        """Update contact attributes during a call."""
        response = self.client.update_contact_attributes(
            InitialContactId=contact_id,
            InstanceId=self.instance_id,
            Attributes=attributes
        )
        return response


def create_danny_contact_flow_json() -> str:
    """
    Generate the contact flow JSON for Danny AI.
    This flow:
    1. Answers the call
    2. Plays consent message
    3. Invokes Lambda for Danny AI processing
    4. Plays Danny's response
    5. Loops for conversation
    6. Handles transfer to human when needed
    """
    contact_flow = {
        "Version": "2019-10-30",
        "StartAction": "welcome_prompt",
        "Actions": [
            {
                "Identifier": "welcome_prompt",
                "Type": "MessageParticipant",
                "Parameters": {
                    "Text": "Thank you for calling. This call may be recorded for quality assurance. You are now being connected to Danny, our AI dental assistant."
                },
                "Transitions": {
                    "NextAction": "get_customer_input",
                    "Errors": [
                        {"NextAction": "end_call", "ErrorType": "NoMatchingError"}
                    ]
                }
            },
            {
                "Identifier": "get_customer_input",
                "Type": "GetParticipantInput",
                "Parameters": {
                    "Text": "Hello! I'm Danny, your AI dental assistant. How can I help you today?",
                    "InputTimeLimitSeconds": "10",
                    "StoreInput": "True",
                    "InputType": "Speech"
                },
                "Transitions": {
                    "NextAction": "invoke_danny_lambda",
                    "Errors": [
                        {"NextAction": "no_input", "ErrorType": "NoMatchingError"},
                        {"NextAction": "no_input", "ErrorType": "InputTimeLimitExceeded"}
                    ]
                }
            },
            {
                "Identifier": "invoke_danny_lambda",
                "Type": "InvokeLambdaFunction",
                "Parameters": {
                    "LambdaFunctionARN": "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:danny-ai-handler",
                    "InvocationTimeLimitSeconds": "8"
                },
                "Transitions": {
                    "NextAction": "play_danny_response",
                    "Errors": [
                        {"NextAction": "lambda_error", "ErrorType": "NoMatchingError"}
                    ]
                }
            },
            {
                "Identifier": "play_danny_response",
                "Type": "MessageParticipant",
                "Parameters": {
                    "Text": "$.External.danny_response"
                },
                "Transitions": {
                    "NextAction": "check_transfer",
                    "Errors": [
                        {"NextAction": "get_customer_input", "ErrorType": "NoMatchingError"}
                    ]
                }
            },
            {
                "Identifier": "check_transfer",
                "Type": "CheckAttribute",
                "Parameters": {
                    "Attribute": "$.External.transfer_requested",
                    "Values": ["true"],
                    "ComparisonType": "Equals"
                },
                "Transitions": {
                    "NextAction": "get_customer_input",
                    "Conditions": [
                        {
                            "NextAction": "transfer_to_queue",
                            "Condition": {
                                "Operator": "Equals",
                                "Operands": ["true"]
                            }
                        }
                    ],
                    "Errors": [
                        {"NextAction": "get_customer_input", "ErrorType": "NoMatchingError"}
                    ]
                }
            },
            {
                "Identifier": "transfer_to_queue",
                "Type": "TransferContactToQueue",
                "Parameters": {},
                "Transitions": {
                    "NextAction": "end_call",
                    "Errors": [
                        {"NextAction": "transfer_failed", "ErrorType": "NoMatchingError"}
                    ]
                }
            },
            {
                "Identifier": "no_input",
                "Type": "MessageParticipant",
                "Parameters": {
                    "Text": "I didn't catch that. Could you please repeat?"
                },
                "Transitions": {
                    "NextAction": "get_customer_input",
                    "Errors": [
                        {"NextAction": "end_call", "ErrorType": "NoMatchingError"}
                    ]
                }
            },
            {
                "Identifier": "lambda_error",
                "Type": "MessageParticipant",
                "Parameters": {
                    "Text": "I'm having some technical difficulties. Let me transfer you to a staff member."
                },
                "Transitions": {
                    "NextAction": "transfer_to_queue",
                    "Errors": [
                        {"NextAction": "end_call", "ErrorType": "NoMatchingError"}
                    ]
                }
            },
            {
                "Identifier": "transfer_failed",
                "Type": "MessageParticipant",
                "Parameters": {
                    "Text": "I apologize, but I wasn't able to transfer your call. Please try calling back during business hours."
                },
                "Transitions": {
                    "NextAction": "end_call",
                    "Errors": [
                        {"NextAction": "end_call", "ErrorType": "NoMatchingError"}
                    ]
                }
            },
            {
                "Identifier": "end_call",
                "Type": "DisconnectParticipant",
                "Parameters": {},
                "Transitions": {}
            }
        ]
    }
    
    return json.dumps(contact_flow, indent=2)


# Singleton instance
_connect_handler: Optional[ConnectHandler] = None


def get_connect_handler() -> ConnectHandler:
    """Get the singleton Connect handler."""
    global _connect_handler
    if _connect_handler is None:
        _connect_handler = ConnectHandler()
    return _connect_handler
