"""Quick test for Connect instance - now checking us-west-2."""
import os
import boto3
from dotenv import load_dotenv
load_dotenv()

# Set credentials
os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID", "")
os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY", "")

# Your Connect instance is in us-west-2
region = 'us-west-2'
instance_id = 'f54880eb-7e09-41aa-8778-97194332068a'

print(f'Connecting to instance: {instance_id} in {region}')
print()

client = boto3.client('connect', region_name=region)

# Get account ID for ARN
sts = boto3.client('sts', region_name=region)
account_id = sts.get_caller_identity()['Account']
instance_arn = f"arn:aws:connect:{region}:{account_id}:instance/{instance_id}"

print(f'Instance ARN: {instance_arn}')
print()

# List phone numbers
print('Phone Numbers:')
try:
    response = client.list_phone_numbers_v2(TargetArn=instance_arn)
    numbers = response.get('ListPhoneNumbersSummaryList', [])
    if numbers:
        for num in numbers:
            phone = num.get('PhoneNumber', 'Unknown')
            phone_id = num.get('PhoneNumberId', 'Unknown')
            phone_type = num.get('PhoneNumberType', 'Unknown')
            print(f'  {phone} ({phone_type})')
            print(f'    ID: {phone_id}')
    else:
        print('  No phone numbers claimed yet')
except Exception as e:
    print(f'  Error: {e}')

print()

# List contact flows
print('Contact Flows:')
try:
    response = client.list_contact_flows(
        InstanceId=instance_id,
        ContactFlowTypes=['CONTACT_FLOW', 'CUSTOMER_QUEUE', 'CUSTOMER_HOLD', 'AGENT_TRANSFER']
    )
    flows = response.get('ContactFlowSummaryList', [])
    if flows:
        for flow in flows:
            name = flow.get('Name', 'Unknown')
            flow_id = flow.get('Id', 'Unknown')
            flow_type = flow.get('ContactFlowType', 'Unknown')
            print(f'  - {name} ({flow_type})')
            print(f'    ID: {flow_id}')
    else:
        print('  No custom contact flows (using defaults)')
except Exception as e:
    print(f'  Error: {e}')

print()
print('Done!')
