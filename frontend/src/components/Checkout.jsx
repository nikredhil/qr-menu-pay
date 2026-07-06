import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, rupees } from "../api";
import { getCustomer, clearCustomer } from "../auth";
import { payWithRazorpay } from "../payments";
import { Button, Spinner, VegMark } from "./ui";
import OtpLogin from "./OtpLogin";
import { UpiPinScreen, CardScreen, NetbankingScreen } from "./PaymentMock";

// Slide-up sheet that takes the cart through: verify phone → choose payment →
// pay (Razorpay/UPI/card, the built-in demo gateway, or cash) → order page.
export default function Checkout({ table, lines, notes, totals, provider, onClose }) {
  const navigate = useNavigate();
  const [customer, setCustomerState] = useState(getCustomer());
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [demoIntent, setDemoIntent] = useState(null); // {order, intent} when demo gateway
  const [itemNotes, setItemNotes] = useState({}); // { lineId: "no onions" }

  async function createOrder() {
    const items = lines.map((l) => ({
      menu_item_id: l.id,
      quantity: l.qty,
      notes: (itemNotes[l.id] || "").trim(),
    }));
    return api.placeOrder({ table_id: table.id, items, notes });
  }

  // If the session token was rejected (expired/invalid), drop it and send the
  // diner back to the OTP step instead of showing a dead-end error.
  function handleError(err) {
    const msg = err.message || "";
    if (msg.startsWith("401") || /token|sign-in/i.test(msg)) {
      clearCustomer();
      setCustomerState(null);
      setDemoIntent(null);
      setError("Your session expired — please verify your number again.");
    } else {
      setError(msg.replace(/^\d+:\s*/, ""));
    }
  }

  async function payOnline() {
    setError("");
    setBusy("online");
    try {
      const order = await createOrder();
      const intent = await api.createIntent(order.id);
      if (intent.provider === "razorpay") {
        await payWithRazorpay(intent, { name: customer?.name, contact: customer?.phone });
        navigate(`/order/${order.id}`);
      } else {
        // Demo gateway: show a simulate step instead of a real sheet.
        setDemoIntent({ order, intent });
      }
    } catch (err) {
      handleError(err);
    } finally {
      setBusy("");
    }
  }

  async function finishDemo(outcome) {
    setError("");
    setBusy("demo");
    try {
      await api.confirmDemo(demoIntent.order.id, demoIntent.intent.razorpay_order_id, outcome);
      navigate(`/order/${demoIntent.order.id}`);
    } catch (err) {
      handleError(err);
    } finally {
      setBusy("");
    }
  }

  async function payCash() {
    setError("");
    setBusy("cash");
    try {
      const order = await createOrder();
      await api.payCash(order.id);
      navigate(`/order/${order.id}`);
    } catch (err) {
      handleError(err);
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 sm:items-center">
      <div className="max-h-[92vh] w-full max-w-md overflow-y-auto rounded-t-3xl bg-white p-5 shadow-2xl sm:rounded-3xl">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-800">
            {customer ? "Checkout" : "Verify your number"}
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600" aria-label="Close">
            ✕
          </button>
        </div>

        <div className="mb-4 rounded-xl bg-club-cream px-3 py-2 text-sm text-slate-600">
          {table.label}
          {table.area ? ` · ${table.area}` : ""}
        </div>

        {!customer ? (
          <>
            {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
            <OtpLogin onDone={(c) => setCustomerState(c)} />
          </>
        ) : demoIntent ? (
          <DemoGateway
            intent={demoIntent.intent}
            busy={busy === "demo"}
            error={error}
            onResult={finishDemo}
          />
        ) : (
          <>
            <ul className="mb-3 divide-y divide-slate-100">
              {lines.map((l) => (
                <li key={l.id} className="py-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <VegMark veg={l.veg} />
                      <span className="text-slate-700">
                        {l.name} <span className="text-slate-400">× {l.qty}</span>
                      </span>
                    </span>
                    <span className="font-medium text-slate-700">{rupees(l.price * l.qty)}</span>
                  </div>
                  <input
                    value={itemNotes[l.id] || ""}
                    onChange={(e) => setItemNotes((n) => ({ ...n, [l.id]: e.target.value }))}
                    maxLength={200}
                    placeholder="Note for the kitchen (e.g. no onions)"
                    className="mt-1.5 w-full rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-600 outline-none focus:border-club-orange focus:bg-white"
                  />
                </li>
              ))}
            </ul>
            <div className="mb-4 space-y-1 border-t border-slate-100 pt-3 text-sm">
              <Row label="Subtotal" value={rupees(totals.subtotal)} />
              <Row label="GST (5%)" value={rupees(totals.tax)} />
              <Row label="Total" value={rupees(totals.total)} bold />
            </div>

            {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

            <div className="space-y-2">
              <Button variant="primary" className="w-full" onClick={payOnline} disabled={!!busy}>
                {busy === "online" ? <Spinner /> : `Pay ${rupees(totals.total)} — UPI / Card`}
              </Button>
              <p className="text-center text-[11px] text-slate-400">
                Google Pay · PhonePe · Paytm · Credit / Debit card
              </p>
              <Button variant="outline" className="w-full" onClick={payCash} disabled={!!busy}>
                {busy === "cash" ? <Spinner /> : "Pay with Cash at counter"}
              </Button>
            </div>
            <p className="mt-3 text-center text-xs text-slate-400">
              Signed in as +91 {customer.phone}
            </p>
          </>
        )}
      </div>
    </div>
  );
}

function Row({ label, value, bold }) {
  return (
    <div className={`flex justify-between ${bold ? "text-base font-bold text-slate-800" : "text-slate-500"}`}>
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}

// Payment methods shown in the sheet. Each renders a coloured monogram so the
// list reads like a real gateway without loading any external logos.
const PAY_METHODS = [
  { id: "phonepe", label: "PhonePe", sub: "UPI", mono: "Pe", bg: "#5f259f" },
  { id: "gpay", label: "Google Pay", sub: "UPI", mono: "G", bg: "#1a73e8" },
  { id: "paytm", label: "Paytm", sub: "UPI · Wallet", mono: "P", bg: "#00baf2" },
  { id: "card", label: "Credit / Debit Card", sub: "Visa · Mastercard · RuPay", mono: "💳", bg: "#0f172a" },
  { id: "netbanking", label: "Netbanking", sub: "All major banks", mono: "🏦", bg: "#334155" },
];

function DemoGateway({ intent, error, onResult }) {
  const [step, setStep] = useState("select"); // select | upi | card | netbanking | processing | done
  const [method, setMethod] = useState(null);
  const amount = rupees(intent.amount / 100);

  function choose(m) {
    setMethod(m);
    if (m.id === "card") setStep("card");
    else if (m.id === "netbanking") setStep("netbanking");
    else setStep("upi"); // phonepe / gpay / paytm
  }

  // Called by a method screen once the diner "completes" it. Show the
  // processing → received animation, then confirm on the server + navigate.
  function complete() {
    setStep("processing");
    setTimeout(() => {
      setStep("done");
      setTimeout(() => onResult("success"), 1100);
    }, 1600);
  }

  if (step === "upi") {
    return (
      <UpiPinScreen method={method} amountLabel={amount} onPaid={complete} onBack={() => setStep("select")} />
    );
  }
  if (step === "card") {
    return <CardScreen amountLabel={amount} onPaid={complete} onBack={() => setStep("select")} />;
  }
  if (step === "netbanking") {
    return <NetbankingScreen amountLabel={amount} onPaid={complete} onBack={() => setStep("select")} />;
  }

  if (step === "processing" || step === "done") {
    const done = step === "done";
    return (
      <div className="flex flex-col items-center gap-3 py-8 text-center">
        {done ? (
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100 text-4xl text-green-600">
            ✓
          </div>
        ) : (
          <span className="inline-block h-10 w-10 animate-spin rounded-full border-4 border-club-orange border-t-transparent" />
        )}
        <p className="text-lg font-bold text-slate-800">
          {done ? "Payment received" : "Processing payment…"}
        </p>
        <p className="text-2xl font-bold text-club-blue">{amount}</p>
        <p className="text-xs text-slate-400">
          {done ? "Confirming your order…" : `via ${method?.label}`}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="rounded-xl bg-club-cream px-4 py-3 text-center">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Amount payable</p>
        <p className="mt-0.5 text-2xl font-bold text-club-blue">{amount}</p>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <p className="px-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
        Choose a payment method
      </p>
      <div className="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200">
        {PAY_METHODS.map((m) => (
          <button
            key={m.id}
            onClick={() => choose(m)}
            className="flex w-full items-center gap-3 px-3 py-3 text-left transition hover:bg-slate-50"
          >
            <span
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-sm font-bold text-white"
              style={{ backgroundColor: m.bg }}
            >
              {m.mono}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-semibold text-slate-800">{m.label}</span>
              <span className="block text-xs text-slate-400">{m.sub}</span>
            </span>
            <span className="text-slate-300">›</span>
          </button>
        ))}
      </div>
      <p className="flex items-center justify-center gap-1 pt-1 text-center text-[11px] text-slate-400">
        <span>🔒</span> Payments are secure &amp; encrypted
      </p>
    </div>
  );
}
