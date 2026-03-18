# CDSS Frontend

React (Vite) apps for the Clinical Decision Support System: **Doctor**, **Patient**, and **Nurse** dashboards.

## Quick start

```bash
npm install
npm run dev:dashboard   # Doctor dashboard → http://localhost:5173
npm run dev:patient     # Patient portal   → http://localhost:5174
npm run dev:nurse       # Nurse dashboard  → http://localhost:5175
```

## Apps

| App | Path | Port | Demo login |
|-----|------|------|------------|
| Doctor dashboard | `apps/doctor-dashboard` | 5173 | Contact team for demo access |
| Patient portal | `apps/patient-dashboard` | 5174 | Contact team for demo access |
| Nurse dashboard | `apps/nurse-dashboard` | 5175 | Contact team for demo access |

## Build & lint

```bash
npm run build:all   # Build all apps
npm run lint        # Lint workspaces
```

## Configuration

- Copy `apps/doctor-dashboard/.env.example` to `apps/doctor-dashboard/.env`.
- Set `VITE_API_URL` to your API Gateway base URL when using the live API.
- Use `VITE_USE_MOCK=true` for mock data without a backend.

## Documentation

- **[Frontend implementation plan](../docs/frontend-implementation-plan.md)** — Current state, full process (dev/build/test/deploy), and prioritized improvements aligned with the project.
