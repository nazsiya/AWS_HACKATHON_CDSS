# Mock DB vs Aurora Database

## Short answer

- **Mock DB** is used when you do **not** connect to Aurora: no `DATABASE_URL` (and no `RDS_CONFIG_SECRET_NAME`). The app uses in-memory sample data so the UI and AI work without a real database.
- **Aurora** is used when you **do** connect: you set `DATABASE_URL` (or `RDS_CONFIG_SECRET_NAME`) and run the tunnel. The app then uses the real PostgreSQL/Aurora database — no mock.

So: **mock DB and Aurora are mutually exclusive.** You don’t “use mock DB to use Aurora.” You either run without a DB (mock) or with a DB (Aurora).

---

## When each is used

| You want… | What to do | Result |
|------------|------------|--------|
| **Use Aurora (real tables and data)** | 1. Start tunnel (`.\scripts\start_ssm_tunnel.ps1` or `start_ssh_tunnel.ps1`).<br>2. Set `DATABASE_URL` (see [database-connection-guide.md](database-connection-guide.md); if Aurora uses IAM auth, use a script that injects the token, e.g. `.\scripts\run_dev_backend.ps1` or the same token generation).<br>3. Run API / migrations / seed / queries. | App and scripts talk to Aurora. You see all tables and data in Aurora. |
| **Run without any database** | Do **not** set `DATABASE_URL` (and leave `RDS_CONFIG_SECRET_NAME` unset). Run `python scripts/run_api_local.py`. | App uses mock data (sample patients, surgeries). Good for UI/demo when Aurora is not available. |

---

## Seeing all tables and data in Aurora

1. **Connect to Aurora**  
   - Terminal 1: start the tunnel (e.g. `.\scripts\start_ssm_tunnel.ps1`).  
   - Terminal 2: set `DATABASE_URL`. If your cluster uses **IAM database authentication**, use the same token injection as the backend (see [DEBUGGING_REPORT_2026_03_08.md](DEBUGGING_REPORT_2026_03_08.md)); for example run the backend once with `.\scripts\run_dev_backend.ps1` so the token is generated, or run the same Python one-liner that sets `DATABASE_URL` with the IAM token.

2. **List tables and row counts**  
   From repo root:
   ```powershell
   python scripts/list_aurora_tables.py
   ```
   This prints all tables in the `public` schema and their row counts (and optionally sample rows).

3. **Run arbitrary SQL**  
   ```powershell
   python scripts/run_db_query.py -q "SELECT * FROM patients LIMIT 10"
   python scripts/run_db_query.py -q "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
   ```

See [BASTION_AND_DB_QUERIES.md](BASTION_AND_DB_QUERIES.md) for tunnel setup and [database-connection-guide.md](database-connection-guide.md) for connection details.
