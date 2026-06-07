import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { api, BASE } from "../api";
import { CLUB } from "../branding";
import AdminShell from "../components/AdminShell";
import { Button, Card, Input, Spinner } from "../components/ui";

// The URL a table's QR encodes. We point at the SPA origin so scanning opens
// the menu directly. If you serve the SPA elsewhere, override VITE_PUBLIC_BASE.
const PUBLIC_BASE = (import.meta.env.VITE_PUBLIC_BASE || window.location.origin).replace(/\/$/, "");
const tableUrl = (id) => `${PUBLIC_BASE}/t/${encodeURIComponent(id)}`;

export default function AdminTables() {
  const [tables, setTables] = useState(null);
  const [form, setForm] = useState({ label: "", area: "", seats: 4 });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    try {
      setTables(await api.adminTables());
    } catch (err) {
      setError(err.message.replace(/^\d+:\s*/, ""));
    }
  }
  useEffect(() => {
    load();
  }, []);

  async function add(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.createTable({
        label: form.label.trim(),
        area: form.area.trim(),
        seats: Number(form.seats) || 1,
      });
      setForm({ label: "", area: "", seats: 4 });
      load();
    } catch (err) {
      setError(err.message.replace(/^\d+:\s*/, ""));
    } finally {
      setBusy(false);
    }
  }

  async function remove(t) {
    if (!confirm(`Delete ${t.label}?`)) return;
    await api.deleteTable(t.id);
    load();
  }

  if (!tables)
    return (
      <AdminShell>
        <div className="flex justify-center py-16">
          <Spinner className="text-club-orange" />
        </div>
      </AdminShell>
    );

  return (
    <AdminShell>
      <Card className="mb-6 p-5">
        <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-club-blue">Add a table</h2>
        <form onSubmit={add} className="grid gap-3 sm:grid-cols-4">
          <Input
            placeholder="Label (e.g. Table 11)"
            value={form.label}
            onChange={(e) => setForm({ ...form, label: e.target.value })}
            required
          />
          <Input
            placeholder="Area (e.g. Garden)"
            value={form.area}
            onChange={(e) => setForm({ ...form, area: e.target.value })}
          />
          <Input
            type="number"
            min="1"
            placeholder="Seats"
            value={form.seats}
            onChange={(e) => setForm({ ...form, seats: e.target.value })}
          />
          <Button type="submit" disabled={busy}>
            {busy ? <Spinner /> : "Add table"}
          </Button>
        </form>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        <p className="mt-3 text-xs text-slate-400">
          API base for scans: <span className="font-mono">{BASE}</span>. Print each QR and place it on
          the matching table — scanning opens that table's menu.
        </p>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {tables.map((t) => (
          <TableCard key={t.id} table={t} onDelete={() => remove(t)} />
        ))}
      </div>
    </AdminShell>
  );
}

function TableCard({ table, onDelete }) {
  const [dataUrl, setDataUrl] = useState("");
  const url = tableUrl(table.id);

  useEffect(() => {
    QRCode.toDataURL(url, { width: 320, margin: 1, color: { dark: "#1f5fa8", light: "#ffffff" } })
      .then(setDataUrl)
      .catch(() => setDataUrl(""));
  }, [url]);

  function download() {
    const a = document.createElement("a");
    a.href = dataUrl;
    a.download = `${CLUB.name}-${table.id}-QR.png`;
    a.click();
  }

  return (
    <Card className="flex flex-col items-center p-4 text-center">
      <div className="text-base font-bold text-slate-800">{table.label}</div>
      <div className="text-xs text-slate-400">
        {table.area || "—"} · {table.seats} seats · code {table.id}
      </div>
      <div className="my-3 rounded-xl bg-white p-2 ring-1 ring-slate-200">
        {dataUrl ? (
          <img src={dataUrl} alt={`QR for ${table.label}`} className="h-44 w-44" />
        ) : (
          <div className="flex h-44 w-44 items-center justify-center">
            <Spinner className="text-club-orange" />
          </div>
        )}
      </div>
      <div className="flex gap-2">
        <Button variant="outline" className="px-3 py-1.5 text-xs" onClick={download} disabled={!dataUrl}>
          Download PNG
        </Button>
        <Button variant="ghost" className="px-3 py-1.5 text-xs text-red-500" onClick={onDelete}>
          Delete
        </Button>
      </div>
    </Card>
  );
}
