# Production deployment — HSR Club Dine

A step-by-step runbook. Two pieces go live separately:

- **Backend** (FastAPI) → **Render** (or any host; a `Dockerfile` is included)
- **Frontend** (Vite SPA) → **Vercel** (or Netlify)

The repo configs (`render.yaml`, `frontend/vercel.json`, `Dockerfile`) make this
mostly click-through. The app also **refuses to boot in production with insecure
config** (default `JWT_SECRET`/`ADMIN_PASSWORD`, or `CORS_ORIGINS='*'`), so you
can't accidentally ship the dev defaults.

---

## Step 0 — Prerequisites

**a. Run the tests** (sanity check before shipping):
```bash
cd qr-menu-pay
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest                       # 29 tests should pass
```

**b. Generate the two secrets** you'll paste into the host:
```bash
python -c "import secrets; print('JWT_SECRET     =', secrets.token_hex(32))"
python -c "import secrets; print('ADMIN_PASSWORD =', secrets.token_urlsafe(18))"
```
Keep these somewhere safe (a password manager). **Never** commit them or paste
them into chat.

**c. Push to GitHub** (from `qr-menu-pay/`):
```bash
gh repo create hsr-club-dine --private --source=. --push
# or: create the repo on github.com, then `git remote add origin … && git push -u origin main`
```

---

## Step 1 — Backend on Render

