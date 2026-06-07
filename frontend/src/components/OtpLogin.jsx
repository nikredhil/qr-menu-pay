import { useState } from "react";
import { api } from "../api";
import { setCustomer } from "../auth";
import { Button, Input, Spinner } from "./ui";

// Two-step phone verification. On success it stores the customer session and
// calls onDone(customer). In demo mode the server returns the OTP, which we
// prefill so the flow is testable instantly.
export default function OtpLogin({ onDone }) {
  const [step, setStep] = useState("phone"); // "phone" | "code"
  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [hint, setHint] = useState("");

  async function sendOtp(e) {
    e?.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await api.requestOtp(phone, name);
      setStep("code");
      if (res.debug_otp) {
        setCode(res.debug_otp);
        setHint(`Demo mode — your code is ${res.debug_otp}`);
      } else {
        setHint(`Code sent to ${res.phone}`);
      }
    } catch (err) {
      setError(err.message.replace(/^\d+:\s*/, ""));
    } finally {
      setBusy(false);
    }
  }

  async function verify(e) {
    e?.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await api.verifyOtp(phone, code);
      setCustomer(res);
      onDone?.(res);
    } catch (err) {
      setError(err.message.replace(/^\d+:\s*/, ""));
    } finally {
      setBusy(false);
    }
  }

  if (step === "phone") {
    return (
      <form onSubmit={sendOtp} className="space-y-3">
        <div>
          <label className="text-xs font-medium text-slate-500">Your name (optional)</label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Ramesh"
            className="mt-1"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-slate-500">Mobile number</label>
          <Input
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            inputMode="numeric"
            placeholder="10-digit mobile"
            className="mt-1"
            required
          />
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <Button type="submit" disabled={busy} className="w-full">
          {busy ? <Spinner /> : "Send OTP"}
        </Button>
        <p className="text-center text-xs text-slate-400">
          We verify your number so we can text you order updates.
        </p>
      </form>
    );
  }

  return (
    <form onSubmit={verify} className="space-y-3">
      <div>
        <label className="text-xs font-medium text-slate-500">
          Enter the 6-digit code sent to +91 {phone}
        </label>
        <Input
          value={code}
          onChange={(e) => setCode(e.target.value)}
          inputMode="numeric"
          maxLength={8}
          placeholder="______"
          className="mt-1 text-center text-lg tracking-[0.4em]"
          required
        />
      </div>
      {hint && <p className="text-xs text-club-green">{hint}</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
      <Button type="submit" disabled={busy} className="w-full">
        {busy ? <Spinner /> : "Verify & continue"}
      </Button>
      <button
        type="button"
        className="w-full text-center text-xs text-slate-500 hover:underline"
        onClick={() => {
          setStep("phone");
          setCode("");
          setError("");
        }}
      >
        Change number
      </button>
    </form>
  );
}
