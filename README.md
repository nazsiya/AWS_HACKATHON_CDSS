# CDSS — Clinical Decision Support System

**Multi-agent AI platform for Indian hospitals** — DISHA compliant, serverless-first, on AWS (ap-south-1). Target budget: **<$100/month**.

## Stack

| Component | Technology |
|-----------|------------|
| **AI** | Amazon Bedrock (Claude 3 Haiku) |
| **Compute** | AWS Lambda (Python 3.12) |
| **API** | Amazon API Gateway (REST + WebSocket) |
| **Data** | DynamoDB, S3, RDS PostgreSQL (optional) |
| **RAG** | Amazon OpenSearch (patient history vectors) |
| **Frontend** | AWS Amplify (React) |
| **ML/NLP** | Amazon Transcribe, Comprehend Medical, Translate |
| **IaC** | Terraform |

## Agents

Five domain agents orchestrated by a **Supervisor**:

- **Patient Agent** — History retrieval, RAG summaries, create/update patient, getSummary  
- **Surgery Planning Agent** — OT checklists, protocols, analyseSurgery, generateChecklist  
- **Resource Agent** — OT availability, equipment, checkOT, allocateEquipment  
- **Scheduling Agent** — Appointments, OT booking, bookSlot, resolveConflict  
- **Engagement Agent** — Reminders (multilingual), escalation, sendReminder, escalateToDoctor  

## Project structure

```
├── src/cdss/
│   ├── api/           # Lambda handlers, middleware, routes, WebSocket
│   ├── agents/        # Bedrock multi-agent (Supervisor + 5 agents)
│   ├── core/          # Config, Bedrock client, DISHA, logging
│   ├── models/        # Pydantic models (patient, surgery, resource)
│   └── services/      # RAG, Comprehend Medical, Transcribe, Translate, MCP
├── infrastructure/    # Terraform (Lambda, API Gateway, DynamoDB, S3, EventBridge)
├── tests/             # Unit, integration, e2e
├── docs/              # Architecture, API, deployment
├── DESIGN_IMPLEMENTATION.md
└── README.md
```

## Quick start

1. **Clone and install**

   ```bash
   git clone <repo-url>
   cd CDSS
   pip install -r requirements.txt
   pip install -e .
   ```

2. **Run tests**

   ```bash
   pytest tests/unit -v
   ```

3. **Deploy (Terraform)**

   ```bash
   cd infrastructure
   terraform init
   terraform plan -var stage=dev
   terraform apply -var stage=dev
   ```

4. **Call API**

   Use `terraform output api_gateway_url` and send `POST` to `/cdss/patient`, `/cdss/surgery`, etc. (see [docs/api.md](docs/api.md)).

## Docs

- [Architecture](docs/architecture.md) — Layers, agents, data flow  
- [API](docs/api.md) — REST endpoints and WebSocket  
- [Deployment](docs/deployment.md) — Terraform, env vars, Amplify  
- [Design & implementation](DESIGN_IMPLEMENTATION.md) — Design decisions and implementation guide  

## Compliance

- **DISHA** — Audit logging (CloudWatch), consent, PHI handling  
- **ABDM** — Integration via ABDM/EHR MCP for digital health IDs  
- **Region** — ap-south-1 (Mumbai)  

## License

MIT (or your chosen license).
