import { useEffect, useRef, useState } from "react";
import { Button } from "./ui";

// Realistic-looking (but entirely fake) payment screens for the demo. None of
// these move real money — each just calls onPaid() when the user "completes"
// the step, so the checkout can record a paid order.

const MERCHANT = "HSR Club Dine";
const VPA = "hsrclubdine@upi";

// ── UPI PIN pad (PhonePe / Google Pay / Paytm) ───────────────────────────────
export function UpiPinScreen({ method, amountLabel, onPaid, onBack }) {
  const [pin, setPin] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const fired = useRef(false); // ensure we complete exactly once

  useEffect(() => {
    if (pin.length === 6 && !fired.current) {
      fired.current = true;
      setSubmitting(true);
      // No cleanup here on purpose: a self-cancelling timeout would be cleared
      // by the re-render that setSubmitting triggers, leaving it stuck.
      setTimeout(() => onPaid(), 700);
    }
  }, [pin, onPaid]);

  const press = (d) => {
    if (submitting) return;
    setPin((p) => (p.length < 6 ? p + d : p));
  };
  const back = () => {
    if (submitting) return;
    setPin((p) => p.slice(0, -1));
  };

  return (
    <div className="-m-5 overflow-hidden rounded-t-3xl sm:rounded-3xl">
      {/* App header */}
      <div className="flex items-center gap-3 px-5 py-4 text-white" style={{ background: method.bg }}>
        <button onClick={onBack} className="text-xl leading-none">←</button>
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/20 text-sm font-bold">
          {method.mono}
        </span>
        <span className="font-semibold">{method.label}</span>
      </div>

      <div className="bg-white px-5 pb-5 pt-4">
        <div className="rounded-xl border border-slate-200 p-4">
          <div className="flex items-center justify-between">
            <div className="min-w-0">
              <p className="text-xs text-slate-400">Paying to</p>
              <p className="truncate font-semibold text-slate-800">{MERCHANT}</p>
              <p className="truncate text-xs text-slate-400">{VPA}</p>
            </div>
            <p className="shrink-0 text-lg font-bold text-slate-900">{amountLabel}</p>
          </div>
        </div>

        <p className="mt-5 text-center text-xs font-semibold uppercase tracking-wide text-slate-400">
          {submitting ? "Authorising…" : "Enter UPI PIN"}
        </p>
        <div className="mt-3 flex justify-center gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <span
              key={i}
              className={`h-3.5 w-3.5 rounded-full border ${
                i < pin.length ? "border-slate-800 bg-slate-800" : "border-slate-300"
              }`}
            />
          ))}
        </div>

        <div className="mx-auto mt-6 grid max-w-xs grid-cols-3 gap-2">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => (
            <Key key={n} onClick={() => press(String(n))} disabled={submitting}>
              {n}
            </Key>
          ))}
          <span />
          <Key onClick={() => press("0")} disabled={submitting}>0</Key>
          <Key onClick={back} disabled={submitting}>⌫</Key>
        </div>
        <p className="mt-5 text-center text-[11px] text-slate-400">🔒 Secured by UPI · Demo</p>
      </div>
    </div>
  );
}

function Key({ children, onClick, disabled }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="rounded-xl bg-slate-100 py-3 text-xl font-semibold text-slate-800 transition active:bg-slate-200 disabled:opacity-40"
    >
      {children}
    </button>
  );
}

