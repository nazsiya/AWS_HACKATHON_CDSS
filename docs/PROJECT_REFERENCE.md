# CDSS Project Reference (Single Source of Truth)

This document contains the centralized configuration, resource identifiers, and endpoints for the Clinical Decision Support System (CDSS) environment.

## 1. Infrastructure (Region: ap-south-1)

| Resource | Description | Value / ARN |
| :--- | :--- | :--- |
| **Project Name** | Base deployment prefix | `cdss-dev` |
| **AWS Region** | Primary region | `ap-south-1` |
| **VPC ID** | Primary network | `vpc-0123456789abcdef0` (Managed via Terraform) |
| **Cognito User Pool ID** | IAM for clinical staff | `ap-south-1_0eRSiDzbY` |
| **Cognito Staff Client ID** | Login for Doctors/Admins | `15hk1uremldsor79jkc7cr866v` |
| **Cognito Patient Client ID**| Login for Patients | `14qo2b4sdrjgbdnqietsj9jn3u` |

## 2. API Endpoints

| Environment | Base URL | WebSocket URL |
| :--- | :--- | :--- |
| **Local (API)** | `http://localhost:8080` | N/A |
| **Production (API)** | `https://b1q9qcuqia.execute-api.ap-south-1.amazonaws.com/dev` | `wss://jcw3vemil9.execute-api.ap-south-1.amazonaws.com/dev` |
| **Frontend (Dev)** | `http://localhost:5173` | N/A |

### Public Endpoint Mappings
- **Swagger UI**: `/api/docs`
- **OpenAPI Spec**: `/docs/swagger.yaml`
- **Health Check**: `/health`
- **Dashboard API**: `/dashboard`

## 3. Database (Aurora PostgreSQL)

| Setting | Context | Value |
| :--- | :--- | :--- |
| **Cluster Identifier** | RDS Master Cluster | `cdss-dev-aurora-cluster` |
| **Database Name** | Postgres DB name | `cdssdb` |
| **Master Username** | Admin User | `cdssadmin` |
| **Local Proxy Port** | SSH Tunnel | `5433` |
| **SSL Mode** | Encryption | `require` |

## 4. Operational Secrets (Secrets Manager)

| Secret Name | Usage |
| :--- | :--- |
| `cdss-dev/rds-config` | Database credentials and host details |
| `cdss-dev/bedrock-config` | Bedrock agent and model configurations |
| `cdss-dev/app-config` | Global feature flags and system settings |

## 5. Notification Topics (SNS ARNs)

| Topic Name | Usage | Placeholder ARN |
| :--- | :--- | :--- |
| `cdss-doctor-escalations` | Clinical alerts & staff notifications | `arn:aws:sns:ap-south-1:123456789012:cdss-doctor-escalations` |
| `cdss-patient-reminders` | Automated patient nudges (Phase 5) | `arn:aws:sns:ap-south-1:123456789012:cdss-patient-reminders` |
| `cdss-alarms` | System and performance alarms | `arn:aws:sns:ap-south-1:123456789012:cdss-alarms` |

---
*Last Verified: 2026-03-08*
