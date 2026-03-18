# CDSS Database Deployment Guide (Manual AWS Console Path)

This guide provides step-by-step instructions to manually provision and seed the Aurora PostgreSQL database via the AWS Management Console.

## 1. Create Aurora Serverless v2 Cluster
1.  **Open Amazon RDS Console**: Navigate to [RDS Console](https://console.aws.amazon.com/rds/).
2.  **Create Database**:
    - Choose **Standard create**.
    - Engine type: **Amazon Aurora**.
    - Edition: **Amazon Aurora PostgreSQL-Compatible Edition**.
    - Engine version: **Aurora PostgreSQL 15.4** (or latest 15.x).
    - Templates: **Dev/Test**.
3.  **Settings**:
    - DB cluster identifier: `cdss-aurora-cluster`.
    - Credentials: Set a master username (e.g., `cdssadmin`) and a strong password.
4.  **Instance Configuration**:
    - DB instance class: **Serverless**.
    - Capacity range: Min **0.5 ACUs**, Max **2.0 ACUs**.
5.  **Connectivity**:
    - VPC: Select your project VPC.
    - Public access: **No** (Security best practice).
    - Security Group: Create a new one named `cdss-db-sg`.
6.  **Additional Configuration**:
    - Initial database name: `cdssdb`.
    - **Enable Data API**: (Important for Query Editor and Lambda access).
7.  **Create Database**: Wait for status to become `Available`.

## 2. Configure Security Group
1.  Go to the **EC2 Console** -> **Security Groups**.
2.  Find `cdss-db-sg`.
3.  **Edit Inbound Rules**:
    - Type: **PostgreSQL (5432)**.
    - Source: Select the Security Group used by your Lambda functions (or your VPC CIDR).
    - Save rules.

## 3. Seed Database via Query Editor
1.  In the RDS Console, click **Query Editor** in the left menu.
2.  **Connect**:
    - Cluster: `cdss-aurora-cluster`.
    - Database name: `cdssdb`.
    - Fetch credentials from Secrets Manager or enter manual credentials.
3.  **Execute Schema**:
    - Copy the contents of [refined_schema.sql](file:///d:/AI_Hackathon_CDSS/backend/database/refined_schema.sql).
    - Paste into the editor and click **Run**.
4.  **Execute Seed Data**:
    - Copy the contents of [seed_data.sql](file:///d:/AI_Hackathon_CDSS/backend/database/seed_data.sql).
    - Paste into the editor and click **Run**.

## 3. Lambda Configuration
Set the following environment variables in your Lambda functions:

| Variable | Description | Example |
|----------|-------------|---------|
| `DB_HOST` | Aurora Cluster Endpoint | `cdss-aurora-cluster.xyz.us-east-1.rds.amazonaws.com` |
| `DB_NAME` | Database Name | `cdssdb` |
| `DB_USER` | Master Username | `postgres` |
| `DB_PASS` | Master Password | (Stored in Secrets Manager) |

## 4. Local Development
To run the project locally against a Docker container:

```bash
# Start PostgreSQL
docker run --name cdss-db -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres:15

# Apply Schema
psql -h localhost -U postgres -f backend/database/refined_schema.sql
```

## 5. Connecting the Frontend to AWS
To see your live database data in the frontend dashboard, you must configure the environment variables:

1.  **Locate `.env.local`** in `frontend/apps/doctor-dashboard/`.
2.  **Update Variables**:
    ```env
    VITE_API_URL=https://<your-api-gateway-id>.execute-api.<region>.amazonaws.com/prod
    VITE_USE_MOCK=false
    ```
3.  **Restart Frontend**: Run `npm run dev` again. The application will now bypass mock data and fetch from your Lambda (which queries Aurora).

## 6. Accessing Data via AWS Console (Query Editor)
If you want to view or verify the database contents directly on AWS without using the frontend:

1.  **Open AWS Console**: Go to the **RDS** service.
2.  **Select Query Editor**: In the left sidebar, click **Query Editor**.
3.  **Connect**:
    - **Cluster**: Select your `cdss-aurora-cluster`.
    - **Database name**: Enter `cdssdb`.
    - **Connect**: Use **Database username and password** (or Secrets Manager).
4.  **Run Queries**:
    ```sql
    -- View all patients in the database
    SELECT * FROM patients;

    -- Check medical equipment inventory
    SELECT * FROM inventory;
    ```

## 7. Performance Optimization Tips
- **Connection Pooling**: Use **RDS Proxy** for Lambda functions to avoid connection exhaustion.
- **JSONB Indexing**: If querying specific keys in `content_json` or `pre_op_requirements`, add GIN indexes:
  ```sql
  CREATE INDEX idx_ai_summary_content ON ai_visit_summaries USING GIN (content_json);
  ```
