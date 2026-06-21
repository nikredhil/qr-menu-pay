import { useEffect, useState } from "react";
import { api } from "../api";
import AdminShell from "../components/AdminShell";
import { Card, Spinner } from "../components/ui";

// Staff view of guest feedback, newest first, with a satisfaction summary.
export default function AdminFeedback() {
  const [items, setItems] = useState(null);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [list, sum] = await Promise.all([api.adminFeedback(), api.feedbackSummary()]);
        if (!active) return;
        setItems(list);
        setSummary(sum);
      } catch (err) {
        if (active) setError(err.message.replace(/^\d+:\s*/, ""));
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  if (error) return <AdminShell>{<p className="text-red-600">{error}</p>}</AdminShell>;
  if (!items)
    return (
      <AdminShell>
        <div className="flex justify-center py-16">
          <Spinner className="text-club-orange" />
        </div>
      </AdminShell>
    );

  const sorted = [...items].sort((a, b) => (a.created_at < b.created_at ? 1 : -1));

  return (
    <AdminShell>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-bold text-slate-800">Guest feedback</h1>
        {summary && summary.count > 0 && (
          <div className="text-sm text-slate-500">
            <span className="font-bold text-club-orange">★ {summary.average_rating}</span> ·{" "}
            {summary.count} review{summary.count === 1 ? "" : "s"}
          </div>
        )}
      </div>

      {sorted.length === 0 && (
        <p className="py-16 text-center text-sm text-slate-400">No feedback yet.</p>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {sorted.map((f) => (
          <Card key={f.id} className="p-4">
            <div className="flex items-center justify-between">
              <Stars n={f.rating} />
              <span className="font-mono text-xs text-slate-400">{f.order_code}</span>
            </div>
            {f.comment && <p className="mt-2 text-sm text-slate-700">“{f.comment}”</p>}
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-400">
              {f.food_rating != null && <span>Food ★ {f.food_rating}</span>}
              {f.service_rating != null && <span>Service ★ {f.service_rating}</span>}
              <span>{f.table_label}</span>
              <span>{new Date(f.created_at).toLocaleString()}</span>
            </div>
          </Card>
        ))}
      </div>
    </AdminShell>
  );
}

function Stars({ n }) {
  return (
    <span className="text-club-orange">
      {"★".repeat(n)}
      <span className="text-slate-200">{"★".repeat(5 - n)}</span>
    </span>
  );
}
