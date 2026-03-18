# Emergency Medical Triage — Frontend Workflow Diagram

## System Overview

The frontend serves **three user roles** (Healthcare Worker / RMP, Hospital Staff, Admin) across **three platforms** (Mobile App, Web Dashboard, Voice Interface). Below are the key workflow diagrams to guide frontend development.

---

## 1. High-Level Frontend Architecture

```mermaid
graph TB
    subgraph "Frontend Applications"
        MA["📱 Mobile App<br/>(Android / iOS)"]
        WD["🖥️ Web Dashboard"]
        VI["🎙️ Voice Interface"]
    end

    subgraph "Frontend Core Modules"
        AUTH["🔐 Auth Module"]
        TRIAGE["🩺 Triage Module"]
        HOSPITAL["🏥 Hospital Module"]
        ROUTING["🗺️ Routing Module"]
        RMP_TRAIN["📚 RMP Training Module"]
        PEER["👥 Peer Network Module"]
        LANG["🌐 Language Module"]
        OFFLINE["📴 Offline Module"]
    end

    MA --> AUTH
    WD --> AUTH
    VI --> AUTH

    AUTH --> TRIAGE
    AUTH --> HOSPITAL
    AUTH --> ROUTING
    AUTH --> RMP_TRAIN
    AUTH --> PEER

    TRIAGE --> LANG
    TRIAGE --> OFFLINE
    HOSPITAL --> OFFLINE
    ROUTING --> OFFLINE
```

---

## 2. Primary User Flow — Emergency Triage & Routing

This is the **core workflow** an RMP/Healthcare Worker follows during an emergency.

```mermaid
flowchart TD
    A["🚨 Emergency Occurs"] --> B["Open App / Voice Trigger"]
    B --> C{"Authenticated?"}
    C -- No --> D["Login / Biometric Auth"]
    D --> C
    C -- Yes --> E["Select Language<br/>(7 languages supported)"]

    E --> F["📝 Enter Patient Info<br/>Age, Gender, Location"]
    F --> G["🩺 Input Symptoms<br/>(Text / Voice / Vernacular)"]
    G --> H["📊 Input Vital Signs<br/>(Heart Rate, BP, SpO2, Temp)"]

    H --> I{"📴 Online?"}
    I -- Yes --> J["🤖 AI Triage Assessment<br/>(Multi-model consensus)"]
    I -- No --> K["📴 Offline Triage<br/>(Cached 20 common scenarios)"]

    J --> L{"Confidence ≥ 85%?"}
    L -- Yes --> M["Show Severity Level<br/>🔴 Critical / 🟠 High / 🟡 Medium / 🟢 Low"]
    L -- No --> N["⚠️ Auto-escalate to HIGH<br/>Flag for doctor review"]
    K --> O["Show Offline Result<br/>+ 'OFFLINE MODE' banner"]

    M --> P["📋 View Triage Report<br/>+ Recommended Actions"]
    N --> P
    O --> P

    P --> Q["🏥 Hospital Matching<br/>(Top 3 recommendations)"]
    Q --> R["🗺️ Select Hospital<br/>& Start Navigation"]
    R --> S["📍 Turn-by-turn Directions<br/>+ ETA"]
    S --> T["🏁 Arrival & Handoff<br/>Generate Medical Report"]

    style A fill:#ff4444,color:#fff
    style N fill:#ff8800,color:#fff
    style M fill:#44aa44,color:#fff
    style K fill:#888,color:#fff
```

---

## 3. Triage Assessment — Detailed Screen Flow

```mermaid
flowchart LR
    subgraph "Screen 1: Patient Info"
        S1A["Age Input"]
        S1B["Gender Select"]
        S1C["GPS Location<br/>(auto-detect)"]
        S1D["Medical History<br/>(optional)"]
        S1E["Allergies<br/>(optional)"]
    end

    subgraph "Screen 2: Symptoms"
        S2A["Primary Symptoms<br/>(multi-select / voice)"]
        S2B["Secondary Symptoms"]
        S2C["Duration"]
        S2D["Patient-reported<br/>Severity"]
        S2E["Vernacular<br/>Description"]
    end

    subgraph "Screen 3: Vitals"
        S3A["Heart Rate"]
        S3B["Blood Pressure"]
        S3C["Temperature"]
        S3D["SpO2"]
        S3E["Respiratory Rate"]
        S3F["Consciousness<br/>Level (AVPU)"]
    end

    subgraph "Screen 4: Results"
        S4A["Severity Badge"]
        S4B["Confidence Score"]
        S4C["Recommended<br/>Actions"]
        S4D["Safety<br/>Disclaimers"]
        S4E["Override Option"]
        S4F["Proceed to<br/>Hospital Match"]
    end

    S1A --> S2A
    S2A --> S3A
    S3A --> S4A
```

