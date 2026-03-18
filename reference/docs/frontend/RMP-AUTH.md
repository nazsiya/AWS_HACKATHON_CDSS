# RMP authentication – frontend integration

**Purpose:** How to sign in as an RMP (Registered Medical Practitioner) and call the protected APIs (POST /triage, POST /hospitals, POST /route). The backend uses **Amazon Cognito User Pools** and **API Gateway Cognito authorizer**.

**For a single guide covering all endpoints (health, triage, hospitals, route) and recommended flow for mobile & web:** see [API-Integration-Guide.md](./API-Integration-Guide.md).

---

## 1. Configuration (from backend / Terraform)

After `terraform apply`, the backend team will provide (or you can read from Terraform outputs):

| Variable | Description | Example |
|----------|-------------|--------|
| **User Pool ID** | Cognito User Pool ID | `us-east-1_xxxxxxxxx` |
| **Client ID** | Cognito App Client ID (public, no secret) | `xxxxxxxxxxxxxxxxxxxxxxxxxx` |
| **Region** | AWS region | `us-east-1` |
| **API base URL** | API Gateway invoke URL | `https://xxxx.execute-api.us-east-1.amazonaws.com/dev` |

**Terraform outputs:**
```bash
cd infrastructure && terraform output cognito_user_pool_id cognito_app_client_id
```

---

## 2. Which endpoints require auth

| Endpoint | Auth | Notes |
|----------|------|--------|
| **GET /health** | No | Public; no token. |
| **POST /triage** | **Yes** | Send `Authorization: Bearer <IdToken>`. |
| **POST /hospitals** | **Yes** | Same. |
| **POST /route** | **Yes** | Same. |

If you call /triage, /hospitals, or /route **without** a valid token, API Gateway returns **401 Unauthorized**.

---

## 3. Header format

Every request to a protected endpoint must include:

```http
Authorization: Bearer <IdToken>
```

- **IdToken** = JWT returned by Cognito after sign-in (not the Access Token). Use the **Id Token** for API Gateway.
- No `Basic` or other scheme; only `Bearer` + IdToken.

---

## 4. Sign-in and getting the Id Token

### Option A: AWS Amplify (recommended for React/React Native)

1. Install:
   ```bash
   npm install aws-amplify @aws-amplify/ui-react
   ```

2. Configure once (e.g. in your app bootstrap):
   ```javascript
   import { Amplify } from 'aws-amplify';

   Amplify.configure({
     Auth: {
       Cognito: {
         userPoolId: '<User Pool ID>',
         userPoolClientId: '<Client ID>',
         loginWith: { password: true },
       },
     },
   });
   ```

3. Sign in and get the Id Token:
   ```javascript
   import { signIn, getCurrentUser } from 'aws-amplify/auth';

   // Sign in (email + password)
   const { isSignedIn } = await signIn({
     username: 'rmp@example.com',
     password: 'YourSecurePassword',
   });

   // After sign-in, get Id Token for API calls
   const user = await getCurrentUser();
   const { idToken } = await fetchAuthSession(); // or get the token from the session
   const idTokenJwt = idToken.toString();       // use this in Authorization header
   ```

   For Amplify v6, use `fetchAuthSession()` from `aws-amplify/auth` and read `tokens.idToken.toString()`.

4. Call the API:
   ```javascript
   const response = await fetch(`${API_BASE_URL}/triage`, {
     method: 'POST',
     headers: {
       'Content-Type': 'application/json',
       'Authorization': `Bearer ${idTokenJwt}`,
     },
     body: JSON.stringify({
       symptoms: ['chest pain'],
       vitals: { heart_rate: 100 },
       age_years: 55,
       sex: 'M',
     }),
   });
   ```

### Option B: amazon-cognito-identity-js (vanilla JS)

1. Install:
   ```bash
   npm install amazon-cognito-identity-js
   ```

