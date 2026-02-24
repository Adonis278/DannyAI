"""Create Danny contact flow with proper format."""
import os
import json
import uuid
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


def create_contact_flow_content():
    """Generate proper contact flow JSON."""
    # Generate UUIDs for actions
    welcome_id = str(uuid.uuid4())
    invoke_lambda_id = str(uuid.uuid4())
    speak_response_id = str(uuid.uuid4())
    error_id = str(uuid.uuid4())
    disconnect_id = str(uuid.uuid4())
    
    content = {
        "Version": "2019-10-30",
        "StartAction": welcome_id,
        "Metadata": {
            "entryPointPosition": {"x": 40, "y": 40},
            "snapToGrid": False,
            "name": "Danny AI Voice Assistant",
            "description": "AI-powered dental practice assistant",
            "type": "contactFlow",
            "status": "published"
        },
        "Actions": [
            {
                "Identifier": welcome_id,
                "Parameters": {
                    "Text": "Hello, thank you for calling Sample Dental Practice. This is Danny, your AI dental assistant. I can help you schedule appointments, verify insurance, or answer questions about our services. One moment while I look up your information."
                },
                "Transitions": {
                    "NextAction": invoke_lambda_id,
                    "Errors": [],
                    "Conditions": []
                },
                "Type": "MessageParticipant"
            },
            {
                "Identifier": invoke_lambda_id,
                "Parameters": {
                    "LambdaFunctionARN": LAMBDA_ARN,
                    "InvocationTimeLimitSeconds": "8",
                    "LambdaInvocationAttributes": {
                        "action": "greeting",
                        "language": "en"
                    }
                },
                "Transitions": {
                    "NextAction": speak_response_id,
                    "Errors": [
                        {
                            "NextAction": error_id,
                            "ErrorType": "NoMatchingError"
                        }
                    ],
                    "Conditions": []
                },
                "Type": "InvokeLambdaFunction"
            },
            {
                "Identifier": speak_response_id,
                "Parameters": {
                    "Text": "$.External.response"
                },
                "Transitions": {
                    "NextAction": disconnect_id,
                    "Errors": [],
                    "Conditions": []
                },
                "Type": "MessageParticipant"
            },
            {
                "Identifier": error_id,
                "Parameters": {
                    "Text": "I apologize, but I'm having technical difficulties. Please call back or press zero to speak with our staff directly."
                },
                "Transitions": {
                    "NextAction": disconnect_id,
                    "Errors": [],
                    "Conditions": []
                },
                "Type": "MessageParticipant"
            },
            {
                "Identifier": disconnect_id,
                "Parameters": {},
                "Transitions": {},
                "Type": "DisconnectParticipant"
            }
        ]
    }
    
    return json.dumps(content)


def main():
    """Main setup function."""
    print("=" * 50)
    print("Danny Contact Flow Setup")
    print("=" * 50)
    print()
    
    connect_client = boto3.client('connect', region_name=AWS_REGION)
    
    # Check if flow already exists
    print("Checking for existing Danny flow...")
    response = connect_client.list_contact_flows(InstanceId=INSTANCE_ID)
    existing_flow_id = None
    for flow in response.get('ContactFlowSummaryList', []):
        if flow.get('Name') == 'Danny AI Voice Assistant':
            existing_flow_id = flow['Id']
            print(f"  Found existing flow: {existing_flow_id}")
            break
    
    content = create_contact_flow_content()
    
    if existing_flow_id:
        # Update existing flow
        print("Updating existing contact flow...")
        try:
            connect_client.update_contact_flow_content(
                InstanceId=INSTANCE_ID,
                ContactFlowId=existing_flow_id,
                Content=content
            )
            print("  Flow updated!")
            flow_id = existing_flow_id
        except Exception as e:
            print(f"  Error: {e}")
            return
    else:
        # Create new flow
        print("Creating new contact flow...")
        try:
            response = connect_client.create_contact_flow(
                InstanceId=INSTANCE_ID,
                Name="Danny AI Voice Assistant",
                Type="CONTACT_FLOW",
                Description="AI-powered dental practice voice assistant",
                Content=content
            )
            flow_id = response['ContactFlowId']
            print(f"  Flow created: {flow_id}")
        except Exception as e:
            print(f"  Error: {e}")
            # Print content for debugging
            print("\nContent that failed:")
            print(json.dumps(json.loads(content), indent=2)[:1000])
            return
    
    # Associate phone number
    print()
    print("Associating phone number with flow...")
    if PHONE_NUMBER_ID:
        try:
            # Get account ID
            sts = boto3.client('sts', region_name=AWS_REGION)
            account_id = sts.get_caller_identity()['Account']
            
            target_arn = f"arn:aws:connect:{AWS_REGION}:{account_id}:instance/{INSTANCE_ID}/contact-flow/{flow_id}"
            
            connect_client.update_phone_number(
                PhoneNumberId=PHONE_NUMBER_ID,
                TargetArn=target_arn
            )
            print("  Phone number associated!")
        except Exception as e:
            print(f"  Error: {e}")
    else:
        print("  No phone number ID configured")
    
    print()
    print("=" * 50)
    print("Setup Complete!")
    print("=" * 50)
    print()
    print(f"Contact Flow ID: {flow_id}")
    print(f"Phone Number: {os.getenv('CONNECT_PHONE_NUMBER', 'Not set')}")
    print()
    print("Call the phone number to test Danny!")


if __name__ == "__main__":
    main()
