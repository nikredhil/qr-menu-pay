# Deploying HSR Club Dine

Two pieces go live separately:

- **Backend** (FastAPI) → **Render** (free tier works)
- **Frontend** (Vite SPA) → **Vercel** (free tier works)

You'll do this once from the dashboards; the configs in this repo
(`render.yaml`, `frontend/vercel.json`) make it mostly click-through.

> Prerequisite: push this repo to GitHub. From `qr-menu-pay/`:
> ```bash
> gh repo create hsr-club-dine --private --source=. --push   # or create on github.com and `git push`
> ```

---

## 1. Backend on Render

1. **Render Dashboard → New → Blueprint**, pick your `hsr-club-dine` repo. Render
   reads [`render.yaml`](render.yaml) and proposes the `hsr-club-dine-api` web service.
2. It will prompt for the secret env vars (everything marked `sync: false`). Set:
   | Key | Value |
   |---|---|
   | `ADMIN_PASSWORD` | a strong staff password |
   | `RAZORPAY_KEY_ID` | `rzp_test_…` (test) or `rzp_live_…` (after KYC) |
   | `RAZORPAY_KEY_SECRET` | the matching secret |
   | `RAZORPAY_WEBHOOK_SECRET` | the secret you set in step 4 |
   | *(SMS — optional)* | see §3 below |
   `JWT_SECRET` is auto-generated; `CORS_ORIGINS` is set in the blueprint — update
   it to your real frontend URL once you have it (step 2).
3. **Create** → wait for the build. Your API is at `https://hsr-club-dine-api.onrender.com`
   (your name may differ). Check `https://…/health` returns `{"status":"ok"}` and
   `https://…/docs` loads.
4. **Razorpay webhook** (once the API URL exists): Razorpay Dashboard → **Settings
   → Webhooks → Add New Webhook**:
   - URL: `https://hsr-club-dine-api.onrender.com/payments/razorpay/webhook`
   - Secret: choose one, and set it as `RAZORPAY_WEBHOOK_SECRET` on Render
   - Active events: `payment.captured`, `payment.failed`, `order.paid`

> **Data persistence:** the free plan's disk is ephemeral, so orders reset on
> redeploy/sleep. The menu + tables auto-reseed on boot. For durable orders,
> uncomment the `disk:` block in `render.yaml` (paid plan) and set `DATA_DIR` to
> its `mountPath`.

---

## 2. Frontend on Vercel

1. **Vercel → Add New → Project**, import the same repo.
2. **Root Directory → `frontend`**. Vercel auto-detects Vite and reads
   [`frontend/vercel.json`](frontend/vercel.json) (which includes the SPA rewrite
   so `/t/<table>` deep links work on scan/refresh).
3. **Environment Variables**:
   | Key | Value |
   |---|---|
   | `VITE_API_BASE` | `https://hsr-club-dine-api.onrender.com` (your Render URL) |
4. **Deploy.** You'll get `https://hsr-club-dine.vercel.app` (or your custom domain,
   e.g. `dine.hsrclub.in`).
5. Go back to Render and set `CORS_ORIGINS` to that exact frontend origin, then
   redeploy the API.

---

## 3. Real OTP SMS (optional)

By default OTP runs in **demo mode** (the code shows on screen). To send real SMS,
on Render set `OTP_DEMO_MODE=false` and configure one provider:

**MSG91 (recommended for India):**
```
OTP_PROVIDER=msg91
MSG91_AUTH_KEY=…
MSG91_TEMPLATE_ID=…        # a DLT-approved Flow template with one variable
MSG91_SENDER_ID=…          # your 6-char DLT sender id
MSG91_OTP_VAR=otp          # the template's variable name for the code
```

**Twilio (global):**
```
OTP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=…
TWILIO_AUTH_TOKEN=…
TWILIO_FROM_NUMBER=+1…     # an SMS-capable Twilio number (E.164)
```

If credentials are missing, the app safely falls back to demo mode and logs a
warning — it won't silently fail to send. India requires DLT registration for SMS
templates/sender ids with both providers.

---

## 4. Print the table QR codes

Sign in at `https://<your-frontend>/admin` (the `ADMIN_PASSWORD`) → **Tables & QR**.
Each QR now encodes `https://<your-frontend>/t/<table>`, so scanning from any phone
opens that table's live menu. Download/print and place on the tables.

---

## Go-live checklist

- [ ] `CORS_ORIGINS` on Render = your real frontend origin(s), no trailing slash
- [ ] `ADMIN_PASSWORD` changed from the default
- [ ] Razorpay **live** keys in place (after KYC) + webhook secret matching Render
- [ ] `OTP_DEMO_MODE=false` with a configured SMS provider
- [ ] `/health` green, a full test order pays through end-to-end
- [ ] (Durability) persistent disk enabled if you need orders to survive restarts
