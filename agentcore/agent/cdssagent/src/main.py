import os
from strands import Agent
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from mcp_client.client import get_streamable_http_mcp_client
from model.load import load_model

app = BedrockAgentCoreApp()
log = app.logger

MEMORY_ID = os.getenv("BEDROCK_AGENTCORE_MEMORY_ID")
REGION = os.getenv("AWS_REGION")

# Import AgentCore Gateway as Streamable HTTP MCP Client
mcp_client = get_streamable_http_mcp_client()

AGENT_CONFIGS = {
    "patient": {
        "description": "History, summaries, surgery readiness, ABDM",
        "system_prompt": """You are the CDSS Patient Agent. Your role is to manage patient histories, generate clinical summaries, and assess surgery readiness.
- Use `get_patient` to see full clinical state, vitals, and conditions.
- Use `list_patients` to search for patient IDs or status.
- Use `get_abdm_record` for external EHR lookups.
Always include a safety disclaimer: 'AI-generated clinical data is for decision support only. All decisions require medical judgment.'""",
        "tools": ["get_patient", "list_patients", "get_abdm_record"]
    },
    "surgery": {
        "description": "Classification, checklists, requirements, procedural support",
        "system_prompt": """You are the CDSS Surgery Agent. Your role is to handle surgery classification, procedural checklists, and complexity analysis.
- Use `get_surgeries` to see upcoming cases.
- Use `get_surgery` for detailed checklist and requirement status.
- Use `get_ot_status` to check where a surgery is assigned.
Always include a safety disclaimer: 'Surgical decisions must be verified by a qualified surgeon.'""",
        "tools": ["get_surgeries", "get_surgery", "get_ot_status"]
    },
    "resource": {
        "description": "OTs, equipment, staff availability, conflicts",
        "system_prompt": """You are the CDSS Resource Agent. Your role is to manage hospital resources like Operating Theaters and equipment.
- Use `get_ot_status` to see current room availability.
- Use `get_hospitals` to find beds or specialty facilities.
Always include a safety disclaimer: 'Resource availability is indicative and must be confirmed with the facility.'""",
        "tools": ["get_ot_status", "get_hospitals"]
    },
    "scheduling": {
        "description": "Booking, find-replacement, utilization",
        "system_prompt": """You are the CDSS Scheduling Agent. Your role is to optimize surgical bookings and manage staff schedules.
- Use `get_schedule` to see current slot allocations.
- Use `find_replacement` when staff are unavailable for a specific speciality.
Always include a safety disclaimer: 'Schedule changes must be approved by the department head.'""",
        "tools": ["get_schedule", "find_replacement"]
    },
    "engagement": {
        "description": "Medications, reminders, consultations, adherence",
        "system_prompt": """You are the CDSS Engagement Agent. Your role is to manage patient medication adherence and reminders.
- Use `get_medications` to see a patient's current drug list.
- Use `get_reminders_adherence` to evaluate if a patient is following their protocol.
Always include a safety disclaimer: 'Medication advice is for decision support only.'""",
        "tools": ["get_medications", "get_reminders_adherence"]
    }
}

DEFAULT_PROMPT = """You are the CDSS General Agent. You provides clinical decision support for Indian hospitals.
- Be conservative. Recommend clinician review for serious symptoms.
- You have access to tools for hospitals, patients, surgeries, and resources.
Always include a safety disclaimer."""

# ─── Orchestrator ──────────────────────────────────────────────────

@app.entrypoint
async def invoke(payload, context):
    session_id = getattr(context, 'session_id', 'default')
    user_id = payload.get("user_id") or 'default-user'
    intent = (payload.get("intent") or "").strip().lower()
    
    # Configure memory
    session_manager = None
    if MEMORY_ID:
        session_manager = AgentCoreMemorySessionManager(
            AgentCoreMemoryConfig(
                memory_id=MEMORY_ID,
                session_id=session_id,
                actor_id=user_id,
                retrieval_config={
                    f"/facts/{user_id}/": RetrievalConfig(top_k=10, relevance_score=0.4),
                    f"/preferences/{user_id}/": RetrievalConfig(top_k=5, relevance_score=0.5),
                    f"/summaries/{user_id}/{session_id}/": RetrievalConfig(top_k=5, relevance_score=0.4),
                    f"/episodes/{user_id}/{session_id}/": RetrievalConfig(top_k=5, relevance_score=0.4),
                }
            ),
            REGION
        )

    # 1. Determine which agent config to use
    config = AGENT_CONFIGS.get(intent)
    system_prompt = config["system_prompt"] if config else DEFAULT_PROMPT
    allowed_tools = config["tools"] if config else None

    with mcp_client as client:
        # 2. Get and filter tools
        all_tools = client.list_tools_sync()
        
        # Debug tool attributes if needed
        if all_tools:
            log.info(f"Available tools sample: {dir(all_tools[0])}")

        if allowed_tools:
            # Match tool names robustly. MCPAgentTool might store name in .info or .metadata or as .name
            tools = []
            for t in all_tools:
                # Try common attribute locations for name
                name = getattr(t, "name", None) or \
                       (getattr(t, "info", None).name if getattr(t, "info", None) and hasattr(t.info, "name") else None) or \
                       (getattr(t, "metadata", None).get("name") if getattr(t, "metadata", None) and isinstance(t.metadata, dict) else None)
                
                if name and any(str(at) in str(name) for at in allowed_tools):
                    tools.append(t)
        else:
            tools = all_tools

        # 3. Create agent instance
        agent = Agent(
            model=load_model(),
            session_manager=session_manager,
            system_prompt=system_prompt,
            tools=tools
        )

        # 4. Execute and stream response
        user_prompt = (payload.get("prompt") or "").strip()
        if intent and user_prompt:
            user_prompt = f"[intent={intent}] {user_prompt}"
        
        stream = agent.stream_async(user_prompt or f"[intent={intent}]")

        async for event in stream:
            if "data" in event and isinstance(event["data"], str):
                yield event["data"]

if __name__ == "__main__":
    app.run()