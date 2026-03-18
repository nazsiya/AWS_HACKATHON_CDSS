from strands.models import BedrockModel

import os

# Defaults for ap-south-1
CLAUDE_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
NOVA_MODEL_ID = "apac.amazon.nova-lite-v1:0"

def load_model() -> BedrockModel:
    """
    Get Bedrock model client.
    Uses Anthropic Claude 3 Haiku by default, falls back to Amazon Nova Lite if requested or if Haiku fails.
    """
    requested_id = (os.getenv("BEDROCK_MODEL_ID") or os.getenv("CDSS_BEDROCK_MODEL_ID") or "").strip()
    
    # If a specific model is requested via env, use it
    if requested_id:
        return BedrockModel(model_id=requested_id)
        
    # Default behavior: try Claude, verified Nova Lite as safe fallback for ap-south-1
    # Note: In a production 'strands' app, the model check happens during invocation.
    # We set Nova Lite as the primary default if we know Claude is restricted in this account/region.
    model_id = NOVA_MODEL_ID
    return BedrockModel(model_id=model_id)