---

## 4. Hospital Matching & Routing Flow

```mermaid
flowchart TD
    A["Triage Complete"] --> B["🔍 Fetch Hospital Data<br/>(via Hospital Data MCP)"]
    B --> C["Score Hospitals by:<br/>• Condition Match<br/>• Bed Availability<br/>• Specialist On-call<br/>• Distance / ETA"]

    C --> D["📋 Show Top 3 Hospitals"]

    D --> E["Hospital Card:<br/>🏥 Name & Distance<br/>🛏️ Beds Available<br/>👨‍⚕️ Specialist Status<br/>⏱️ ETA<br/>📊 Match Score"]

    E --> F{"Select Hospital"}
    F --> G["🗺️ Navigation View<br/>Turn-by-turn directions"]
    G --> H{"Route Issue?"}
    H -- "Traffic / Road Block" --> I["⚡ Re-route<br/>or Suggest Alternative"]
    I --> G
    H -- No --> J["📍 Arriving"]
    J --> K["📄 Generate Handoff Report<br/>for Hospital Staff"]

    D --> L["Hospital Unavailable?<br/>→ Auto-suggest next"]
```

---

## 5. RMP Augmentation & Training Flow

```mermaid
flowchart TD
    A["RMP Logs In"] --> B["📊 Dashboard:<br/>Competency Profile"]

    B --> C{"Mode?"}

    C -- "Emergency" --> D["🩺 Start Triage<br/>(see Flow #2)"]
    D --> E["💡 Real-time Education<br/>'WHY this indicates X'"]
    E --> F["📋 Step-by-step<br/>Procedure Guidance"]
    F --> G{"Exceeds Capability?"}
    G -- Yes --> H["📞 Escalate to<br/>Telemedicine"]
    G -- No --> I["✅ Complete Case"]
    I --> J["📈 Update Competency<br/>Profile & Score"]

    C -- "Learning" --> K["📚 Micro-Learning<br/>Modules"]
    K --> L["🎯 Skill Assessment"]
    L --> M["🏆 Achievement Badges<br/>& Peer Rankings"]

    C -- "Peer Network" --> N["👥 Peer Consultation"]
    N --> O["📸 Share Case<br/>(anonymized)"]
    O --> P["💬 Virtual Medical<br/>Rounds"]
```

---

## 6. Offline Mode State Machine

```mermaid
stateDiagram-v2
    [*] --> Online

    Online --> CheckingConnectivity: Periodic check
    CheckingConnectivity --> Online: Connected
    CheckingConnectivity --> OfflineTransition: No connection

    OfflineTransition --> OfflineMode: Activate within 5s

    state OfflineMode {
        [*] --> ShowBanner
        ShowBanner --> CachedTriage: Use cached AI models
        CachedTriage --> CachedHospitals: 50km radius data
        CachedHospitals --> CachedRouting: Cached road maps
        CachedRouting --> QueueAssessments: Store locally
    }

    OfflineMode --> SyncPending: Connectivity restored
    SyncPending --> Syncing: Auto-sync queued data
    Syncing --> RefreshCache: Update all cached data
    RefreshCache --> Online

    OfflineMode --> ForceReconnect: 48hr limit reached
```

---

## 7. Role-Based Screen Map

