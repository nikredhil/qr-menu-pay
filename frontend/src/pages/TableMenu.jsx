import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, rupees, localizeItem, LANGUAGE_NAMES } from "../api";
import { Header, Footer } from "../components/Brand";
import { Button, Card, Spinner, VegMark } from "../components/ui";
import Checkout from "../components/Checkout";

const TAX_RATE = 0.05; // mirrors the server (GST on dining)
const cartKey = (tableId) => `hsr_cart_${tableId}`;

export default function TableMenu() {
  const { tableId } = useParams();
  const [table, setTable] = useState(null);
  const [menu, setMenu] = useState([]);
  const [provider, setProvider] = useState("demo");
  const [languages, setLanguages] = useState(["en"]);
  const [lang, setLang] = useState("en");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [cart, setCart] = useState({}); // { itemId: qty }
  const [vegOnly, setVegOnly] = useState(false);
  const [query, setQuery] = useState("");
  const [notes, setNotes] = useState("");
  const [checkout, setCheckout] = useState(false);

  // Load table + config, then the menu scoped to that table's outlet.
  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      try {
        const [t, cfg] = await Promise.all([api.getTable(tableId), api.config()]);
        if (!active) return;
        setTable(t);
        setProvider(cfg.payment_provider);
        setLanguages(cfg.languages?.length ? cfg.languages : ["en"]);
        setLang(cfg.default_language || "en");
        const m = await api.menu(t.outlet_id || undefined);
        if (active) setMenu(m);
      } catch (err) {
        if (active) setError(err.message.replace(/^\d+:\s*/, ""));
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [tableId]);

  // Restore / persist cart per table.
  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(cartKey(tableId)) || "{}");
      setCart(saved);
    } catch {
      setCart({});
    }
  }, [tableId]);
  useEffect(() => {
    localStorage.setItem(cartKey(tableId), JSON.stringify(cart));
  }, [cart, tableId]);

  const byId = useMemo(() => Object.fromEntries(menu.map((m) => [m.id, m])), [menu]);

  const categories = useMemo(() => {
    const q = query.toLowerCase();
    const filtered = menu.filter((m) => {
      if (vegOnly && !m.veg) return false;
      if (q && !localizeItem(m, lang).name.toLowerCase().includes(q)) return false;
      return true;
    });
    const groups = {};
    for (const item of filtered) (groups[item.category] ||= []).push(item);
    return groups;
  }, [menu, vegOnly, query, lang]);

  const lines = useMemo(
    () =>
      Object.entries(cart)
        .filter(([id, qty]) => qty > 0 && byId[id])
        .map(([id, qty]) => ({ ...byId[id], qty })),
    [cart, byId]
  );

  const totals = useMemo(() => {
    const subtotal = lines.reduce((s, l) => s + l.price * l.qty, 0);
    const tax = Math.round(subtotal * TAX_RATE * 100) / 100;
    return { subtotal, tax, total: Math.round((subtotal + tax) * 100) / 100 };
  }, [lines]);

  const count = lines.reduce((s, l) => s + l.qty, 0);

  function setQty(id, qty) {
    setCart((c) => {
      const next = { ...c };
      if (qty <= 0) delete next[id];
      else next[id] = qty;
      return next;
    });
  }

  if (loading) {
    return (
      <Centered>
        <Spinner className="text-club-orange" />
      </Centered>
    );
  }
  if (error || !table) {
    return (
      <Centered>
        <Card className="max-w-sm p-6 text-center">
          <p className="text-2xl">🍽️</p>
          <p className="mt-2 font-semibold text-slate-700">This table couldn't be found</p>
          <p className="mt-1 text-sm text-slate-500">{error || "Please scan the QR on your table again."}</p>
          <Link to="/" className="mt-4 inline-block text-sm font-medium text-club-orange">
            Go to home
          </Link>
        </Card>
      </Centered>
    );
  }

  return (
    <div className="min-h-full pb-28">
      <Header subtitle={`${table.label}${table.area ? ` · ${table.area}` : ""}`} />

      <main className="mx-auto max-w-3xl px-4">
        <div className="sticky top-[60px] z-10 -mx-4 bg-club-cream/95 px-4 py-3 backdrop-blur">
          <div className="flex items-center gap-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search dishes…"
              className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-sm outline-none focus:border-club-orange"
            />
            <button
              onClick={() => setVegOnly((v) => !v)}
              className={`shrink-0 rounded-xl border px-3 py-2 text-xs font-semibold ${
                vegOnly ? "border-green-600 bg-green-50 text-green-700" : "border-slate-300 bg-white text-slate-500"
              }`}
            >
              Veg only
            </button>
            {languages.length > 1 && (
              <select
                value={lang}
                onChange={(e) => setLang(e.target.value)}
                aria-label="Menu language"
                className="shrink-0 rounded-xl border border-slate-300 bg-white px-2 py-2 text-xs font-semibold text-slate-600 outline-none focus:border-club-orange"
              >
                {languages.map((code) => (
                  <option key={code} value={code}>
                    {LANGUAGE_NAMES[code] || code.toUpperCase()}
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>

        {Object.keys(categories).length === 0 && (
          <p className="py-10 text-center text-sm text-slate-400">No dishes match your search.</p>
        )}

        {Object.entries(categories).map(([cat, items]) => (
          <section key={cat} className="mt-5">
            <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-club-blue">{cat}</h2>
            <div className="space-y-2">
              {items.map((item) => {
                const loc = localizeItem(item, lang);
                return (
                  <Card key={item.id} className="flex items-center justify-between gap-3 p-3">
                    {item.image_url && (
                      <img
                        src={item.image_url}
                        alt={loc.name}
                        loading="lazy"
                        className="h-16 w-16 shrink-0 rounded-xl object-cover"
                        onError={(e) => {
                          e.currentTarget.style.display = "none";
                        }}
                      />
                    )}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <VegMark veg={item.veg} />
                        <span className="truncate font-semibold text-slate-800">{loc.name}</span>
                      </div>
                      {loc.description && (
                        <p className="mt-0.5 line-clamp-2 text-xs text-slate-500">{loc.description}</p>
                      )}
                      <p className="mt-1 text-sm font-semibold text-slate-700">{rupees(item.price)}</p>
                    </div>
                    <QtyControl qty={cart[item.id] || 0} onChange={(q) => setQty(item.id, q)} />
                  </Card>
                );
              })}
            </div>
          </section>
        ))}

        {count > 0 && (
          <div className="mt-6">
            <label className="text-xs font-medium text-slate-500">Note for the kitchen (optional)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="e.g. Less spicy, no onions"
              className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-sm outline-none focus:border-club-orange"
            />
          </div>
        )}

        <Footer />
      </main>

      {count > 0 && (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-slate-200 bg-white/95 backdrop-blur">
          <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-3">
            <div>
              <div className="text-xs text-slate-500">
                {count} item{count > 1 ? "s" : ""}
              </div>
              <div className="text-lg font-bold text-slate-800">{rupees(totals.total)}</div>
            </div>
            <Button onClick={() => setCheckout(true)} className="px-6">
              Review & Pay →
            </Button>
          </div>
        </div>
      )}

      {checkout && (
        <Checkout
          table={table}
          lines={lines}
          notes={notes}
          totals={totals}
          provider={provider}
          onClose={() => setCheckout(false)}
        />
      )}
    </div>
  );
}

function QtyControl({ qty, onChange }) {
  if (!qty) {
    return (
      <Button variant="outline" className="shrink-0 px-4 py-1.5" onClick={() => onChange(1)}>
        Add
      </Button>
    );
  }
  return (
    <div className="flex shrink-0 items-center gap-2 rounded-xl border border-club-orange/40 bg-club-cream px-1">
      <button onClick={() => onChange(qty - 1)} className="px-2 py-1 text-lg font-bold text-club-orange">
        −
      </button>
      <span className="w-5 text-center text-sm font-bold text-slate-800">{qty}</span>
      <button onClick={() => onChange(qty + 1)} className="px-2 py-1 text-lg font-bold text-club-orange">
        +
      </button>
    </div>
  );
}

function Centered({ children }) {
  return <div className="flex min-h-screen items-center justify-center p-4">{children}</div>;
}
