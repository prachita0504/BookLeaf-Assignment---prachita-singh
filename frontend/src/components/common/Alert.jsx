// Inline message box for errors, warnings and info.

const TONES = {
  error: "border-red-200 bg-red-50 text-red-800",
  warning: "border-amber-200 bg-amber-50 text-amber-900",
  info: "border-brand-100 bg-brand-50 text-brand-900",
  success: "border-emerald-200 bg-emerald-50 text-emerald-800",
};

export default function Alert({ tone = "info", title, children, className = "" }) {
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`rounded-lg border px-4 py-3 text-sm ${TONES[tone]} ${className}`}>
      {title && <p className="font-semibold">{title}</p>}
      {children && <div className={title ? "mt-0.5" : ""}>{children}</div>}
    </div>
  );
}