2. Sign in and get Id Token:
   ```javascript
   import {
     CognitoUserPool,
     CognitoUser,
     AuthenticationDetails,
   } from 'amazon-cognito-identity-js';

   const userPool = new CognitoUserPool({
     UserPoolId: '<User Pool ID>',
     ClientId: '<Client ID>',
   });

   const cognitoUser = new CognitoUser({
     Username: 'rmp@example.com',
     Pool: userPool,
   });

   const authDetails = new AuthenticationDetails({
     Username: 'rmp@example.com',
     Password: 'YourSecurePassword',
   });

   cognitoUser.authenticateUser(authDetails, {
     onSuccess: (result) => {
       const idToken = result.getIdToken().getJwtToken();
       // Use idToken in Authorization: Bearer <idToken>
       callTriageApi(idToken);
     },
     onFailure: (err) => console.error(err),
   });
   ```

3. **Refresh:** Id tokens expire (e.g. 60 minutes). Use Amplify’s `fetchAuthSession()` (it refreshes automatically) or Cognito’s `refreshSession()` and then get the new Id Token before each API call or when you get 401.

---

## 5. Example: curl (for testing)

**Get Id token via AWS CLI** (then use it in the curl `Authorization` header):

```bash
# From infrastructure dir: terraform output cognito_user_pool_id cognito_app_client_id
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id "YOUR_CLIENT_ID" \
  --auth-parameters USERNAME="rmp@example.com",PASSWORD="YourPassword" \
  --query 'AuthenticationResult.IdToken' \
  --output text
```

Replace placeholders and use the Id Token from a sign-in response (decode the JWT at jwt.io if needed to check expiry).

```bash
# 1. Sign in (you need a small script or Postman to get id_token from Cognito)
# 2. Then:
curl -X POST "https://YOUR_API_URL/dev/triage" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ID_TOKEN" \
  -d '{"symptoms":["chest pain"],"vitals":{"heart_rate":100},"age_years":55,"sex":"M"}'
```

For a full pipeline (triage → hospitals → route) with copy-paste curl commands, see [TESTING-Pipeline-curl.md](../backend/TESTING-Pipeline-curl.md).

Without a valid token:
```bash
curl -X POST "https://YOUR_API_URL/dev/triage" \
  -H "Content-Type: application/json" \
  -d '{"symptoms":["chest pain"]}'
# → 401 Unauthorized
```

---

## 6. Creating a test RMP user

Users are created in the Cognito User Pool. Options:

1. **AWS Console:** Cognito → User Pools → your pool → Users → Create user (email + temporary password). User signs in and changes password on first login if you enforce it.
2. **AWS CLI:**
   ```bash
   aws cognito-idp admin-create-user \
     --user-pool-id us-east-1_xxxxxxxxx \
     --username rmp@example.com \
     --user-attributes Name=email,Value=rmp@example.com Name=email_verified,Value=true \
     --temporary-password "TempPass123!"
   ```
3. **Frontend:** Use Amplify’s `signUp` (if you enable self-service sign-up in the User Pool). Currently the pool is set up for email + password; add sign-up in Cognito if you want self-registration.

---

## 7. Audit (what the backend stores)

- For **POST /triage**, when you omit `submitted_by` in the body, the backend uses the Cognito **sub** (or email) from the token as the submitting RMP for the record (stored in `triage_assessments.submitted_by`).
- For **POST /hospitals** and **POST /route**, the backend logs the RMP identifier (sub) in CloudWatch for audit. No separate “submitted_by” in the request body required.

---

## 8. Summary checklist for frontend

- [ ] Get **User Pool ID** and **Client ID** from backend/Terraform.
- [ ] Configure Amplify (or Cognito SDK) with User Pool ID and Client ID.
- [ ] Implement **sign-in** (email + password) and obtain **Id Token** (not Access Token).
- [ ] Send **`Authorization: Bearer <IdToken>`** on every request to **POST /triage**, **POST /hospitals**, **POST /route**.
- [ ] Handle **401**: refresh the token or re-prompt sign-in.
- [ ] Optional: use **sub** or **email** from the token to show “Logged in as …” in the UI (decode JWT or use Amplify’s `getCurrentUser()`).

---

## References

- [API-Integration-Guide.md](./API-Integration-Guide.md) – Single guide for mobile & web: base URL, auth, triage → hospitals → route, real directions (POST /route).
- [AWS Amplify Auth](https://docs.amplify.aws/react/build-a-backend/auth/)
- [Cognito User Pools](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools.html)
- [API Gateway Cognito authorizer](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-integrate-with-cognito.html)
