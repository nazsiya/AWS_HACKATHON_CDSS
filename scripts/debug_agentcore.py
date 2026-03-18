import boto3
import json
import uuid

AGENT_RUNTIME_ARN = "arn:aws:bedrock-agentcore:ap-south-1:746412758276:runtime/cdssagent_Agent-t2U3Q67I4j"

client = boto3.client("bedrock-agentcore", region_name="ap-south-1")

payload = {
    "intent": "patient",
    "prompt": "Give me a summary of patient PT-1001",
    "patient_id": "PT-1001"
}

print(f"Invoking AgentCore: {AGENT_RUNTIME_ARN}")
try:
    response = client.invoke_agent_runtime(
        agentRuntimeArn=AGENT_RUNTIME_ARN,
        runtimeSessionId=str(uuid.uuid4()),
        payload=json.dumps(payload).encode(),
        contentType="application/json"
    )
    
    body = response.get("response")
    print("Full response object:")
    print(response)
    if body:
        result = body.read().decode() if hasattr(body, "read") else body
        print("Success! Response:")
        print(result)
    else:
        print("Response body is empty.")
except Exception as e:
    print(f"Error: {e}")
