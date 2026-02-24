"""Deploy Danny Lambda function to AWS."""
import os
import json
import zipfile
import tempfile
import shutil
import boto3
from dotenv import load_dotenv

load_dotenv()

# Configuration
AWS_REGION = os.getenv("CONNECT_REGION", "us-west-2")
LAMBDA_NAME = "danny-voice-handler"
LAMBDA_ROLE_NAME = "danny-lambda-role"

# Set credentials
os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID", "")
os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY", "")

def create_lambda_role(iam_client):
    """Create IAM role for Lambda if it doesn't exist."""
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        # Check if role exists
        response = iam_client.get_role(RoleName=LAMBDA_ROLE_NAME)
        print(f"  Role already exists: {LAMBDA_ROLE_NAME}")
        return response['Role']['Arn']
    except iam_client.exceptions.NoSuchEntityException:
        pass
    
    print(f"  Creating role: {LAMBDA_ROLE_NAME}")
    response = iam_client.create_role(
        RoleName=LAMBDA_ROLE_NAME,
        AssumeRolePolicyDocument=json.dumps(trust_policy),
        Description="Lambda role for Danny voice handler"
    )
    role_arn = response['Role']['Arn']
    
    # Attach policies
    policies = [
        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        "arn:aws:iam::aws:policy/AmazonPollyReadOnlyAccess",
        "arn:aws:iam::aws:policy/AmazonTranscribeFullAccess",
        "arn:aws:iam::aws:policy/AmazonConnect_FullAccess",
    ]
    
    for policy in policies:
        print(f"  Attaching policy: {policy.split('/')[-1]}")
        iam_client.attach_role_policy(RoleName=LAMBDA_ROLE_NAME, PolicyArn=policy)
    
    # Wait for role to propagate
    import time
    print("  Waiting for role to propagate (10s)...")
    time.sleep(10)
    
    return role_arn


def create_deployment_package():
    """Create ZIP package for Lambda deployment."""
    print("Creating deployment package...")
    
    # Create temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Install dependencies
        print("  Installing dependencies...")
        import subprocess
        subprocess.run([
            "pip", "install", 
            "anthropic", "strands-agents", "requests",
            "-t", temp_dir,
            "--quiet"
        ], check=True)
        
        # Copy danny module
        danny_src = os.path.join(os.path.dirname(__file__), "danny")
        danny_dst = os.path.join(temp_dir, "danny")
        shutil.copytree(danny_src, danny_dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        
        # Create lambda handler wrapper at root level (uses Strands handler)
        wrapper_code = '''"""Lambda entry point for Danny AI (Strands Framework)."""
import os
import json

# Set environment variables for Lambda
os.environ.setdefault("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))
# Use DANNY_REGION since AWS_REGION is reserved
os.environ.setdefault("AWS_REGION", os.environ.get("DANNY_REGION", os.environ.get("AWS_REGION", "us-west-2")))
os.environ.setdefault("USE_BEDROCK", "false")

from danny.strands_lambda_handler import handler as danny_handler

def handler(event, context):
    """Main Lambda handler."""
    return danny_handler(event, context)
'''
        with open(os.path.join(temp_dir, "lambda_function.py"), "w") as f:
            f.write(wrapper_code)
        
        # Create ZIP file
        zip_path = os.path.join(os.path.dirname(__file__), "lambda_deployment.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(temp_dir):
                # Skip __pycache__ directories
                dirs[:] = [d for d in dirs if d != '__pycache__']
                for file in files:
                    if file.endswith('.pyc'):
                        continue
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, temp_dir)
                    zf.write(file_path, arc_name)
        
        # Get file size
        size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"  Package created: lambda_deployment.zip ({size_mb:.2f} MB)")
        
        return zip_path


