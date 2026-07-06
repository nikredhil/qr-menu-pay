import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, rupees } from "../api";
import { getCustomer, clearCustomer } from "../auth";
import { payWithRazorpay } from "../payments";
import { Button, Spinner, VegMark } from "./ui";
import OtpLogin from "./OtpLogin";

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
                {provider === "demo" ? " — demo gateway" : ""}
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

function DemoGateway({ intent, busy, error, onResult }) {
  return (
    <div className="space-y-4 text-center">
      <div className="rounded-xl border border-dashed border-club-orange/50 bg-club-cream p-4">
        <p className="text-sm font-semibold text-slate-700">Demo payment gateway</p>
        <p className="mt-1 text-xs text-slate-500">
          No Razorpay keys are configured, so no real money moves. This stands in for the UPI /
          card sheet your members would see. Add test keys to run real Razorpay Checkout.
        </p>
        <p className="mt-2 text-lg font-bold text-club-blue">{rupees(intent.amount / 100)}</p>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="grid grid-cols-2 gap-2">
        <Button variant="green" onClick={() => onResult("success")} disabled={busy}>
          {busy ? <Spinner /> : "Simulate success"}
        </Button>
        <Button variant="danger" onClick={() => onResult("fail")} disabled={busy}>
          Simulate failure
        </Button>
      </div>
    </div>
  );
}
