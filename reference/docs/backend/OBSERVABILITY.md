# Observability (AC-1, AC-2, AC-4)

Triage, Hospital Matcher, and Routing Lambdas emit structured logs for **trace review** and **medical audit**. Use CloudWatch Logs Insights to query by source and duration.

---

## Tracing and log delivery – every agent

Each agent path **must** emit the following so observability is consistent:

| Check | Triage | Hospital Matcher | Routing |
|-------|--------|-------------------|---------|
| `source=` (agentcore \| converse \| bedrock_agent) | ✅ | ✅ | ✅ (AC-4) |
| `duration_ms=` | ✅ | ✅ | ✅ (AC-4) |
| `request_id=` or `aws_request_id=` on success | ✅ | ✅ | ✅ (AC-4) |
| No PHI in log message text | ✅ | ✅ | ✅ |

When adding a new agent or Lambda, add the same pattern and document it here.

---

## Log fields

| Lambda        | Log message pattern | Use |
|---------------|---------------------|-----|
| **Triage**    | `Triage source=agentcore \| converse \| bedrock_agent duration_ms=...` | Which path ran; latency |
| **Triage**    | `Triage success request_id=... aws_request_id=...` | Correlate assessment with Lambda request |
| **Triage**   | `Persisted triage assessment id=...` | DB row for audit |
| **Hospital Matcher** | `HospitalMatcher source=agentcore \| converse \| bedrock_agent duration_ms=...` | Which path ran; latency |
| **Hospital Matcher** | `HospitalMatcher success request_id=...` | Correlate with Lambda request |
| **Routing**   | `Routing source=agentcore duration_ms=...` | Which path ran; latency (AC-4) |
| **Routing**   | `Routing success request_id=...` | Correlate with Lambda request (AC-4) |

---

## CloudWatch Logs Insights

**Triage – count by source (last 24h):**
```text
fields @timestamp, @message
| filter @message like /Triage source=/
| parse @message "Triage source=* duration_ms=*" as source, duration_ms
| stats count() by source
```

**Triage – p99 duration (last 24h):**
```text
fields @timestamp, @message
| filter @message like /Triage source=/
| parse @message "Triage source=* duration_ms=*" as source, duration_ms
| stats pct(duration_ms, 99) by source
```

**Trace review (medical audit):** Use `request_id` (UUID) or `aws_request_id` (Lambda request ID) from the success log line to find the same request in other log lines or in Aurora (`triage_assessments.request_id`).

**Routing – count by source (last 24h):**
```text
fields @timestamp, @message
| filter @message like /Routing source=/
| parse @message "Routing source=* duration_ms=*" as source, duration_ms
| stats count() by source
```

**Routing – p99 duration (last 24h):**
```text
fields @timestamp, @message
| filter @message like /Routing source=/
| parse @message "Routing source=* duration_ms=*" as source, duration_ms
| stats pct(duration_ms, 99) by source
```

---

## Dashboards

You can create a CloudWatch dashboard with widgets that run the above queries, or use the default Lambda metrics (Invocations, Duration, Errors). For full AgentCore tracing (Runtime spans), use the Bedrock AgentCore console when available.

---

## AC-2 Triage on AgentCore

When `USE_AGENTCORE_TRIAGE=true` and `TRIAGE_AGENT_RUNTIME_ARN` is set, POST /triage uses the AgentCore Runtime triage agent. Logs show `Triage source=agentcore`. Persistence to Aurora is unchanged; `request_id` and assessment `id` remain the primary keys for audit.

---

## AC-4 Routing

When POST /route is implemented, the Routing Lambda must log `Routing source=agentcore duration_ms=...` and `Routing success request_id=...` (use `aws_request_id` or a generated UUID). Same pattern as Triage and Hospital Matcher for consistent trace review.
