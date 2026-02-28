# CDSS REST API

Base URL: `https://<api-id>.execute-api.ap-south-1.amazonaws.com/<stage>/cdss`

## Endpoints

All endpoints accept `POST` with JSON body: `{ "action": "<action>", "payload": { ... } }`.

| Path | Agent | Actions |
|------|--------|--------|
| `/cdss/supervisor` | Supervisor | `route`, `aggregate` (action names from handler) |
| `/cdss/patient` | Patient | `getHistory`, `getRAGSummary`, `createPatient`, `getSummary`, `updateRecord` |
| `/cdss/surgery` | Surgery Planning | `getOTChecklists`, `getProtocols`, `analyseSurgery`, `generateChecklist` |
| `/cdss/resource` | Resource | `getOTAvailability`, `getEquipment`, `checkOT`, `allocateEquipment` |
| `/cdss/scheduling` | Scheduling | `getAppointments`, `bookOT`, `bookSlot`, `resolveConflict` |
| `/cdss/engagement` | Engagement | `getReminders`, `getEscalations`, `sendReminder`, `escalateToDoctor` |

## Example

```bash
curl -X POST https://<api-id>.execute-api.ap-south-1.amazonaws.com/dev/cdss/patient \
  -H "Content-Type: application/json" \
  -d '{"action":"getSummary","payload":{"patientId":"P001"}}'
```

## WebSocket

Real-time surgical planning uses API Gateway WebSocket API or ECS Fargate container. Routes: `$connect`, `$disconnect`, `default` (message handler).