// ── Card entry form ──────────────────────────────────────────────────────────
export function CardScreen({ amountLabel, onPaid, onBack }) {
  const [num, setNum] = useState("4111 1111 1111 1111");
  const [exp, setExp] = useState("12/28");
  const [cvv, setCvv] = useState("123");
  const [name, setName] = useState("HSR Club Member");
  const [busy, setBusy] = useState(false);

  const fmtNum = (v) =>
    v.replace(/\D/g, "").slice(0, 16).replace(/(.{4})/g, "$1 ").trim();
  const fmtExp = (v) => {
    const d = v.replace(/\D/g, "").slice(0, 4);
    return d.length > 2 ? `${d.slice(0, 2)}/${d.slice(2)}` : d;
  };

  const pay = () => {
    setBusy(true);
    setTimeout(onPaid, 900);
  };

  return (
    <div className="-m-5 overflow-hidden rounded-t-3xl sm:rounded-3xl">
      <div className="flex items-center gap-3 bg-slate-900 px-5 py-4 text-white">
        <button onClick={onBack} className="text-xl leading-none">←</button>
        <span className="font-semibold">Card Payment</span>
        <span className="ml-auto font-bold">{amountLabel}</span>
      </div>

      <div className="bg-white px-5 pb-5 pt-4">
        {/* Card visual */}
        <div className="mb-4 rounded-2xl bg-gradient-to-br from-slate-700 to-slate-900 p-4 text-white shadow-lg">
          <div className="flex justify-between text-xs opacity-70">
            <span>DEBIT / CREDIT</span>
            <span>VISA</span>
          </div>
          <p className="mt-4 font-mono text-lg tracking-widest">{num || "•••• •••• •••• ••••"}</p>
          <div className="mt-3 flex justify-between text-xs">
            <span className="truncate">{name || "CARDHOLDER"}</span>
            <span>{exp || "MM/YY"}</span>
          </div>
        </div>

        <div className="space-y-2">
          <Field label="Card number" value={num} onChange={(v) => setNum(fmtNum(v))} inputMode="numeric" />
          <div className="flex gap-2">
            <Field label="Expiry" value={exp} onChange={(v) => setExp(fmtExp(v))} inputMode="numeric" />
            <Field label="CVV" value={cvv} onChange={(v) => setCvv(v.replace(/\D/g, "").slice(0, 3))} inputMode="numeric" type="password" />
          </div>
          <Field label="Name on card" value={name} onChange={setName} />
        </div>

        <Button variant="primary" className="mt-4 w-full" onClick={pay} disabled={busy}>
          {busy ? "Processing…" : `Pay ${amountLabel}`}
        </Button>
        <p className="mt-3 text-center text-[11px] text-slate-400">🔒 256-bit encrypted · Demo</p>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, type = "text", inputMode }) {
  return (
    <label className="block flex-1">
      <span className="text-[11px] font-medium text-slate-400">{label}</span>
      <input
        type={type}
        inputMode={inputMode}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-0.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-800 outline-none focus:border-club-orange"
      />
    </label>
  );
}

// ── Netbanking (bank pick → login → success) ─────────────────────────────────
const BANKS = ["HDFC Bank", "ICICI Bank", "State Bank of India", "Axis Bank", "Kotak Mahindra"];

export function NetbankingScreen({ amountLabel, onPaid, onBack }) {
  const [bank, setBank] = useState(null);
  const [busy, setBusy] = useState(false);

  const login = () => {
    setBusy(true);
    setTimeout(onPaid, 1100);
  };

  return (
    <div className="-m-5 overflow-hidden rounded-t-3xl sm:rounded-3xl">
      <div className="flex items-center gap-3 bg-slate-700 px-5 py-4 text-white">
        <button onClick={bank ? () => setBank(null) : onBack} className="text-xl leading-none">←</button>
        <span className="font-semibold">🏦 {bank || "Netbanking"}</span>
        <span className="ml-auto font-bold">{amountLabel}</span>
      </div>

      <div className="bg-white px-5 pb-5 pt-4">
        {!bank ? (
          <>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Select your bank</p>
            <div className="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200">
              {BANKS.map((b) => (
                <button
                  key={b}
                  onClick={() => setBank(b)}
                  className="flex w-full items-center gap-3 px-3 py-3 text-left text-sm font-medium text-slate-800 hover:bg-slate-50"
                >
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-xs font-bold text-slate-500">
                    {b.slice(0, 2).toUpperCase()}
                  </span>
                  <span className="flex-1">{b}</span>
                  <span className="text-slate-300">›</span>
                </button>
              ))}
            </div>
          </>
        ) : (
          <>
            <p className="mb-3 text-sm text-slate-500">Log in to {bank} to authorise the payment.</p>
            <div className="space-y-2">
              <Field label="Customer ID" value="hsr_member" onChange={() => {}} />
              <Field label="Password" value="••••••••" onChange={() => {}} type="password" />
            </div>
            <Button variant="primary" className="mt-4 w-full" onClick={login} disabled={busy}>
              {busy ? "Authorising…" : `Login & Pay ${amountLabel}`}
            </Button>
          </>
        )}
        <p className="mt-4 text-center text-[11px] text-slate-400">🔒 Bank-grade encryption · Demo</p>
      </div>
    </div>
  );
}
