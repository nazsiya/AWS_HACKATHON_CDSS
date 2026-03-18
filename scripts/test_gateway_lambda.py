import boto3
import json

def test_lambda():
    client = boto3.client('lambda', region_name='ap-south-1')
    
    print("Testing get_ot_status tool...")
    payload = {"__tool": "get_ot_status"}
    response = client.invoke(
        FunctionName='cdss-dev-gateway-get-hospitals',
        Payload=json.dumps(payload)
    )
    result = json.loads(response['Payload'].read().decode('utf-8'))
    print(json.dumps(result, indent=2))
    print(f"Source: {result.get('source', 'Unknown')}")

if __name__ == "__main__":
    test_lambda()
