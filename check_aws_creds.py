import boto3
from botocore.exceptions import ClientError, NoCredentialsError

def check_credentials():
    print("--- AWS Credential Validator ---")
    
    # Try to get credentials from session (which looks at env and ~/.aws/credentials)
    session = boto3.Session()
    credentials = session.get_credentials()
    
    if not credentials:
        print("Error: No credentials found. Please set them first.")
        return

    access_key = credentials.access_key
    print(f"Checking Access Key ID: {access_key[:4]}...{access_key[-4:] if len(access_key) > 4 else ''}")

    if not access_key.startswith('AKIA') and not access_key.startswith('ASIA'):
        print("Warning: Your Access Key ID does not start with 'AKIA' or 'ASIA'.")
        print("AWS Access Key IDs typically look like: AKIAIOSFODNN7EXAMPLE")

    try:
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        print("SUCCESS! Credentials are valid.")
        print(f"Account ID: {identity['Account']}")
        print(f"Arn: {identity['Arn']}")
    except ClientError as e:
        print(f"FAILED: {e}")
        if 'InvalidClientTokenId' in str(e):
            print("\nTip: 'InvalidClientTokenId' usually means the Access Key ID is wrong.")
        elif 'SignatureDoesNotMatch' in str(e):
            print("\nTip: 'SignatureDoesNotMatch' usually means the Secret Access Key is wrong.")
    except NoCredentialsError:
        print("Error: No credentials found.")

if __name__ == "__main__":
    check_credentials()
