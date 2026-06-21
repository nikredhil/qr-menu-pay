# HSR Club Dine 🍽️

A QR-code dine-in ordering + payment app for **HSR Club** (HSR Layout, Bengaluru).
A member scans the QR on their table, verifies their phone with a one-time OTP,
browses the menu, places an order, and pays by **UPI (Google Pay / PhonePe /
Paytm)**, **credit / debit card**, or **cash at the counter**. Staff get a live
dashboard to manage the menu, print table QR codes, and run the kitchen board.

Built with the same stack as the sibling RentWise app: **FastAPI** (async
repositories, JWT auth) + a **React / Vite / Tailwind** SPA.

```
Scan QR  →  Phone OTP  →  Menu & cart  →  Pay (UPI / card / cash)  →  Live order status
                                                      │
                                          Staff dashboard: menu · QR codes · orders
```

## What's real, and what needs your keys

| Capability | Out of the box | With your credentials |
|---|---|---|
| **QR → table menu** | ✅ Real QR codes are generated per table, encoding `/.../t/<table>` | — |
| **Phone OTP** | ✅ Demo mode — the code is shown on screen so the flow is fully testable | Set `OTP_DEMO_MODE=false` and add **Twilio** or **MSG91** credentials to send real SMS (both wired in `app/services/sms.py`) |
| **UPI / card payment** | ✅ Built-in **demo gateway** completes the flow and records a paid order (no real money) | Add **Razorpay** keys → real Razorpay Checkout (UPI + cards + netbanking). Test keys work immediately; live keys after KYC take real money |
| **Cash** | ✅ Order is placed and marked payable at the counter; staff confirm collection | — |

> Moving real money requires a payment-gateway merchant account (KYC). That's
> the one thing this repo can't fabricate — but the moment you paste Razorpay
> test keys into `.env`, the exact same checkout runs against the real gateway.

> **Production is a real product, not a demo.** When `ENVIRONMENT=prod` the app
> *refuses to boot* with demo OTP, an unconfigured (demo) payment gateway, the
> default JWT secret / admin password, or wildcard CORS. The demo OTP and demo
> gateway exist only to make local dev runnable with zero setup.

## Full feature set

A complete digital-menu ordering product (in the spirit of mydigimenu):

**For diners**
- 📱 **QR → table menu** with food **photos**, veg/non-veg marks, live search & category sections
- 🌐 **Multi-language menu** — switch language on the fly (English / Hindi / Kannada out of the box; configurable)
- 🔐 **Phone-OTP sign-in**, cart, server-computed totals + GST
- 💳 **Pay by UPI / card (Razorpay)** or **cash at the counter**
- 🔔 **SMS / WhatsApp updates** when the order is placed and served
- ⭐ **Post-payment feedback** — rate food & service, leave a comment

**For staff**
- 🍳 **Live kitchen (KOT) board** — new orders appear with a sound alert; advance Placed → Preparing → Served
- 📊 **Sales analytics dashboard** — today's revenue, order counts, top sellers, payment mix, repeat diners, avg rating
- 🗒️ **Menu management** with photos & availability toggles · **table QR** printing
- 💬 **Guest feedback** board
- 🏢 **Multi-outlet** — one backend can serve several branches; each table/menu/order is outlet-scoped
- 🎁 **Loyalty** — visits, spend, and points tracked per diner automatically

**Deploying?** See [DEPLOY.md](DEPLOY.md) for the full Render (backend) + Vercel
(frontend) walkthrough, including the Razorpay webhook and real SMS setup.

## Run it locally

### 1. Backend (port 8000)

```bash
cd qr-menu-pay
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m scripts.seed_data          # loads the HSR Club menu + 10 tables
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 2. Frontend (port 5174)

```bash
cd qr-menu-pay/frontend
npm install
cp .env.example .env                 # VITE_API_BASE defaults to http://localhost:8000
npm run dev
```

Open http://localhost:5174 — the home page lists the seeded tables so you can
jump into one without a physical QR. Or go straight to a table:
http://localhost:5174/t/TABLE1

### Staff dashboard

http://localhost:5174/admin — sign in with the `ADMIN_PASSWORD` from `.env`
(default `hsrclub-admin`). Manage the menu, generate/print table QR codes, and
work the live orders board.

## Testing the QR flow on a real phone

1. Find your computer's LAN IP (e.g. `192.168.1.20`).
2. In `frontend/.env` set `VITE_API_BASE=http://192.168.1.20:8000`.
3. Start the API with `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
4. `npm run dev` already binds all interfaces (`host: true`).
5. In the staff dashboard → **Tables & QR**, download/print a table's QR. Scan it
   with your phone (on the same Wi-Fi) — it opens that table's menu.

## Turning on real Razorpay payments

1. Create a Razorpay account → **Settings → API Keys** → generate **Test** keys.
2. In `qr-menu-pay/.env`:
   ```
   RAZORPAY_KEY_ID=rzp_test_xxxxxxxx
   RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxx
   ```
3. Restart the API. `/config` now reports `payment_provider: razorpay`, and the
   checkout opens the real Razorpay sheet (UPI / cards / netbanking) in test
   mode. Use Razorpay's [test cards / test UPI](https://razorpay.com/docs/payments/payments/test-card-details/).
4. After completing Razorpay KYC, swap in **live** keys to accept real payments.

The backend creates the Razorpay order server-side and verifies the
HMAC-SHA256 signature on return (`app/services/payment_service.py`), so a client
can never fake a successful payment.

## Project layout

```
qr-menu-pay/
├── app/
│   ├── main.py                 # app factory, lifespan wiring, routers
│   ├── core/                   # config, security (JWT), logging, deps
│   ├── db/repositories/        # base + in-memory + JSON-file backends
│   ├── models/schemas/         # menu, table, auth, order, payment models
│   ├── services/               # menu, table, otp, sms, order, payment, customer
│   └── api/routers/            # health, auth, menu, tables, orders, payments
├── scripts/seed_data.py        # HSR Club menu + tables
├── data/                       # JSON store (gitignored)
└── frontend/
    └── src/
        ├── pages/              # TableMenu, OrderStatus, Landing, Admin*
        ├── components/         # OtpLogin, Checkout, AdminShell, Brand, ui
        ├── payments.js         # Razorpay Checkout loader + demo fallback
        ├── api.js / auth.js    # API client + customer/admin sessions
        └── branding.js         # HSR Club name, address, contacts
```

## Security notes

- Prices and totals are computed **server-side** from the live menu — the client
  only sends item ids and quantities, so it can't dictate a price.
- Customers can only read/pay their **own** orders (scoped by phone in the JWT).
- Staff endpoints require the admin token; OTP codes are one-time-use with an
  attempt cap and TTL.
- **Rate limiting** (per client IP) on OTP request/verify and admin login —
  returns 429 + `Retry-After`, blunting SMS-bombing and password brute-force.
- **Security headers** on every response (`X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`; HSTS in prod).
- **Fail-fast prod guard:** with `ENVIRONMENT=prod`, the app refuses to boot on
  insecure defaults (`JWT_SECRET`/`ADMIN_PASSWORD`) or `CORS_ORIGINS='*'`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest        # 29 tests: flows, authz, rate limits, signature verify, config guard
```

The suite runs fully offline (in-memory store, demo gateway) — no network, no
real keys, no data files touched.
