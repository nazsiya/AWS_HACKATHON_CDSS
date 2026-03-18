# MCP & Gateway Research for Emergency Medical Triage

**Purpose:** Identify available MCP servers for hospital/medical data and define Gateway strategy.

---

## MCP Servers Researched

### India-focused

| Server | Use Case | Hospital Data? | Notes |
|--------|----------|----------------|-------|
| **Eka MCP Server** | Indian drugs, treatment protocols | No | 500k+ drugs, ICMR/RSSDI protocols. Requires Eka API key from eka.care. Best fit for **Triage** (protocols, drug lookup). |
| [eka-care/eka_mcp_server](https://github.com/eka-care/eka_mcp_server) | | | MIT license |

### US / generic

| Server | Use Case | Hospital Data? | Notes |
|--------|----------|----------------|-------|
| **NPI Registry MCP** | US provider/facility search | Yes (US) | National Provider Identifier, location search. US-only. |
| **AWS HealthLake MCP** | FHIR data in HealthLake | Yes (if loaded) | Requires HealthLake + FHIR data. Overkill for hackathon. |
| **Stedi MCP** | Eligibility/benefits verification | No | Payer workflows. |
| **HealthEx MCP** | Patient health records | No | FHIR/C-CDA via OAuth. |

### Conclusion: Hospital directory for India

**No public MCP server provides Indian hospital/facility directory.** Options:

1. **Gateway + Lambda target** – Lambda returns synthetic or real hospital data; Gateway exposes as MCP tools. (Current plan.)
2. **Build custom MCP server** – Expose hospital DB/API via MCP. Higher effort.
3. **Eka MCP** – Use for Triage (protocols, drugs); does not solve hospital matching.

---

## Recommended Gateway Strategy

| Component | Source | Notes |
|-----------|--------|-------|
| **Hospital matching** | Gateway + Lambda (synthetic) | Lambda tool `get_hospitals(severity, limit)` returns synthetic Indian hospitals. Replace with real data when available. |
| **Triage protocols/drugs** | Eka MCP (optional) | Add Eka as Gateway target for Indian treatment protocols. Requires Eka API key. |
| **Patient context** | AgentCore Memory | Short/long-term memory; no MCP needed. |

### Eka MCP integration (optional)

- **Tools:** Indian drug search, treatment protocol search
- **Benefit:** Triage agent can query ICMR protocols and drug info
- **Requirement:** API key from [console.eka.care](https://console.eka.care)
- **Gateway:** Add Eka as MCP target (stdio or HTTP) if AgentCore Gateway supports external MCP URLs

---

## Next Steps

1. **Gateway + Lambda** – Create Gateway, add Lambda target with `get_hospitals` tool.
2. **Wire Hospital Matcher agent** – Connect agent to Gateway for hospital tool (replace in-agent synthetic).
3. **Eka (optional)** – If Eka API key available, add Eka MCP as Gateway target for Triage.
