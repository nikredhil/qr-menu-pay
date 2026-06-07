import { useEffect, useState } from "react";
import { api, rupees, STATUS_META, PAY_META } from "../api";
import AdminShell from "../components/AdminShell";
import { Badge, Button, Card, Spinner, VegMark } from "../components/ui";

const NEXT = { placed: "preparing", preparing: "served" };

export default function AdminOrders() {
  const [orders, setOrders] = useState(null);
  const [filter, setFilter] = useState("active"); // active | all
  const [error, setError] = useState("");

  async function load() {
    try {
      setOrders(await api.adminOrders());
    } catch (err) {
      setError(err.message.replace(/^\d+:\s*/, ""));
    }
  }

  useEffect(() => {
    load();
    const id = setInterval(load, 10000); // refresh the board
    return () => clearInterval(id);
  }, []);

  async function advance(o) {
    const next = NEXT[o.status];
    if (next) {
      await api.setOrderStatus(o.id, next);
      load();
    }
  }
  async function cancel(o) {
    await api.setOrderStatus(o.id, "cancelled");
    load();
  }
  async function collectCash(o) {
    await api.markCashCollected(o.id);
    load();
  }

  if (error) return <AdminShell>{<p className="text-red-600">{error}</p>}</AdminShell>;
  if (!orders)
    return (
      <AdminShell>
        <div className="flex justify-center py-16">
          <Spinner className="text-club-orange" />
        </div>
      </AdminShell>
    );

  const shown = orders.filter((o) =>
    filter === "active" ? o.status !== "served" && o.status !== "cancelled" : true
  );

  return (
    <AdminShell>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-bold text-slate-800">Orders</h1>
        <div className="flex rounded-xl border border-slate-300 bg-white p-0.5 text-sm">
          {["active", "all"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`rounded-lg px-3 py-1 font-medium capitalize ${
                filter === f ? "bg-club-orange text-white" : "text-slate-500"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {shown.length === 0 && (
        <p className="py-16 text-center text-sm text-slate-400">No orders here right now.</p>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {shown.map((o) => (
          <Card key={o.id} className="flex flex-col p-4">
            <div className="flex items-start justify-between">
              <div>
                <div className="font-mono text-lg font-bold text-club-blue">{o.code}</div>
                <div className="text-xs text-slate-500">
                  {o.table_label} · {new Date(o.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </div>
              </div>
              <div className="flex flex-col items-end gap-1">
                <Badge className={STATUS_META[o.status].className}>{STATUS_META[o.status].label}</Badge>
                <Badge className={PAY_META[o.payment_status].className}>
                  {o.payment_method === "cash" && o.payment_status !== "paid"
                    ? "Cash due"
                    : PAY_META[o.payment_status].label}
                </Badge>
              </div>
            </div>

            <ul className="my-3 flex-1 space-y-1 text-sm">
              {o.lines.map((l) => (
                <li key={l.menu_item_id} className="flex items-center gap-2 text-slate-700">
                  <VegMark veg={l.veg} />
                  <span className="flex-1 truncate">{l.name}</span>
                  <span className="text-slate-400">× {l.quantity}</span>
                </li>
              ))}
            </ul>

            {o.notes && (
              <p className="mb-2 rounded-lg bg-club-cream px-2 py-1 text-xs text-slate-600">{o.notes}</p>
            )}

            <div className="flex items-center justify-between border-t border-slate-100 pt-2">
              <span className="text-sm font-bold text-slate-800">{rupees(o.total)}</span>
              <span className="text-xs capitalize text-slate-400">{o.payment_method || "—"}</span>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {NEXT[o.status] && (
                <Button variant="green" className="flex-1 py-1.5 text-xs" onClick={() => advance(o)}>
                  Mark {STATUS_META[NEXT[o.status]].label}
                </Button>
              )}
              {o.payment_method === "cash" && o.payment_status !== "paid" && (
                <Button variant="primary" className="flex-1 py-1.5 text-xs" onClick={() => collectCash(o)}>
                  Cash collected
                </Button>
              )}
              {o.status !== "cancelled" && o.status !== "served" && (
                <Button variant="ghost" className="py-1.5 text-xs text-red-500" onClick={() => cancel(o)}>
                  Cancel
                </Button>
              )}
            </div>
          </Card>
        ))}
      </div>
    </AdminShell>
  );
}
