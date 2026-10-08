// Shared page shell: top bar with logo, navigation, signed-in user and logout.
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

export default function Shell({ nav, badge, children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const onLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-1 px-4 py-2 sm:h-14 sm:flex-nowrap sm:py-0 sm:px-6">
          <div className="flex items-center gap-2">
            <Logo />
            <span className="font-semibold text-brand-900">BookLeaf</span>
            {badge && (
              <span className="rounded-md bg-brand-50 px-1.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-brand-700">
                {badge}
              </span>
            )}
          </div>
          {/* On phones the nav wraps onto its own full-width row below the logo. */}
          <nav className="order-last -mx-2 flex w-full items-center gap-1 overflow-x-auto sm:order-none sm:mx-0 sm:w-auto sm:flex-1">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `inline-flex items-center whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition ${
                    isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`
                }
              >
                {item.label}
                {item.badge && (
                  <span
                    className="ml-1.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1.5 text-[11px] font-semibold text-white"
                    title={`${item.badge} new ${item.badge === 1 ? "reply" : "replies"}`}
                  >
                    {item.badge}
                  </span>
                )}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3 sm:ml-0">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium leading-tight text-slate-800">{user?.name}</p>
              <p className="text-xs leading-tight text-slate-500">{user?.email}</p>
            </div>
            <button
              type="button"
              onClick={onLogout}
              className="rounded-md px-2.5 py-1.5 text-sm text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
            >
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">{children}</main>
    </div>
  );
}

export function Logo({ className = "h-7 w-7" }) {
  return (
    <svg className={className} viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="#1b5276" />
      <path d="M9 22c0-8 5-13 14-13-1 9-6 14-14 13Z" fill="#7fc3ea" />
      <path d="M9 22 18 13" stroke="#1b5276" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
