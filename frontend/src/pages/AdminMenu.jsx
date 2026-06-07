import { useEffect, useState } from "react";
import { api, rupees, MENU_CATEGORIES } from "../api";
import AdminShell from "../components/AdminShell";
import { Button, Card, Input, Spinner, VegMark } from "../components/ui";

const BLANK = { name: "", description: "", price: "", category: MENU_CATEGORIES[0], veg: true, available: true };

export default function AdminMenu() {
  const [items, setItems] = useState(null);
  const [form, setForm] = useState(BLANK);
  const [editing, setEditing] = useState(null); // item id or null
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    try {
      setItems(await api.adminMenu());
    } catch (err) {
      setError(err.message.replace(/^\d+:\s*/, ""));
    }
  }
  useEffect(() => {
    load();
  }, []);

  function startEdit(item) {
    setEditing(item.id);
    setForm({ ...item, price: String(item.price) });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  function reset() {
    setEditing(null);
    setForm(BLANK);
    setError("");
  }

  async function save(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const payload = {
      name: form.name.trim(),
      description: form.description.trim(),
      price: Number(form.price),
      category: form.category,
      veg: form.veg,
      available: form.available,
    };
    try {
      if (editing) await api.updateMenuItem(editing, payload);
      else await api.createMenuItem(payload);
      reset();
      load();
    } catch (err) {
      setError(err.message.replace(/^\d+:\s*/, ""));
    } finally {
      setBusy(false);
    }
  }

  async function toggleAvailable(item) {
    await api.updateMenuItem(item.id, { available: !item.available });
    load();
  }
  async function remove(item) {
    if (!confirm(`Delete "${item.name}"?`)) return;
    await api.deleteMenuItem(item.id);
    load();
  }

  if (!items)
    return (
      <AdminShell>
        <div className="flex justify-center py-16">
          <Spinner className="text-club-orange" />
        </div>
      </AdminShell>
    );

  const byCat = {};
  for (const it of items) (byCat[it.category] ||= []).push(it);

  return (
    <AdminShell>
      <Card className="mb-6 p-5">
        <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-club-blue">
          {editing ? "Edit dish" : "Add a dish"}
        </h2>
        <form onSubmit={save} className="grid gap-3 sm:grid-cols-2">
          <Input
            placeholder="Dish name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
          />
          <Input
            type="number"
            step="1"
            min="0"
            placeholder="Price ₹"
            value={form.price}
            onChange={(e) => setForm({ ...form, price: e.target.value })}
            required
          />
          <Input
            className="sm:col-span-2"
            placeholder="Short description"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm"
          >
            {MENU_CATEGORIES.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
          <div className="flex items-center gap-4 px-1 text-sm">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.veg}
                onChange={(e) => setForm({ ...form, veg: e.target.checked })}
              />
              Veg
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.available}
                onChange={(e) => setForm({ ...form, available: e.target.checked })}
              />
              Available
            </label>
          </div>
          {error && <p className="text-sm text-red-600 sm:col-span-2">{error}</p>}
          <div className="flex gap-2 sm:col-span-2">
            <Button type="submit" disabled={busy}>
              {busy ? <Spinner /> : editing ? "Save changes" : "Add dish"}
            </Button>
            {editing && (
              <Button type="button" variant="outline" onClick={reset}>
                Cancel
              </Button>
            )}
          </div>
        </form>
      </Card>

      {MENU_CATEGORIES.filter((c) => byCat[c]).map((cat) => (
        <section key={cat} className="mb-5">
          <h3 className="mb-2 text-sm font-bold uppercase tracking-wide text-slate-500">{cat}</h3>
          <div className="space-y-2">
            {byCat[cat].map((item) => (
              <Card key={item.id} className="flex items-center justify-between gap-3 p-3">
                <div className="flex min-w-0 items-center gap-2">
                  <VegMark veg={item.veg} />
                  <div className="min-w-0">
                    <div className="truncate font-semibold text-slate-800">
                      {item.name}
                      {!item.available && (
                        <span className="ml-2 text-xs font-normal text-red-500">(hidden)</span>
                      )}
                    </div>
                    <div className="text-xs text-slate-500">{rupees(item.price)}</div>
                  </div>
                </div>
                <div className="flex shrink-0 gap-1">
                  <Button variant="outline" className="px-3 py-1.5 text-xs" onClick={() => toggleAvailable(item)}>
                    {item.available ? "Hide" : "Show"}
                  </Button>
                  <Button variant="ghost" className="px-3 py-1.5 text-xs" onClick={() => startEdit(item)}>
                    Edit
                  </Button>
                  <Button variant="ghost" className="px-2 py-1.5 text-xs text-red-500" onClick={() => remove(item)}>
                    ✕
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </section>
      ))}
    </AdminShell>
  );
}