def deploy_lambda(lambda_client, iam_client):
    """Deploy or update the Lambda function."""
    
    # Get or create role
    print("Setting up IAM role...")
    role_arn = create_lambda_role(iam_client)
    
    # Create deployment package
    zip_path = create_deployment_package()
    
    with open(zip_path, 'rb') as f:
        zip_content = f.read()
    
    # Environment variables for Lambda (AWS_REGION is reserved, use DANNY_REGION)
    env_vars = {
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
        "DANNY_REGION": AWS_REGION,
        "USE_BEDROCK": "false",
        "CALENDLY_API_KEY": os.getenv("CALENDLY_API_KEY", ""),
        "PRACTICE_NAME": os.getenv("PRACTICE_NAME", "Sample Dental Practice"),
    }
    
    try:
        # Check if function exists
        lambda_client.get_function(FunctionName=LAMBDA_NAME)
        
        # Update existing function
        print(f"Updating Lambda function: {LAMBDA_NAME}")
        
        # Wait for any pending updates
        import time
        for attempt in range(10):
            try:
                lambda_client.update_function_code(
                    FunctionName=LAMBDA_NAME,
                    ZipFile=zip_content
                )
                print("  Code updated!")
                break
            except lambda_client.exceptions.ResourceConflictException:
                print(f"  Waiting for previous update... ({attempt+1}/10)")
                time.sleep(5)
        
        # Wait before updating configuration
        time.sleep(3)
        
        # Update configuration
        for attempt in range(10):
            try:
                lambda_client.update_function_configuration(
                    FunctionName=LAMBDA_NAME,
                    Environment={"Variables": env_vars},
                    Timeout=30,
                    MemorySize=256
                )
                print("  Configuration updated!")
                break
            except lambda_client.exceptions.ResourceConflictException:
                print(f"  Waiting for code update... ({attempt+1}/10)")
                time.sleep(5)
        
    except lambda_client.exceptions.ResourceNotFoundException:
        # Create new function
        print(f"Creating Lambda function: {LAMBDA_NAME}")
        lambda_client.create_function(
            FunctionName=LAMBDA_NAME,
            Runtime="python3.11",
            Role=role_arn,
            Handler="lambda_function.handler",
            Code={"ZipFile": zip_content},
            Description="Danny AI Voice Handler for Amazon Connect",
            Timeout=30,
            MemorySize=256,
            Environment={"Variables": env_vars}
        )
        print("  Function created!")
    
    # Get function ARN
    response = lambda_client.get_function(FunctionName=LAMBDA_NAME)
    function_arn = response['Configuration']['FunctionArn']
    print(f"  ARN: {function_arn}")
    
    return function_arn


def add_connect_permission(lambda_client, function_arn):
    """Allow Connect to invoke the Lambda function."""
    print("Adding Connect invoke permission...")
    
    # Get account ID
    sts = boto3.client('sts', region_name=AWS_REGION)
    account_id = sts.get_caller_identity()['Account']
    
    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_NAME,
            StatementId="AllowConnectInvoke",
            Action="lambda:InvokeFunction",
            Principal="connect.amazonaws.com",
            SourceAccount=account_id
        )
        print("  Permission added!")
    except lambda_client.exceptions.ResourceConflictException:
        print("  Permission already exists")


def main():
    """Main deployment function."""
    print("=" * 50)
    print("Danny Lambda Deployment")
    print("=" * 50)
    print()
    
    # Initialize clients
    lambda_client = boto3.client('lambda', region_name=AWS_REGION)
    iam_client = boto3.client('iam', region_name=AWS_REGION)
    
    # Deploy function
    function_arn = deploy_lambda(lambda_client, iam_client)
    
    # Add Connect permission
    add_connect_permission(lambda_client, function_arn)
    
    print()
    print("=" * 50)
    print("Deployment Complete!")
    print("=" * 50)
    print()
    print(f"Lambda ARN: {function_arn}")
    print()
    print("Next steps:")
    print("1. Go to Amazon Connect console")
    print("2. Create a contact flow that invokes this Lambda")
    print("3. Associate your phone number with the flow")
    
    return function_arn


if __name__ == "__main__":
    main()
