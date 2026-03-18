
import os
import json
from cdss.bedrock.chat import invoke_chat

def test_general_query():
    prompt = "who is going to win the war between iran an Israle."
    print(f"\n--- Testing General Query: {prompt} ---")
    
    # Ensure environment is set
    os.environ["BEDROCK_CONFIG_SECRET_NAME"] = "cdss-dev/bedrock-config"
    os.environ["AWS_REGION"] = "ap-south-1"
    
    result = invoke_chat(prompt)
    print(f"Reply: {result.reply}")
    print(f"Disclaimer: {result.safety_disclaimer}")

if __name__ == "__main__":
    test_general_query()
