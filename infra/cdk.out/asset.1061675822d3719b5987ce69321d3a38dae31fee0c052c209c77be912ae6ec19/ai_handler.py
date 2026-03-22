import json
import os
import sys
from pathlib import Path

# Add agents path to import shared components
agents_path = str(Path(__file__).resolve().parent.parent.parent / "agents")
if agents_path not in sys.path:
    sys.path.append(agents_path)

from shared.bedrock_client import BedrockClient
from shared.config import SYSTEM_PROMPTS, AGENT_NAMES

def lambda_handler(event, context):
    """
    Handles AI agent requests (chat, specific queries).
    Expected body: { "message": "...", "patient_id": "...", "agent_type": "patient" }
    """
    http_method = event.get('httpMethod', 'POST')
    
    if http_method == 'OPTIONS':
        return {
            'statusCode': 204,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            },
            'body': ''
        }

    if http_method != 'POST':
        return {'statusCode': 405, 'body': json.dumps({'error': 'Method not allowed'})}

    try:
        body = json.loads(event.get('body', '{}'))
        user_message = body.get('message')
        patient_id = body.get('patient_id')
        agent_type = body.get('agent_type', 'patient')
        history = body.get('history', [])

        if not user_message:
            return {'statusCode': 400, 'body': json.dumps({'error': 'message is required'})}

        bedrock = BedrockClient()
        system_prompt = SYSTEM_PROMPTS.get(agent_type, SYSTEM_PROMPTS.get("supervisor"))

        # In a real system, we'd fetch patient data here to augment the prompt.
        # For now, we'll pass the message and history to Bedrock.
        # If patient_id is provided, we could fetch details from the DB here.
        
        response = bedrock.invoke(
            user_message=user_message,
            system_prompt=system_prompt,
            conversation_history=history
        )

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'response': response['content'],
                'agent': AGENT_NAMES.get(agent_type, "Assistant"),
                'model': response['model']
            })
        }

    except Exception as e:
        print(f"AI Handler Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
