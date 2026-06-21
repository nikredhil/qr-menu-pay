import { useEffect, useState } from "react";
import { api, rupees } from "../api";
import AdminShell from "../components/AdminShell";
import { Card, Spinner } from "../components/ui";

// Sales analytics: today's takings, all-time totals, payment mix, top sellers,
// and guest satisfaction. Auto-refreshes so the counter screen stays live.
export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const s = await api.stats();
        if (active) setStats(s);
      } catch (err) {
        if (active) setError(err.message.replace(/^\d+:\s*/, ""));
      }
    }
    load();
    const id = setInterval(load, 15000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  if (error) return <AdminShell>{<p className="text-red-600">{error}</p>}</AdminShell>;
  if (!stats)
    return (
      <AdminShell>
        <div className="flex justify-center py-16">
          <Spinner className="text-club-orange" />
        </div>
      </AdminShell>
    );

  const maxQty = Math.max(1, ...stats.top_items.map((t) => t.quantity));

  return (
    <AdminShell>
      <h1 className="mb-4 text-lg font-bold text-slate-800">Dashboard</h1>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Today's revenue" value={rupees(stats.today.revenue)} accent />
        <Stat label="Today's orders" value={stats.today.orders} sub={`${stats.today.paid_orders} paid`} />
        <Stat label="All-time revenue" value={rupees(stats.all_time.revenue)} />
        <Stat
          label="Avg rating"
          value={stats.feedback_count ? `★ ${stats.average_rating}` : "—"}
          sub={`${stats.feedback_count} review${stats.feedback_count === 1 ? "" : "s"}`}
        />
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <Card className="p-4">
          <h2 className="mb-3 text-sm font-bold text-slate-700">Top sellers</h2>
          {stats.top_items.length === 0 ? (
            <p className="text-sm text-slate-400">No paid orders yet.</p>
          ) : (
            <ul className="space-y-2">
              {stats.top_items.map((t) => (
                <li key={t.menu_item_id}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="truncate text-slate-700">{t.name}</span>
                    <span className="ml-2 shrink-0 text-slate-500">
                      {t.quantity} · {rupees(t.revenue)}
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 rounded-full bg-slate-100">
                    <div
                      className="h-1.5 rounded-full bg-club-orange"
                      style={{ width: `${(t.quantity / maxQty) * 100}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="p-4">
          <h2 className="mb-3 text-sm font-bold text-slate-700">Breakdown</h2>
          <Group title="Payment mix" data={stats.payment_mix} />
          <Group title="Kitchen status" data={stats.status_mix} />
          <div className="mt-3 flex justify-between border-t border-slate-100 pt-3 text-sm">
            <span className="text-slate-500">Repeat diners (2+ visits)</span>
            <span className="font-semibold text-slate-800">{stats.repeat_customers}</span>
          </div>
        </Card>
      </div>
    </AdminShell>
  );
}

function Stat({ label, value, sub, accent }) {
  return (
    <Card className={`p-4 ${accent ? "ring-2 ring-club-orange/40" : ""}`}>
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-extrabold text-slate-800">{value}</div>
      {sub && <div className="mt-0.5 text-xs text-slate-400">{sub}</div>}
    </Card>
  );
}

function Group({ title, data }) {
  const entries = Object.entries(data || {});
  return (
    <div className="mb-2">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-400">{title}</div>
      {entries.length === 0 ? (
        <p className="text-sm text-slate-400">—</p>
      ) : (
        <ul className="mt-1 space-y-0.5">
          {entries.map(([k, v]) => (
            <li key={k} className="flex justify-between text-sm">
              <span className="capitalize text-slate-600">{k}</span>
              <span className="font-semibold text-slate-800">{v}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
