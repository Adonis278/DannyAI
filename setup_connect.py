"""Set up Amazon Connect contact flow for Danny.

This script:
1. Associates Lambda with Connect instance
2. Creates a contact flow that invokes Danny
3. Associates the phone number with the flow
"""
import os
import json
import boto3
from dotenv import load_dotenv

load_dotenv()

# Configuration
AWS_REGION = os.getenv("CONNECT_REGION", "us-west-2")
INSTANCE_ID = os.getenv("CONNECT_INSTANCE_ID", "")
PHONE_NUMBER_ID = os.getenv("CONNECT_PHONE_NUMBER_ID", "")
LAMBDA_ARN = f"arn:aws:lambda:{AWS_REGION}:029643847270:function:danny-voice-handler"

# Set credentials
os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID", "")
os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY", "")


def get_or_create_queue(connect_client):
    """Get or create a basic queue for routing."""
    # List existing queues
    response = connect_client.list_queues(InstanceId=INSTANCE_ID)
    for queue in response.get('QueueSummaryList', []):
        if queue.get('QueueType') == 'STANDARD':
            print(f"  Using existing queue: {queue['Name']}")
            return queue['Id'], queue['Arn']
    
    print("  No standard queue found - please create one in Connect console")
    return None, None


def associate_lambda(connect_client):
    """Associate Lambda function with Connect instance."""
    print("Associating Lambda with Connect instance...")
    
    try:
        connect_client.associate_lambda_function(
            InstanceId=INSTANCE_ID,
            FunctionArn=LAMBDA_ARN
        )
        print("  Lambda associated!")
    except connect_client.exceptions.ResourceConflictException:
        print("  Lambda already associated")
    except Exception as e:
        print(f"  Error: {e}")
        return False
    return True


def create_danny_contact_flow(connect_client):
    """Create the Danny AI contact flow."""
    print("Creating Danny contact flow...")
    
    # Check if flow already exists
    response = connect_client.list_contact_flows(InstanceId=INSTANCE_ID)
    for flow in response.get('ContactFlowSummaryList', []):
        if flow.get('Name') == 'Danny AI Voice Assistant':
            print(f"  Contact flow already exists: {flow['Id']}")
            return flow['Id'], flow['Arn']
    
    # Contact flow content - this is a simple flow that:
    # 1. Plays welcome message
    # 2. Gets customer input
    # 3. Invokes Lambda
    # 4. Speaks response
    # 5. Loops back for more input
    
    content = {
        "Version": "2019-10-30",
        "StartAction": "Welcome",
        "Actions": [
            {
                "Identifier": "Welcome",
                "Type": "MessageParticipant",
                "Parameters": {
                    "Text": "Hello, thank you for calling Sample Dental Practice. My name is Danny, I'm your AI dental assistant. How can I help you today?"
                },
                "Transitions": {
                    "NextAction": "GetInput",
                    "Errors": [
                        {
                            "NextAction": "Hangup",
                            "ErrorType": "NoMatchingError"
                        }
                    ]
                }
            },
            {
                "Identifier": "GetInput",
                "Type": "GetParticipantInput",
                "Parameters": {
                    "InputTimeLimitSeconds": "7",
                    "StoreInput": "True",
                    "InputValidation": {
                        "CustomValidation": {
                            "MaximumLength": "1000"
                        }
                    },
                    "Media": {
                        "Uri": "Beep.wav",
                        "SourceType": "S3",
                        "Enabled": "False"
                    }
                },
                "Transitions": {
                    "NextAction": "InvokeLambda",
                    "Errors": [
                        {
                            "NextAction": "NoInputResponse",
                            "ErrorType": "InputTimeLimitExceeded"
                        },
                        {
                            "NextAction": "Hangup",
                            "ErrorType": "NoMatchingError"
                        }
                    ]
                }
            },
            {
                "Identifier": "InvokeLambda",
                "Type": "InvokeLambdaFunction",
                "Parameters": {
                    "LambdaFunctionARN": LAMBDA_ARN,
                    "InvocationTimeLimitSeconds": "8",
                    "LambdaInvocationAttributes": {
                        "input_type": "voice",
                        "language": "en"
                    }
                },
                "Transitions": {
                    "NextAction": "SpeakResponse",
                    "Errors": [
                        {
                            "NextAction": "ErrorResponse",
                            "ErrorType": "NoMatchingError"
                        }
                    ]
                }
            },
            {
                "Identifier": "SpeakResponse",
                "Type": "MessageParticipant",
                "Parameters": {
                    "Text": "$.External.response"
                },
                "Transitions": {
                    "NextAction": "CheckContinue",
                    "Errors": [
                        {
                            "NextAction": "GetInput",
                            "ErrorType": "NoMatchingError"
                        }
                    ]
                }
            },
            {
                "Identifier": "CheckContinue",
                "Type": "CheckAttribute",
                "Parameters": {
                    "Attribute": "$.External.should_end",
                    "ComparisonType": "Equals",
                    "Value": "true"
                },
                "Transitions": {
                    "Conditions": [
                        {
                            "NextAction": "GoodbyeMessage",
                            "Condition": {
                                "Operands": ["true"]
                            }
                        }
                    ],
                    "DefaultAction": "GetInput",
                    "Errors": [
                        {
                            "NextAction": "GetInput",
                            "ErrorType": "NoMatchingError"
                        }
                    ]
                }
            },
            {
                "Identifier": "NoInputResponse",
                "Type": "MessageParticipant",
                "Parameters": {
                    "Text": "I didn't hear anything. Are you still there? Please let me know how I can help."
                },
                "Transitions": {
                    "NextAction": "GetInput",
                    "Errors": [
                        {
                            "NextAction": "Hangup",
                            "ErrorType": "NoMatchingError"
                        }
                    ]
                }
            },
            {
                "Identifier": "ErrorResponse",
                "Type": "MessageParticipant",
                "Parameters": {
                    "Text": "I apologize, I'm having some technical difficulties. Please hold while I connect you with our staff."
                },
                "Transitions": {
                    "NextAction": "Hangup",
                    "Errors": [
                        {
                            "NextAction": "Hangup",
                            "ErrorType": "NoMatchingError"
                        }
                    ]
                }
            },
            {
                "Identifier": "GoodbyeMessage",
                "Type": "MessageParticipant",
                "Parameters": {
                    "Text": "Thank you for calling. Have a great day! Goodbye."
                },
                "Transitions": {
                    "NextAction": "Hangup",
                    "Errors": [
                        {
                            "NextAction": "Hangup",
                            "ErrorType": "NoMatchingError"
                        }
                    ]
                }
            },
            {
                "Identifier": "Hangup",
                "Type": "DisconnectParticipant",
                "Parameters": {}
            }
        ]
    }
    
    try:
        response = connect_client.create_contact_flow(
            InstanceId=INSTANCE_ID,
            Name="Danny AI Voice Assistant",
            Type="CONTACT_FLOW",
            Description="AI-powered dental practice voice assistant",
            Content=json.dumps(content)
        )
        flow_id = response['ContactFlowId']
        flow_arn = response['ContactFlowArn']
        print(f"  Contact flow created: {flow_id}")
        return flow_id, flow_arn
    except Exception as e:
        print(f"  Error creating contact flow: {e}")
        return None, None


