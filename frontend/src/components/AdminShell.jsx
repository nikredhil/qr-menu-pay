import { Link, useLocation, useNavigate } from "react-router-dom";
import { clearAdmin } from "../auth";
import { Logo } from "./Brand";

const TABS = [
  { to: "/admin/orders", label: "Orders" },
  { to: "/admin/menu", label: "Menu" },
  { to: "/admin/tables", label: "Tables & QR" },
];

export default function AdminShell({ children }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();

  function logout() {
    clearAdmin();
    navigate("/admin/login", { replace: true });
  }

  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-3">
          <Logo size={36} />
          <div className="flex-1">
            <div className="text-sm font-extrabold text-club-blue">HSR Club Dine</div>
            <div className="text-[11px] text-slate-400">Staff dashboard</div>
          </div>
          <button onClick={logout} className="text-sm font-medium text-slate-500 hover:text-red-600">
            Sign out
          </button>
        </div>
        <nav className="mx-auto flex max-w-5xl gap-1 px-2">
          {TABS.map((t) => {
            const active = pathname === t.to;
            return (
              <Link
                key={t.to}
                to={t.to}
                className={`border-b-2 px-4 py-2.5 text-sm font-semibold ${
                  active
                    ? "border-club-orange text-club-orange"
                    : "border-transparent text-slate-500 hover:text-slate-700"
                }`}
              >
                {t.label}
              </Link>
            );
          })}
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-5">{children}</main>
    </div>
  );
}
