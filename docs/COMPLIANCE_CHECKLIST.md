# CDSS Regulatory & Compliance Checklist (CDSCO)

This document outlines the safeguards and procedures implemented to ensure the Clinical Decision Support System (CDSS) complies with regulatory standards (Req 6.5).

## 1. Doctor-in-the-Loop Enforcement
All AI-generated insights and clinical suggestions are explicitly marked as "Draft" and require physician verification.
- [ ] **AI Summaries**: Physicians must review and can edit the AI-generated consultation summary before final submission.
- [ ] **Drug Interactions**: Interaction alerts are displayed to the physician for final clinical judgment.
- [ ] **AI Chat (Supervisor)**: A mandatory safety disclaimer is appended to every AI chat response ("AI is a support tool, not a diagnostic replacement").

## 2. Audit Trail & Traceability
- [ ] **Data Lineage**: Every clinical record (Visits, Surgeries) tracks the `doctor_id` responsible for the entry.
- [ ] **Alert Logging**: All safety-critical alerts (Drug interactions, Vitals) are logged in the `alert_log` table with timestamps and contextual data.
- [ ] **RBAC Logs**: Access to patient records is logged and monitored for unauthorized access patterns.

## 3. Data Privacy (DISHA/SOP)
- [ ] **PII/PHI Protection**: No patient-identifiable information is emitted in system logs (CloudWatch).
- [ ] **ABDM Integration**: Patient identity Management is handled predominantly via ABHA ID redirection to ABDM.

## 4. Continuity & Safety
- [ ] **Emergency Thresholds**: Critical vitals trigger automated escalations to ensure 24/7 safety coverage.
- [ ] **Maintenance Protocol**: Procedures for downtime notifications are documented in [MAINTENANCE_LOG.md](file:///d:/AI_Hackathon_CDSS/docs/MAINTENANCE_LOG.md).

---
*Verified by: Clinical Systems Lead*
*Date: 2026-03-08*