def associate_phone_number(connect_client, flow_id):
    """Associate phone number with the contact flow."""
    print("Associating phone number with contact flow...")
    
    if not PHONE_NUMBER_ID:
        print("  Error: CONNECT_PHONE_NUMBER_ID not set in .env")
        return False
    
    try:
        connect_client.update_phone_number(
            PhoneNumberId=PHONE_NUMBER_ID,
            TargetArn=f"arn:aws:connect:{AWS_REGION}:029643847270:instance/{INSTANCE_ID}/contact-flow/{flow_id}"
        )
        print("  Phone number associated with Danny flow!")
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False


def main():
    """Main setup function."""
    print("=" * 50)
    print("Danny Connect Setup")
    print("=" * 50)
    print()
    print(f"Instance ID: {INSTANCE_ID}")
    print(f"Region: {AWS_REGION}")
    print(f"Lambda ARN: {LAMBDA_ARN}")
    print()
    
    # Initialize Connect client
    connect_client = boto3.client('connect', region_name=AWS_REGION)
    
    # Step 1: Associate Lambda
    if not associate_lambda(connect_client):
        print("Failed to associate Lambda. Aborting.")
        return
    
    print()
    
    # Step 2: Create contact flow
    flow_id, flow_arn = create_danny_contact_flow(connect_client)
    if not flow_id:
        print("Failed to create contact flow. Aborting.")
        return
    
    print()
    
    # Step 3: Associate phone number
    associate_phone_number(connect_client, flow_id)
    
    print()
    print("=" * 50)
    print("Setup Complete!")
    print("=" * 50)
    print()
    phone = os.getenv("CONNECT_PHONE_NUMBER", "")
    print(f"Danny is now available at: {phone}")
    print()
    print("Try calling the number to test!")


if __name__ == "__main__":
    main()
