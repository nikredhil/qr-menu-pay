import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { CLUB } from "../branding";
import { Logo, Footer } from "../components/Brand";
import { Card } from "../components/ui";

// Public home. Diners normally arrive by scanning a table QR (→ /t/:id); this
// page explains the flow and, for convenience while testing, lists the tables
// so you can jump straight into one without a physical QR.
export default function Landing() {
  const [tables, setTables] = useState(null); // null = not loaded; [] = none/blocked

  useEffect(() => {
    // Public lookup isn't available for the whole list, so we probe a few seeded
    // codes. This is just a testing convenience; real diners scan a QR.
    (async () => {
      const guesses = ["TABLE1", "TABLE2", "TABLE3", "TABLE4", "TABLE5"];
      const found = [];
      for (const code of guesses) {
        try {
          found.push(await api.getTable(code));
        } catch {
          /* skip */
        }
      }
      setTables(found);
    })();
  }, []);

  return (
    <div className="min-h-full">
      <main className="mx-auto max-w-md px-4 py-10">
        <div className="flex flex-col items-center text-center">
          <Logo size={72} />
          <h1 className="mt-4 text-2xl font-extrabold tracking-tight text-club-blue">
            {CLUB.product}
          </h1>
          <p className="mt-1 text-sm text-slate-500">{CLUB.tagline}</p>
        </div>

        <Card className="mt-8 p-6">
          <h2 className="text-sm font-bold uppercase tracking-wide text-club-blue">How it works</h2>
          <ol className="mt-3 space-y-3 text-sm text-slate-600">
            <Step n="1" title="Scan the QR on your table" />
            <Step n="2" title="Verify your mobile with a one-time OTP" />
            <Step n="3" title="Browse the menu and build your order" />
            <Step n="4" title="Pay by UPI, card, or cash — and track your order" />
          </ol>
        </Card>

        {tables && tables.length > 0 && (
          <Card className="mt-4 p-5">
            <h2 className="text-xs font-bold uppercase tracking-wide text-slate-400">
              Try a table (testing)
            </h2>
            <div className="mt-3 flex flex-wrap gap-2">
              {tables.map((t) => (
                <Link
                  key={t.id}
                  to={`/t/${t.id}`}
                  className="rounded-xl border border-club-orange/40 bg-club-cream px-3 py-1.5 text-sm font-medium text-club-orange hover:bg-club-orange hover:text-white"
                >
                  {t.label}
                </Link>
              ))}
            </div>
          </Card>
        )}

        <div className="mt-6 text-center">
          <Link to="/admin/login" className="text-xs font-medium text-slate-400 hover:text-slate-600">
            Staff sign-in →
          </Link>
        </div>

        <Footer />
      </main>
    </div>
  );
}

function Step({ n, title }) {
  return (
    <li className="flex items-start gap-3">
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-club-orange text-xs font-bold text-white">
        {n}
      </span>
      <span className="pt-0.5">{title}</span>
    </li>
  );
}
