// Small, dependency-free UI primitives shared across pages.

export function Button({ variant = "primary", className = "", ...props }) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed";
  const variants = {
    primary: "bg-club-orange text-white hover:bg-club-orange-dark shadow-sm",
    green: "bg-club-green text-white hover:brightness-95 shadow-sm",
    outline: "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50",
    ghost: "text-slate-600 hover:bg-slate-100",
    danger: "bg-red-600 text-white hover:bg-red-700",
  };
  return <button className={`${base} ${variants[variant]} ${className}`} {...props} />;
}

export function Card({ className = "", children }) {
  return (
    <div className={`rounded-2xl bg-white shadow-sm ring-1 ring-slate-200 ${className}`}>
      {children}
    </div>
  );
}

export function Badge({ className = "", children }) {
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${className}`}>
      {children}
    </span>
  );
}

export function Input({ className = "", ...props }) {
  return (
    <input
      className={`w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-club-orange focus:ring-2 focus:ring-club-orange/30 ${className}`}
      {...props}
    />
  );
}

export function Spinner({ className = "" }) {
  return (
    <span
      className={`inline-block h-5 w-5 animate-spin rounded-full border-2 border-current border-t-transparent ${className}`}
    />
  );
}

// A green/red diamond marking veg / non-veg, like Indian menus use.
export function VegMark({ veg }) {
  const color = veg ? "border-green-600 text-green-600" : "border-red-600 text-red-600";
  return (
    <span
      className={`inline-flex h-4 w-4 items-center justify-center rounded-sm border ${color}`}
      title={veg ? "Vegetarian" : "Non-vegetarian"}
    >
      <span className={`h-2 w-2 rounded-full ${veg ? "bg-green-600" : "bg-red-600"}`} />
    </span>
  );
}

export function Toast({ message, tone = "info", onClose }) {
  if (!message) return null;
  const tones = {
    info: "bg-slate-800",
    error: "bg-red-600",
    success: "bg-club-green",
  };
  return (
    <div className="fixed inset-x-0 bottom-4 z-50 flex justify-center px-4">
      <div
        className={`flex max-w-md items-center gap-3 rounded-xl px-4 py-3 text-sm text-white shadow-lg ${tones[tone]}`}
        onClick={onClose}
      >
        {message}
      </div>
    </div>
  );
}
