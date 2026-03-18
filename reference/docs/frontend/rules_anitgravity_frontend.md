---
description: Frontend standards — Emergency Medical Triage (Safety-Critical)
alwaysApply: true
---

# Emergency Medical Triage — Frontend Guardrails & Best Practices
# (Google Antigravity Strict Mode)

## 1. Project Context

- Domain: Healthcare / Safety-Critical.
- Priority: Safety > Correctness > Clarity > Reliability > Performance > Aesthetics.
- Stack: TypeScript-first (React / Next.js assumed).
- This is NOT a consumer app. It is a safety-sensitive system.

The frontend MUST be:
- Deterministic
- Explicit
- Minimal
- Secure
- Auditable
- Conservative by default

No experimental patterns. No over-engineering.

---

# 2. Core Non-Negotiable Rules

## 2.1 Minimal Hop Rule (CRITICAL)

Network flow must be:

UI → API Gateway → Lambda → Response

DO NOT introduce:
- Multiple client-side proxy layers
- Middleware chains
- Nested API wrappers
- Double transformations of the same payload
- UI → Service → Adapter → Wrapper → API patterns

Use ONE service abstraction per domain.

---

## 2.2 No Hardcoding Policy (STRICT)

Never hardcode:

- API URLs
- Region names
- Model IDs
- Feature flags
- Triage thresholds
- Timeout values
- Role names
- Severity mappings
- Static secrets
- Correlation IDs

Use:
- Environment variables
- Typed config objects
- Central config module

Bad:
const API_URL = "https://prod-api.com";

Good:
const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

---

## 2.3 No Secrets in Frontend

Never store or expose:
- API keys
- IAM credentials
- Bedrock keys
- DB credentials
- Secrets Manager values

Authentication must use:
- HTTP-only cookies
- Cognito / secure backend-issued tokens

---

## 2.4 No Silent Failures

Never:

try { ... } catch (e) {}

All errors must:
- Be logged
- Trigger safe fallback UI
- Show conservative message

---

# 3. TypeScript Standards (Mandatory)

- Strict mode ON.
- No `any`.
- No implicit return types.
- No loosely typed API responses.
- All external data must be typed.

Example:

interface TriageResponse {
  priority: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  confidence: number;
  reasoning: string;
  disclaimer: string;
}

Validate response shape before use.

Never render unknown JSON blindly.

---

# 4. Component Design Rules

## 4.1 Single Responsibility

Each component must:
- Have one purpose
- Be under ~150 lines (soft cap)
- Contain no business logic

Business logic must live in:
- /services
- /utils
- /validators

---

## 4.2 No State Duplication

- Do not store derived state.
- Do not mirror props into state.
- Avoid nested state objects.
- Avoid global state unless justified.

---

## 4.3 Minimal Functions Rule

Do not create:
- Helper functions used once
- Generic abstractions prematurely
- Wrapper hooks without need

Only create functions that are:
- Reused
- Improve clarity
- Reduce duplication

---

# 5. API Interaction Rules

## 5.1 Structured Requests Only

Before sending request:
- Validate payload shape
- Validate required fields
- Reject malformed input

Before using response:
- Check response.ok
- Parse JSON safely
- Validate schema
- Check confidence

---

## 5.2 Required Error Handling

Handle:
- 400
- 401
- 403
- 500
- Network timeout

If response fails:
- Show safe fallback
- Log structured error
- Do NOT suppress

---

## 5.3 No Blind AI Rendering

AI responses must:
- Be schema-validated
- Be sanitized
- Include disclaimer

If:
confidence < threshold

Frontend MUST:
- Escalate to HIGH priority
- Display emergency guidance
- Log event

Never downgrade severity on low confidence.

---

# 6. Safety-First Medical UI Rules

## 6.1 Mandatory Disclaimer

Every triage result must show:

"This system does not provide medical diagnosis. If symptoms are severe, seek emergency care immediately."

This must:
- Be visible
- Not collapsible
- Not hidden behind tooltip

---

## 6.2 Conservative Default

If:
- API fails
- Response malformed
- Confidence missing
- Timeout occurs

Default UI must:
- Treat as HIGH priority
- Show emergency instruction

---

## 6.3 No Auto-Actions

Never:
- Auto-submit forms
- Auto-trigger triage
- Auto-run AI in background
- Change priority automatically without explicit logic

---

# 7. UX & Severity Rules

Severity mapping must NEVER change:

LOW → Green
MEDIUM → Yellow
HIGH → Orange
CRITICAL → Red

Do not invert.
Do not customize per theme.

Use:
- Text labels
- Icons
- Color
- ARIA indicators

Never rely on color only.

---

# 8. Accessibility (MANDATORY)

- All controls keyboard accessible.
- Buttons must have aria-label.
- Minimum contrast AA.
- No color-only indicators.
- Screen-reader compatible.

---

# 9. Logging & Observability

Use structured logging.

Never use console.log in production.

Log:
- Action name
- Status
- Correlation ID (if provided)
- Non-PII metadata

Never log:
- Full symptoms text
- Personal data
- Tokens

---

# 10. Performance Rules

- No unnecessary re-renders.
- Memo only when measurable.
- Debounce input (300–500ms).
- No polling unless required.
- API timeout max 10s (configurable).

Do not introduce heavy libraries.

---

# 11. Folder Structure

/src
  /components
  /services
  /types
  /utils
  /validators
  /config

No circular dependencies.
No deep relative imports (../../../../).

Use absolute imports.

---

# 12. Input Validation Rules

Reject:
- Script injections
- Extremely large payloads
- Empty symptom lists
- Suspicious patterns

Sanitize:
- Text input
- Displayed reasoning

---

# 13. Disallowed Patterns

❌ Multiple API abstraction layers  
❌ Business logic inside JSX  
❌ Hardcoded environment values  
❌ Rendering raw AI output  
❌ Using `any`  
❌ Global mutable variables  
❌ Silent catch blocks  
❌ Feature creep  
❌ Over-generalized custom hooks  

---

# 14. Golden Path (Approved Flow)

1. User inputs symptoms
2. Validate input
3. Single API call
4. Validate response
5. Check confidence
6. Render structured result
7. Show disclaimer
8. Log interaction

Nothing more.

---

# 15. Definition of Done (Frontend)

Feature is complete ONLY if:

- Strict TypeScript
- No hardcoded values
- No console logs
- Error states handled
- Timeout handled
- Low-confidence escalation handled
- Disclaimer visible
- Response validated
- Single network hop
- Minimal functions
- No unnecessary abstractions

---

# 16. Google Antigravity Enforcement Rules

When generating code, Antigravity MUST:

- Generate minimal viable implementation
- Avoid introducing new dependencies
- Avoid multi-hop architecture
- Avoid abstraction layering
- Avoid over-complication
- Avoid unused functions
- Avoid magic numbers
- Avoid deeply nested async chains
- Avoid state duplication
- Favor explicit over clever
- Default to conservative safety behavior

If uncertain → choose simpler, safer implementation.