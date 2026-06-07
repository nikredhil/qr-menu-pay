import { CLUB } from "../branding";

// The official HSR Club emblem (served from /public). Preserves the logo's
// 137×93 aspect ratio; `size` sets the rendered height.
export function Logo({ size = 40 }) {
  return (
    <img
      src="/hsr-club-logo.png"
      alt="HSR Club"
      style={{ height: size, width: "auto" }}
      className="object-contain"
    />
  );
}

export function Header({ right = null, subtitle }) {
  return (
    <header className="sticky top-0 z-20 border-b border-club-orange/20 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-3xl items-center gap-3 px-4 py-3">
        <Logo size={40} />
        <div className="min-w-0 flex-1">
          <div className="truncate text-base font-extrabold tracking-tight text-club-blue">
            {CLUB.product}
          </div>
          {subtitle && <div className="truncate text-xs text-slate-500">{subtitle}</div>}
        </div>
        {right}
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="mt-10 border-t border-slate-200 px-4 py-6 text-center text-xs text-slate-400">
      <div className="font-semibold text-slate-500">{CLUB.name}</div>
      <div className="mt-1">{CLUB.address}</div>
      <div className="mt-1">
        {CLUB.phones.join(" · ")} · {CLUB.email}
      </div>
    </footer>
  );
}
