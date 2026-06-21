import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, rupees, STATUS_META, PAY_META } from "../api";
import { Header, Footer } from "../components/Brand";
import { Badge, Button, Card, Spinner, VegMark } from "../components/ui";

// Live order receipt + kitchen status. Polls every 8s so diners see the
// kitchen advance "placed → preparing → served" without refreshing.
export default function OrderStatus() {
  const { orderId } = useParams();
  const [order, setOrder] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const o = await api.getOrder(orderId);
        if (active) setOrder(o);
      } catch (err) {
        if (active) setError(err.message.replace(/^\d+:\s*/, ""));
      }
    }
    load();
    const id = setInterval(load, 8000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [orderId]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <Card className="max-w-sm p-6 text-center">
          <p className="font-semibold text-slate-700">Couldn't load this order</p>
          <p className="mt-1 text-sm text-slate-500">{error}</p>
          <Link to="/" className="mt-4 inline-block text-sm font-medium text-club-orange">
            Home
          </Link>
        </Card>
      </div>
    );
  }
  if (!order) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner className="text-club-orange" />
      </div>
    );
  }

  const paid = order.payment_status === "paid";
  const isCash = order.payment_method === "cash";
  const sm = STATUS_META[order.status];
  const pm = PAY_META[order.payment_status];

  return (
    <div className="min-h-full">
      <Header subtitle={`Order ${order.code}`} />
      <main className="mx-auto max-w-md px-4 py-5">
        <Card className="overflow-hidden">
          <div className={`px-5 py-6 text-center text-white ${paid ? "bg-club-green" : "bg-club-orange"}`}>
            <div className="text-4xl">{paid ? "✅" : isCash ? "🪙" : "⏳"}</div>
            <h1 className="mt-2 text-xl font-bold">
              {paid ? "Payment received" : isCash ? "Pay at the counter" : "Awaiting payment"}
            </h1>
            <p className="mt-1 text-sm opacity-90">
              Order <span className="font-mono font-bold">{order.code}</span> · {order.table_label}
            </p>
          </div>

          <div className="space-y-4 p-5">
            <div className="flex items-center justify-between">
              <Badge className={sm.className}>Kitchen: {sm.label}</Badge>
              <Badge className={pm.className}>
                {isCash && !paid ? "Cash — pay at counter" : pm.label}
              </Badge>
            </div>

            <StatusTrack status={order.status} />

            <ul className="divide-y divide-slate-100">
              {order.lines.map((l) => (
                <li key={l.menu_item_id} className="flex items-center justify-between py-2 text-sm">
                  <span className="flex items-center gap-2">
                    <VegMark veg={l.veg} />
                    <span className="text-slate-700">
                      {l.name} <span className="text-slate-400">× {l.quantity}</span>
                    </span>
                  </span>
                  <span className="font-medium text-slate-700">{rupees(l.unit_price * l.quantity)}</span>
                </li>
              ))}
            </ul>

            {order.notes && (
              <p className="rounded-lg bg-club-cream px-3 py-2 text-xs text-slate-600">
                Note: {order.notes}
              </p>
            )}

            <div className="space-y-1 border-t border-slate-100 pt-3 text-sm">
              <Row label="Subtotal" value={rupees(order.subtotal)} />
              <Row label="GST (5%)" value={rupees(order.tax)} />
              <Row label="Total" value={rupees(order.total)} bold />
            </div>

            {isCash && !paid && (
              <p className="rounded-lg bg-amber-50 px-3 py-2 text-center text-xs text-amber-700">
                Please pay {rupees(order.total)} in cash at the counter. Staff will mark it paid.
              </p>
            )}
          </div>
        </Card>

        {paid && <FeedbackCard orderId={order.id} />}

        <Link
          to={`/t/${order.table_id}`}
          className="mt-4 block text-center text-sm font-medium text-club-orange"
        >
          ← Back to the menu
        </Link>
        <Footer />
      </main>
    </div>
  );
}

function StatusTrack({ status }) {
  const steps = ["placed", "preparing", "served"];
  if (status === "cancelled") {
    return <p className="text-center text-sm font-medium text-red-600">This order was cancelled.</p>;
  }
  const activeIdx = steps.indexOf(status);
  return (
    <div className="flex items-center">
      {steps.map((s, i) => (
        <div key={s} className="flex flex-1 items-center last:flex-none">
          <div
            className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
              i <= activeIdx ? "bg-club-green text-white" : "bg-slate-200 text-slate-400"
            }`}
          >
            {i + 1}
          </div>
          {i < steps.length - 1 && (
            <div className={`h-1 flex-1 ${i < activeIdx ? "bg-club-green" : "bg-slate-200"}`} />
          )}
        </div>
      ))}
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

// Post-payment feedback. Shows a star form once the order is paid; if the diner
// already rated this order it shows a thank-you instead.
function FeedbackCard({ orderId }) {
  const [existing, setExisting] = useState(undefined); // undefined = loading
  const [rating, setRating] = useState(0);
  const [food, setFood] = useState(0);
  const [service, setService] = useState(0);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api
      .myFeedback(orderId)
      .then((fb) => active && setExisting(fb))
      .catch(() => active && setExisting(null));
    return () => {
      active = false;
    };
  }, [orderId]);

  async function submit() {
    if (!rating) {
      setError("Please tap a star rating first.");
      return;
    }
    setError("");
    setBusy(true);
    try {
      const fb = await api.submitFeedback({
        order_id: orderId,
        rating,
        food_rating: food || null,
        service_rating: service || null,
        comment,
      });
      setExisting(fb);
    } catch (err) {
      setError(err.message.replace(/^\d+:\s*/, ""));
    } finally {
      setBusy(false);
    }
  }

  if (existing === undefined) return null;
  if (existing) {
    return (
      <Card className="mt-4 p-5 text-center">
        <p className="text-2xl">🙏</p>
        <p className="mt-1 font-semibold text-slate-700">Thanks for your feedback!</p>
        <p className="mt-1 text-club-orange">{"★".repeat(existing.rating)}</p>
      </Card>
    );
  }

  return (
    <Card className="mt-4 p-5">
      <h2 className="text-center font-bold text-slate-800">How was your experience?</h2>
      <div className="mt-3 flex justify-center">
        <StarPicker value={rating} onChange={setRating} size="text-3xl" />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 text-center text-sm">
        <div>
          <div className="mb-1 text-xs text-slate-500">Food</div>
          <StarPicker value={food} onChange={setFood} />
        </div>
        <div>
          <div className="mb-1 text-xs text-slate-500">Service</div>
          <StarPicker value={service} onChange={setService} />
        </div>
      </div>
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        rows={2}
        placeholder="Anything you'd like to tell us? (optional)"
        className="mt-4 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-sm outline-none focus:border-club-orange"
      />
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      <Button className="mt-3 w-full" onClick={submit} disabled={busy}>
        {busy ? <Spinner /> : "Submit feedback"}
      </Button>
    </Card>
  );
}

function StarPicker({ value, onChange, size = "text-xl" }) {
  return (
    <div className={`inline-flex ${size}`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          className={n <= value ? "text-club-orange" : "text-slate-300"}
          aria-label={`${n} star${n > 1 ? "s" : ""}`}
        >
          ★
        </button>
      ))}
    </div>
  );
}
