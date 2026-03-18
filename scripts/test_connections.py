import sys
sys.path.append("src")

print("\nTesting direct Bedrock Invoke...")
try:
    from cdss.bedrock.chat import invoke_chat
    res = invoke_chat("Hello, can you help me?")
    print(f"Bedrock Test Reply: {res.reply}...")
except Exception as e:
    print(f"Bedrock Test Error: {e}")