| Screen / Module | 🩺 RMP / Healthcare Worker | 🏥 Hospital Staff | 🔧 Admin |
|---|---|---|---|
| **Login / Auth** | ✅ | ✅ | ✅ |
| **Language Selection** | ✅ | ✅ | ✅ |
| **Triage Assessment** | ✅ | ❌ | ❌ |
| **Hospital Matching** | ✅ | ❌ | ❌ |
| **Route Navigation** | ✅ | ❌ | ❌ |
| **Real-time Guidance** | ✅ | ❌ | ❌ |
| **Training / Learning** | ✅ | ❌ | ❌ |
| **Peer Network** | ✅ | ❌ | ❌ |
| **Competency Dashboard** | ✅ | ❌ | ✅ (view all) |
| **Capacity Management** | ❌ | ✅ | ✅ |
| **Incoming Patient Alerts** | ❌ | ✅ | ❌ |
| **Handoff Reports** | ✅ (send) | ✅ (receive) | ✅ (audit) |
| **Analytics Dashboard** | ❌ | ❌ | ✅ |
| **User Management** | ❌ | ❌ | ✅ |
| **System Config / MCP** | ❌ | ❌ | ✅ |
| **Audit Logs** | ❌ | ❌ | ✅ |
| **Outbreak Alerts** | ✅ (view) | ✅ (view) | ✅ (manage) |

---

## 8. Recommended Frontend Build Order

```mermaid
flowchart TD
    P1["Phase 1: Foundation"]
    P2["Phase 2: Core Triage"]
    P3["Phase 3: Hospital & Routing"]
    P4["Phase 4: RMP Features"]
    P5["Phase 5: Advanced Features"]

    P1 --> P2 --> P3 --> P4 --> P5

    P1 -.- P1A["• Project setup (Vite / Next.js)<br/>• Design system & tokens<br/>• Auth flow (login, roles, RBAC)<br/>• Language selector (7 langs)<br/>• Offline-first service worker<br/>• API client & error handling"]

    P2 -.- P2A["• Patient Info form<br/>• Symptom input (text + voice)<br/>• Vital signs form<br/>• AI Triage result screen<br/>• Triage report view<br/>• Override / escalation UI"]

    P3 -.- P3A["• Hospital list with match scores<br/>• Hospital detail cards<br/>• Map integration (routing)<br/>• Turn-by-turn navigation<br/>• Dynamic re-routing<br/>• Handoff report generator"]

    P4 -.- P4A["• Competency dashboard<br/>• Real-time guidance overlay<br/>• Procedural step-by-step UI<br/>• Micro-learning modules<br/>• Achievement / gamification<br/>• Telemedicine escalation"]

    P5 -.- P5A["• Peer consultation network<br/>• Case sharing (anonymized)<br/>• Virtual medical rounds<br/>• Outbreak alerts dashboard<br/>• Admin analytics panel<br/>• Hospital staff portal"]

    style P1 fill:#4a90d9,color:#fff
    style P2 fill:#e8a838,color:#fff
    style P3 fill:#50b83c,color:#fff
    style P4 fill:#9c6ade,color:#fff
    style P5 fill:#de3618,color:#fff
```

---

## 9. API Endpoints the Frontend Will Consume

| Endpoint | Method | Purpose |
|---|---|---|
| `/auth/login` | POST | Authenticate user, return JWT |
| `/auth/validate` | GET | Validate token & role |
| `/triage/assess` | POST | Submit symptoms → get severity; send optional `session_id` (UUID, ≥33 chars) for memory continuity; response includes `session_id` to reuse on /hospitals and /route |
| `/triage/report/{id}` | GET | Fetch triage report |
| `/triage/override/{id}` | PUT | Override AI recommendation |
| `/hospitals/match` | POST | Get top 3 hospital matches; send same `session_id` as triage for AgentCore memory |
| `/hospitals/{id}/status` | GET | Real-time hospital status |
| `/routing/calculate` | POST | Get route to hospital |
| `/routing/navigate/{id}` | GET | Turn-by-turn steps |
| `/rmp/profile/{id}` | GET | RMP competency profile |
| `/rmp/guidance/{emergencyId}` | GET | Real-time procedural guidance |
| `/rmp/learning/modules` | GET | Available micro-learning |
| `/rmp/telemedicine/connect` | POST | Escalate to doctor |
| `/collective/insights/{region}` | GET | Regional health insights |
| `/collective/share` | POST | Share anonymized case |
| `/language/translate` | POST | Translate symptom text |
| `/language/audio` | POST | Text-to-speech output |
| `/sync/upload` | POST | Sync offline assessments |
| `/sync/download` | GET | Download cache data |

---

> [!TIP]
> **Start with Phase 1** (project scaffolding, auth, language, offline shell) and **Phase 2** (the triage flow) — these cover the core value proposition and can be demoed independently.
