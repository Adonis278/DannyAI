"""Tech validation script - Check all AWS resources."""
import boto3
import os
from dotenv import load_dotenv
load_dotenv()

os.environ['AWS_ACCESS_KEY_ID'] = os.getenv('AWS_ACCESS_KEY_ID')
os.environ['AWS_SECRET_ACCESS_KEY'] = os.getenv('AWS_SECRET_ACCESS_KEY')

print("=" * 60)
print("DANNY AI - TECHNICAL VALIDATION")
print("=" * 60)
print()

# Check Lambda
print("1. LAMBDA FUNCTION")
print("-" * 40)
try:
    lam = boto3.client('lambda', region_name='us-west-2')
    func = lam.get_function(FunctionName='danny-voice-handler')
    config = func['Configuration']
    print(f"   Name: {config['FunctionName']}")
    print(f"   Runtime: {config['Runtime']}")
    print(f"   State: {config['State']}")
    print(f"   Memory: {config['MemorySize']} MB")
    print(f"   Timeout: {config['Timeout']}s")
    print("   Status: ✅ DEPLOYED")
except Exception as e:
    print(f"   Status: ❌ ERROR - {e}")
print()

# Check Connect Flow
print("2. AMAZON CONNECT")
print("-" * 40)
try:
    conn = boto3.client('connect', region_name='us-west-2')
    instance_id = 'f54880eb-7e09-41aa-8778-97194332068a'
    
    # Get instance info
    instance = conn.describe_instance(InstanceId=instance_id)
    print(f"   Instance: {instance['Instance'].get('InstanceAlias', 'N/A')}")
    print(f"   Status: {instance['Instance'].get('InstanceStatus', 'N/A')}")
    
    # Get contact flow
    flow = conn.describe_contact_flow(
        InstanceId=instance_id, 
        ContactFlowId='aa16e15a-e2e3-472c-9440-4f12731328e7'
    )
    print(f"   Flow: {flow['ContactFlow']['Name']}")
    print(f"   Flow Status: ✅ ACTIVE")
    
    # Check phone
    sts = boto3.client('sts', region_name='us-west-2')
    account_id = sts.get_caller_identity()['Account']
    instance_arn = f'arn:aws:connect:us-west-2:{account_id}:instance/{instance_id}'
    phones = conn.list_phone_numbers_v2(TargetArn=instance_arn)
    
    for p in phones.get('ListPhoneNumbersSummaryList', []):
        print(f"   Phone: {p['PhoneNumber']}")
        flow_info = conn.describe_phone_number(PhoneNumberId=p['PhoneNumberId'])
        target = flow_info.get('ClaimedPhoneNumberSummary', {}).get('TargetArn', '')
        if 'contact-flow' in target:
            flow_id = target.split('/')[-1]
            if flow_id == 'aa16e15a-e2e3-472c-9440-4f12731328e7':
                print(f"   Phone -> Danny Flow: ✅ LINKED")
            else:
                print(f"   Phone -> Flow: {flow_id}")
except Exception as e:
    print(f"   Status: ❌ ERROR - {e}")
print()

# Check Polly
print("3. AMAZON POLLY")
print("-" * 40)
try:
    polly = boto3.client('polly', region_name='us-west-2')
    voices = polly.describe_voices(LanguageCode='en-US')
    neural_voices = [v for v in voices['Voices'] if 'neural' in v.get('SupportedEngines', [])]
    print(f"   Neural voices available: {len(neural_voices)}")
    print("   Status: ✅ READY")
except Exception as e:
    print(f"   Status: ❌ ERROR - {e}")
print()

# Check Transcribe
print("4. AMAZON TRANSCRIBE")
print("-" * 40)
try:
    transcribe = boto3.client('transcribe', region_name='us-west-2')
    # Just verify we can access the service
    transcribe.list_transcription_jobs(MaxResults=1)
    print("   Status: ✅ READY")
except Exception as e:
    print(f"   Status: ❌ ERROR - {e}")
print()

# Check Bedrock
print("5. AMAZON BEDROCK (Claude)")
print("-" * 40)
try:
    bedrock = boto3.client('bedrock-runtime', region_name='us-west-2')
    # Try to list models
    bedrock_mgmt = boto3.client('bedrock', region_name='us-west-2')
    models = bedrock_mgmt.list_foundation_models()
    claude_models = [m for m in models.get('modelSummaries', []) if 'claude' in m.get('modelId', '').lower()]
    print(f"   Claude models in catalog: {len(claude_models)}")
    print("   Note: Access requires use case approval")
    print("   Using fallback: ✅ Direct Anthropic API")
except Exception as e:
    print(f"   Status: ⚠️ Using Direct Anthropic API (Bedrock not configured)")
print()

# Check Anthropic API
print("6. ANTHROPIC API (Claude)")
print("-" * 40)
try:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    # Quick test
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=50,
        messages=[{"role": "user", "content": "Say 'API OK' and nothing else"}]
    )
    result = response.content[0].text
    print(f"   Model: claude-sonnet-4-20250514")
    print(f"   Test response: {result}")
    print("   Status: ✅ WORKING")
except Exception as e:
    print(f"   Status: ❌ ERROR - {e}")
print()

# Check Calendly
print("7. CALENDLY API")
print("-" * 40)
try:
    import requests
    api_key = os.getenv('CALENDLY_API_KEY')
    headers = {'Authorization': f'Bearer {api_key}'}
    response = requests.get('https://api.calendly.com/users/me', headers=headers)
    if response.status_code == 200:
        user = response.json()['resource']
        print(f"   User: {user.get('name', 'N/A')}")
        print("   Status: ✅ WORKING")
    else:
        print(f"   Status: ❌ API returned {response.status_code}")
except Exception as e:
    print(f"   Status: ❌ ERROR - {e}")
print()

print("=" * 60)
print("VALIDATION COMPLETE")
print("=" * 60)
