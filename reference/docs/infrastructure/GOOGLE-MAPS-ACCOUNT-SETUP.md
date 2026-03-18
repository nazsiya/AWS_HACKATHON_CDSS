# Google Maps Platform – account and API key setup

**Purpose:** Create a Google Cloud project, enable Maps APIs (Directions, Geocoding), and get an API key so the backend can return **directions_url** (the Google Maps link users click to open turn-by-turn directions). The key is stored in Secrets Manager; the **gateway_maps** Lambda reads it and builds the URL.

---

## Where the directions URL comes from

- **`directions_url`** is a link like `https://www.google.com/maps/dir/?api=1&origin=12.97,77.59&destination=12.8967,77.5982&travelmode=driving`. It is built by the **gateway_maps** Lambda using your Google Maps API key (Routes API for distance/duration; the URL is a standard Google Maps deep link).
- **POST /route** – The Route Lambda calls the Gateway tool **maps-target___get_directions** → gateway_maps Lambda → returns `distance_km`, `duration_minutes`, **directions_url**. So the URL appears in the /route response when the Gateway and maps Lambda are configured and the API key is set in Terraform.
- **POST /hospitals** (with `patient_location_lat` / `patient_location_lon`) – The Hospital Matcher agent calls **routing-target___get_route** → gateway_routing Lambda invokes the **Routing AgentCore runtime** → the Routing agent calls **maps-target___get_directions** → gateway_maps Lambda returns the same fields. So each hospital in the response can have **directions_url** (and distance/duration) only if the **Routing runtime** has Gateway env vars set (so it can call maps-target). Running `setup_agentcore_gateway.py` (without `--skip-runtime-env`) sets Gateway env on both Hospital Matcher and **Routing** runtimes so this chain works.

---

## Step 1: Create or select a Google Cloud project

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Sign in with your Google account.
3. **Create a project** (or select an existing one):
   - Click the project dropdown at the top → **New Project**.
   - Name it (e.g. `emergency-triage-maps`), choose organization if needed, click **Create**.

---

## Step 2: Enable billing

- Google Maps Platform requires a billing account (pay-as-you-go; free tier is generous).
- In the Console: **Billing** → link your project to a billing account (or create one).
- **Set a budget alert** (e.g. $50/month) so you get notified before unexpected cost: **Billing** → **Budgets & alerts** → **Create budget**.

---

## Step 3: Enable the required APIs

1. Go to [APIs & Services → Library](https://console.cloud.google.com/apis/library).
2. Enable these APIs (search by name, then **Enable**):
   - **Routes API** (required for directions; replaces the legacy Directions API for new projects)
   - **Geocoding API** (for address → lat/lon when origin or destination is an address)

**Note:** New Google Cloud projects get “legacy API not enabled” for the classic Directions API. Use **Routes API** instead; this backend calls `computeRoutes` (POST `https://routes.googleapis.com/directions/v2:computeRoutes`).

---

## Step 4: Create an API key

1. Go to [APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials).
2. Click **+ Create credentials** → **API key**.
3. Copy the generated key (e.g. `AIza...`). You can optionally **Restrict key** (recommended for production):
   - **Application restrictions:** None or “IP addresses” (if your Lambda has fixed egress IPs) or “HTTP referrers” for web.
   - **API restrictions:** Restrict to “Directions API” and “Geocoding API” only.
4. Click **Save**.

---

## Step 5: Add the key to the backend (Terraform)

1. Open `infrastructure/terraform.tfvars` (or create it from `terraform.tfvars.example`).
2. Set the variable (use a secret manager or env for CI; do not commit the key to git if the repo is public):

   ```hcl
   google_maps_api_key = "YOUR_API_KEY_HERE"
   ```

3. Apply Terraform so the key is stored in Secrets Manager and the Maps Lambda can use it:

   ```bash
   cd infrastructure
   terraform plan
   terraform apply
   ```

4. Re-run the Gateway setup so the **maps target** is registered (if not already):

   ```bash
   python scripts/setup_agentcore_gateway.py
   ```

   This reads `gateway_maps_lambda_arn` from the api_config secret and adds the maps target (get_directions, geocode_address) to the AgentCore Gateway.

---

## Step 6: Verify

- Call **POST /route** with a valid RMP token and body e.g.:
  ```json
  { "origin": { "address": "MG Road, Bangalore" }, "destination": { "lat": 12.8967, "lon": 77.5982 } }
  ```
- You should get a response with `distance_km`, `duration_minutes`, and `directions_url` (no `stub: true`).

---

## Cost reminder

- **India:** 70,000 free Directions + Geocoding events/month; then ~$1.50 per 1,000 events.
- **Global:** 10,000 free/month; then ~$5 per 1,000.
- Typical session (one geocode + a few route calls) is a few cents above free tier. Set a budget alert in Step 2.

---

## References

- [Google Maps Platform](https://developers.google.com/maps)
- [Pricing (global)](https://developers.google.com/maps/billing-and-pricing/pricing)
- [Pricing (India)](https://developers.google.com/maps/billing-and-pricing/pricing-india)
