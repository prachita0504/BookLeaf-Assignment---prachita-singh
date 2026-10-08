// Labelled form controls that show the backend's per-field validation messages.

const CONTROL =
  "block w-full rounded-lg border-0 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm ring-1 ring-inset placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-brand-500";

function Wrapper({ label, hint, error, htmlFor, children }) {
  return (
    <div>
      {label && (
        <label htmlFor={htmlFor} className="mb-1 block text-sm font-medium text-slate-700">
          {label}
        </label>
      )}
      {children}
      {error ? <p className="mt-1 text-xs text-red-600">{error}</p> : hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

const ring = (error) => (error ? "ring-red-400" : "ring-slate-300");

export function Input({ label, hint, error, id, ...props }) {
  return (
    <Wrapper label={label} hint={hint} error={error} htmlFor={id}>
      <input id={id} className={`${CONTROL} ${ring(error)}`} {...props} />
    </Wrapper>
  );
}

export function Textarea({ label, hint, error, id, ...props }) {
  return (
    <Wrapper label={label} hint={hint} error={error} htmlFor={id}>
      <textarea id={id} className={`${CONTROL} ${ring(error)}`} {...props} />
    </Wrapper>
  );
}

export function Select({ label, hint, error, id, children, className = "", ...props }) {
  return (
    <Wrapper label={label} hint={hint} error={error} htmlFor={id}>
      <select id={id} className={`${CONTROL} ${ring(error)} pr-8 ${className}`} {...props}>
        {children}
      </select>
    </Wrapper>
  );
}
