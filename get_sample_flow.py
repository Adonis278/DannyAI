"""Get sample Lambda flow info."""
import os
import boto3
from dotenv import load_dotenv

load_dotenv()

os.environ['AWS_ACCESS_KEY_ID'] = os.getenv('AWS_ACCESS_KEY_ID')
os.environ['AWS_SECRET_ACCESS_KEY'] = os.getenv('AWS_SECRET_ACCESS_KEY')

client = boto3.client('connect', region_name='us-west-2')
instance_id = 'f54880eb-7e09-41aa-8778-97194332068a'

# Get the Sample Lambda integration flow
response = client.list_contact_flows(InstanceId=instance_id)
for flow in response.get('ContactFlowSummaryList', []):
    name = flow.get('Name', '')
    if 'Lambda' in name:
        flow_id = flow['Id']
        print(f'Found: {name}')
        print(f'  Flow ID: {flow_id}')
        
        # Get flow content
        detail = client.describe_contact_flow(
            InstanceId=instance_id, 
            ContactFlowId=flow_id
        )
        
        content = detail['ContactFlow'].get('Content', '')
        print(f'  Content length: {len(content)}')
        
        # Save content for reference
        import json
        with open('sample_lambda_flow.json', 'w') as f:
            try:
                parsed = json.loads(content)
                json.dump(parsed, f, indent=2)
                print('  Saved to sample_lambda_flow.json')
            except:
                f.write(content)
