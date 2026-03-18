import boto3
import json

def get_secret():
    client = boto3.client('secretsmanager', region_name='ap-south-1')
    response = client.get_secret_value(SecretId='cdss-dev/rds-config')
    
    secret_string = response.get('SecretString')
    if secret_string:
        print(json.dumps(json.loads(secret_string), indent=2))
        
if __name__ == "__main__":
    get_secret()