**1a. Provision a free Postgres (Neon).** Orders are written concurrently during
a rush, so the app uses Postgres (`DB_BACKEND=sql`) rather than the single-writer
JSON file. [Neon](https://neon.tech)'s free tier is durable and needs no card:

   1. Create a project → copy the **Pooled** connection string (the host
      contains `-pooler`). Either `postgres://…` or `postgresql://…` is fine —
      it's normalised to the async driver automatically.
   2. You'll paste it as `DATABASE_URL` below. The tables and indexes are created
      automatically on first boot; `scripts/migrate_json_to_sql.py` (run from the
      start command) loads the seeded menu/tables in.

1. **Render → New → Blueprint**, pick the `hsr-club-dine` repo. It reads
   [`render.yaml`](render.yaml) and proposes the `hsr-club-dine-api` service.
2. Set the secret env vars (Render prompts for everything marked `sync:false`):

   | Key | Value |
   |---|---|
   | `JWT_SECRET` | the value generated in Step 0b (or let Render auto-generate) |
   | `ADMIN_PASSWORD` | the value from Step 0b |
   | `RAZORPAY_KEY_ID` | `rzp_test_…` first; `rzp_live_…` after KYC |
   | `RAZORPAY_KEY_SECRET` | the matching secret |
   | `RAZORPAY_WEBHOOK_SECRET` | the secret you set in Step 3 |
   | `DATABASE_URL` | the Neon **pooled** connection string (Step 1a) |

   `ENVIRONMENT=prod`, `DB_BACKEND=sql`, and `CORS_ORIGINS` are already in the
   blueprint — you'll finalize `CORS_ORIGINS` in Step 2 once you know the
   frontend URL.
3. **Create** and wait for the build. Confirm:
   - `https://<api>.onrender.com/health` → `{"status":"ok"}`
   - `https://<api>.onrender.com/docs` loads
   - If you set insecure values by mistake, the service **fails to boot** with a
     clear log line — fix the env var and redeploy.

> **Data durability & scale:** with `DB_BACKEND=sql`, orders live in Postgres
> and survive Render redeploys/sleep — no persistent disk needed. A single
> Render worker on Neon comfortably absorbs a busy single-venue rush (hundreds of
> concurrent orders), because each write is an independent indexed upsert rather
> than a whole-file rewrite under one lock. To scale to *multiple* API instances
> later, also move the in-memory rate-limit and OTP state (`app/core/rate_limit.py`,
> `app/services/otp_service.py`) to a shared store like Redis — not needed for one
> venue on one worker.

---

## Step 2 — Frontend on Vercel

1. **Vercel → Add New → Project**, import the same repo.
2. **Root Directory → `frontend`**. Vercel auto-detects Vite and reads
   [`frontend/vercel.json`](frontend/vercel.json) (SPA rewrite so `/t/<table>`
   deep links resolve on scan/refresh).
3. **Environment variable:**
   | Key | Value |
   |---|---|
   | `VITE_API_BASE` | `https://<api>.onrender.com` (your Render URL) |
4. **Deploy** → you get `https://hsr-club-dine.vercel.app` (or a custom domain,
   e.g. `dine.hsrclub.in`).
5. **Back on Render**, set `CORS_ORIGINS` to that exact origin (comma-separate if
   several, no trailing slash), then redeploy the API.

---

## Step 3 — Razorpay (real payments)

1. Razorpay Dashboard → **Settings → API Keys** → generate **Test** keys first
   (no KYC needed); put them on Render (Step 1). Test a full order end-to-end with
   [test instruments](https://razorpay.com/docs/payments/payments/test-card-details/)
   (card `4111 1111 1111 1111`, or UPI `success@razorpay`).
2. **Webhook** (once the API URL exists): **Settings → Webhooks → Add**:
   - URL: `https://<api>.onrender.com/payments/razorpay/webhook`
   - Secret: choose one → set it as `RAZORPAY_WEBHOOK_SECRET` on Render
   - Active events: `payment.captured`, `payment.failed`, `order.paid`

   This is the reliable source of truth — an order is marked paid server-to-server
   even if the customer's browser closes mid-payment.
3. **Go live:** complete Razorpay **KYC** (business + bank proof) → generate
   **Live** keys (`rzp_live_…`) → replace the test keys on Render. Same code.

---

## Step 4 — Real OTP SMS

Default is demo mode (code shown on screen). For production set
`OTP_DEMO_MODE=false` on Render and configure one provider:

**MSG91 (recommended for India):**
```
OTP_PROVIDER=msg91
MSG91_AUTH_KEY=…
MSG91_TEMPLATE_ID=…     # DLT-approved Flow template with one variable for the code
MSG91_SENDER_ID=…       # your 6-char DLT sender id
MSG91_OTP_VAR=otp       # the template's variable name
```

**Twilio (global):**
```
OTP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=…
TWILIO_AUTH_TOKEN=…
TWILIO_FROM_NUMBER=+1…  # SMS-capable Twilio number (E.164)
```
Missing credentials → safe fallback to demo mode (logged warning), never a silent
failure. India requires DLT registration with either provider.

---

## Step 5 — Print the table QR codes

Sign in at `https://<frontend>/admin` with `ADMIN_PASSWORD` → **Tables & QR**.
Add your real tables; each QR encodes `https://<frontend>/t/<table>`. Download and
print, place on the tables. Scanning from any phone opens that table's live menu.

---

## Production checklist

Security (the boot guard enforces the first three):
- [x] `ENVIRONMENT=prod`
- [x] `JWT_SECRET` = strong random (not the default)
- [x] `ADMIN_PASSWORD` = strong (not the default)
- [x] `CORS_ORIGINS` = your real frontend origin(s), no `*`, no trailing slash
- [ ] Razorpay **live** keys + webhook secret matching Render
- [ ] `OTP_DEMO_MODE=false` with a configured SMS provider
- [ ] HTTPS everywhere (Render + Vercel give this automatically; HSTS is sent in prod)

Built-in protections (already on): per-IP rate limits on OTP request/verify and
admin login (429 + `Retry-After`); server-side price/total computation; one-time
OTP with attempt cap + TTL; orders scoped to the owning phone; security headers.

Operational:
- [ ] `/health` green; a full test order pays through end-to-end
- [ ] `DATABASE_URL` set to the Neon **pooled** string; orders persist across a redeploy
- [ ] Secrets stored only in the host dashboard (never in git/chat)

---

## Alternative: Docker

A `Dockerfile` is included for any container host:
```bash
docker build -t hsr-club-dine-api .
docker run -p 8000:8000 --env-file .env hsr-club-dine-api
```
