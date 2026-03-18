
import os
import json
from cdss.bedrock.chat import invoke_chat

def test_clinical_query():
    # Setup environment
    os.environ["BEDROCK_CONFIG_SECRET_NAME"] = "cdss-dev/bedrock-config"
    os.environ["AWS_REGION"] = "ap-south-1"
    
    clinical_prompt = """
    A 65-year-old male presents with chest pain radiating to the left arm, sweating, and shortness of breath. 
    Vitals: BP 140/90, HR 105, SpO2 94%. 
    What are the immediate clinical steps and possible differential diagnoses?
    Answer concisely with clinical focus.
    """
    
    print(f"\n--- Testing Clinical Query ---")
    print(f"Prompt: {clinical_prompt.strip()}")
    
    result = invoke_chat(clinical_prompt)
    
    print("-" * 20)
    print(f"Reply: \n{result.reply}")
    print("-" * 20)
    print(f"Safety Disclaimer: {result.safety_disclaimer}")
    print("-" * 20)

if __name__ == "__main__":
    test_clinical_query()
