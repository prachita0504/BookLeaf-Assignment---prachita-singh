// Two-column layout shared by the login and sign-up pages.
import { Logo } from "../../components/layout/Shell";

export default function AuthLayout({ title, subtitle, children }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <aside className="relative hidden overflow-hidden bg-brand-900 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="flex items-center gap-2">
          <Logo className="h-9 w-9" />
          <span className="text-lg font-semibold">BookLeaf Publishing</span>
        </div>
        <div>
          <h2 className="text-3xl font-semibold leading-tight">
            Your books, your royalties,
            <br />
            your support team, in one place.
          </h2>
          <ul className="mt-8 space-y-3 text-brand-100">
            <li>📚 Track sales and royalties for every title</li>
            <li>💬 Raise a query and follow every reply live</li>
            <li>⚡ Faster answers from the BookLeaf support team</li>
          </ul>
        </div>
        <p className="text-sm text-brand-100/70">India · US · 22,000+ titles published</p>
        <div className="pointer-events-none absolute -right-24 -bottom-24 h-80 w-80 rounded-full bg-brand-500/20" />
      </aside>

      <main className="flex items-center justify-center px-4 py-12 sm:px-8">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-2 lg:hidden">
            <Logo />
            <span className="font-semibold text-brand-900">BookLeaf</span>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
          <div className="mt-8">{children}</div>
        </div>
      </main>
    </div>
  );
}
