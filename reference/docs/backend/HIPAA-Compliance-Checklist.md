# HIPAA / health data compliance checklist (H1–H4)

**Purpose:** Document PHI scope, encryption, access control, and audit logging so the system is suitable for handling protected health information (PHI). See [ROADMAP-NEXT.md](../ROADMAP-NEXT.md) Phase 3 and [ROADMAP-after-AC4.md](./ROADMAP-after-AC4.md) §1.

---

## H1: Document PHI scope

**Goal:** List what we store and classify as PHI/sensitive.

| Data | Where stored | Classification |
|------|--------------|----------------|
| Symptoms (free text) | Request body → Lambda → AgentCore; optionally `triage_assessments` (Aurora) | **PHI** – health-related; can identify condition |
| Vitals (heart_rate, blood_pressure_systolic/diastolic, temperature_celsius, respiratory_rate, spo2) | Request body → Lambda → AgentCore; optionally DB | **PHI** |
| Age, sex | Request body → Lambda → AgentCore; optionally DB | **PHI** (demographic) |
| Triage result (severity, confidence, recommendations, force_high_priority) | Response; optionally `triage_assessments` | **PHI** – clinical assessment |
| Session ID / patient ID | Request body; passed to AgentCore as `runtimeSessionId`; optionally DB | **Identifier** – links to PHI |
| Hospital list, route (origin/destination, directions_url) | Response; not persisted by default | **Context** – location; can be sensitive |
| RMP auth (Cognito Id Token) | API Gateway / Lambda (not stored in app DB) | **Auth** – AWS handles per Cognito |

**Scope summary:** Symptoms, vitals, age, sex, triage result, and session/patient identifiers are PHI or directly link to PHI. Treat all triage and hospital-match payloads as containing or referencing PHI.

---

## H2: Encryption checklist

**Goal:** Confirm encryption at rest and in transit; document.

| Item | Status | Notes |
|------|--------|--------|
| **Aurora encryption at rest** | ✅ | `storage_encrypted = true` in [infrastructure/rds.tf](../../infrastructure/rds.tf). AWS-managed keys. |
| **Secrets Manager** | ✅ | API config, gateway-config, RDS config, Eka config. AWS encrypts at rest; TLS in transit. |
| **TLS in transit** | ✅ | API Gateway HTTPS only; Lambda ↔ Aurora via Data API (HTTPS); Lambda ↔ Bedrock/Gateway over HTTPS. |
| **S3 (if used)** | ✅ | [infrastructure/s3.tf](../../infrastructure/s3.tf) – server-side encryption configured for deployment buckets. |

No PHI is stored in S3 by the application; deployment artifacts only. **Conclusion:** Encryption at rest (Aurora, Secrets Manager, S3) and in transit (HTTPS) is in place.

---

## H3: Access control

**Goal:** IAM least privilege; no PHI in log messages; restrict who can read api_config / gateway-config / Eka.

| Item | Action / status |
|------|------------------|
| **IAM least privilege** | **Audited.** Lambdas use execution roles scoped to specific resources. Secrets Manager: each Lambda has `GetSecretValue` only on the secret(s) it needs (e.g. triage: rds_config + gateway_config; route: gateway_config; gateway_eka: eka_config). No `Resource = "*"` for secretsmanager. See [infrastructure/triage.tf](../../infrastructure/triage.tf), [route.tf](../../infrastructure/route.tf), [gateway_eka.tf](../../infrastructure/gateway_eka.tf), [gateway_maps.tf](../../infrastructure/gateway_maps.tf). |
| **No PHI in log messages** | **Done.** Application code does not log symptoms, vitals, or full request/response bodies. Triage and Hospital Matcher handlers log only `type(e).__name__` on validation errors (not exception detail that could contain field values). Eka tool calls log "Triage calling Eka: search_indian_medications" / "search_treatment_protocols" without drug_name or query content. Logs use request_id, severity, duration_ms, rmp_sub (for audit). See [OBSERVABILITY.md](./OBSERVABILITY.md). |
| **Secrets access** | Only the Lambdas that need each secret have GetSecretValue on that secret's ARN. Scripts (load_api_config, load_gateway_config, setup_agentcore_gateway) run with user/CI credentials; no broad `secretsmanager:GetSecretValue` on `*`. |
| **API Gateway** | RMP auth (Cognito) restricts who can call POST /triage, /hospitals, /route. |

**Conclusion:** H3 complete. IAM is scoped; PHI redacted from logs; secrets access is per-resource.

---

## H4: Audit logging

**Goal:** Document what we have; add who-accessed-what if required.

| Item | Status | Notes |
|------|--------|--------|
| **Request ID** | ✅ | Propagated in API and Lambda; can correlate logs. |
| **triage_assessments.id** | ✅ | Primary key for stored assessments; supports “what was recorded.” |
| **CloudWatch Logs** | ✅ | Lambda logs (with request_id); Bedrock AgentCore runtime logs. |
| **Who accessed what** | Documented | Option A – CloudTrail: Enable for API Gateway and Lambda; correlate by time + request_id; CloudTrail gives principal. Option B – Audit table: api_access_log (timestamp, request_id, endpoint, principal_id) if queryable who-accessed-which-assessment needed. |

**Conclusion:** H4 complete. Basic audit trail (request_id, DB ids, CloudWatch) in place. Who-accessed-what via CloudTrail + request_id; optional audit table documented.

---

## Summary

| # | Item | Status |
|---|------|--------|
| H1 | Document PHI scope | Done – symptoms, vitals, age, sex, triage result, session/patient ids classified. |
| H2 | Encryption checklist | Done – Aurora, Secrets Manager, TLS, S3 documented. |
| H3 | Access control | Done – IAM audited (scoped secrets); no PHI in logs (redacted Eka tool args, validation errors). |
| H4 | Audit logging | Done – request_id, triage_assessments.id, CloudWatch; who-accessed-what via CloudTrail + request_id documented. |

For H5 (data retention & deletion) and H6 (BAA/DPA), see [ROADMAP-after-AC4.md](./ROADMAP-after-AC4.md) §1 (policy/legal).
