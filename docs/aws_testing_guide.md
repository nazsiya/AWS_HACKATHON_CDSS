# Testing CDSS AI Features against Real AWS Environment

This document provides the exact commands needed to connect your local development environment to the real AWS Bedrock AI models and the Aurora Database. 

Your AWS credentials (`aws sts get-caller-identity`) are currently working. To test the real generative AI, follow the steps below.

---

## 1. Start the Database Tunnel (Optional)
If you also want to connect the mock API to your real Aurora Database, you need to open an SSM tunnel. 
*Note: If you only want to test the AI responses and don't care about fetching real patients from the database, you can skip this step, but the mock API will use hardcoded patient data.*

**Open a new PowerShell terminal and run:**
```powershell
.\scripts\start_ssm_tunnel.ps1
```
*Leave this terminal open. It maps port 5433 on your machine to the Aurora database in AWS.*

---

## 2. Start the Backend API (Connected to AWS)
We will start the local backend router and inject both the `RDS_CONFIG_SECRET_NAME` (for the database) and the `BEDROCK_CONFIG_SECRET_NAME` (which tells the code to use Claude on AWS).

**Open another PowerShell terminal and run:**
```powershell
$env:RDS_CONFIG_SECRET_NAME="cdss-dev/rds-config"
$env:BEDROCK_CONFIG_SECRET_NAME="cdss-dev/bedrock-config"
$env:AWS_REGION="ap-south-1"
$env:TUNNEL_LOCAL_PORT="5433"
$env:PORT="8081"
$env:PYTHONPATH="src"
.\.venv\Scripts\python.exe scripts\run_api_local.py
```
*Leave this terminal open. You should see "CDSS local API at http://localhost:8081 (mock DB: False)"*

---

## 3. Test the Endpoints directly (CLI)
You can verify the connection is working by querying the backend API directly.

**Open a third PowerShell terminal and test the Chatbot:**
```powershell
python -c "
import urllib.request, json
req = urllib.request.Request('http://localhost:8081/api/v1/agent', data=b'{\"message\": \"Hello, can you help me understand my symptoms?\"}', method='POST')
req.add_header('X-CDSS-Role', 'doctor')
req.add_header('Content-Type', 'application/json')
res = urllib.request.urlopen(req, timeout=30)
data = json.loads(res.read())
print(json.dumps(data, indent=2))
"
```
Expect to see a generated response from AWS Bedrock (`data.reply`) rather than the "Agent endpoint ready" fallback.

---

## 4. Test via Frontend Browser
To test utilizing the actual frontend user interface:

1. Open `frontend/apps/doctor-dashboard/.env.local`
2. Ensure it contains the following:
   ```env
   VITE_API_URL=http://localhost:8081
   VITE_USE_MOCK=false
   ```
3. Restart your frontend server (if it isn't already running):
   ```powershell
   cd frontend
   npm run dev:dashboard
   ```
4. Navigate to the local dashboard (usually `http://localhost:5173/`) and test the chatbot and patient summary features. They will now be generating real data via your configured AWS CLI profile!
