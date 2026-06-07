import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { setAdminToken } from "../auth";
import { Logo } from "../components/Brand";
import { Button, Card, Input, Spinner } from "../components/ui";

export default function AdminLogin() {
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await api.adminLogin(password);
      setAdminToken(res.access_token);
      navigate("/admin/orders", { replace: true });
    } catch (err) {
      setError(err.message.replace(/^\d+:\s*/, ""));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm p-7">
        <div className="flex flex-col items-center text-center">
          <Logo size={56} />
          <h1 className="mt-3 text-lg font-extrabold text-club-blue">Staff sign-in</h1>
          <p className="mt-1 text-xs text-slate-500">HSR Club Dine dashboard</p>
        </div>
        <form onSubmit={submit} className="mt-6 space-y-3">
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Staff password"
            autoFocus
            required
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" className="w-full" disabled={busy}>
            {busy ? <Spinner /> : "Sign in"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
