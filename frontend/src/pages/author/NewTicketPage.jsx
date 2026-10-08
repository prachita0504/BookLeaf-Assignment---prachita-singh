// Raise a support query: book dropdown (or General / Account Level), subject, description, attachment.
import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { getMyBooks } from "../../api/books";
import { createTicket } from "../../api/tickets";
import Alert from "../../components/common/Alert";
import Button from "../../components/common/Button";
import { Input, Select, Textarea } from "../../components/common/Field";
import { PageHeader } from "../../components/layout/Shell";

const MAX_FILE_MB = 5;

export default function NewTicketPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [books, setBooks] = useState([]);
  const [form, setForm] = useState({ book_id: params.get("book") || "", subject: "", description: "" });
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getMyBooks().then(setBooks).catch(() => setBooks([]));
  }, []);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const onFile = (e) => {
    const f = e.target.files?.[0] ?? null;
    setFileError(f && f.size > MAX_FILE_MB * 1024 * 1024 ? `File must be under ${MAX_FILE_MB} MB` : null);
    setFile(f);
  };

  const submit = async (e) => {
    e.preventDefault();
    if (fileError) return;
    setSubmitting(true);
    setError(null);
    try {
      const ticket = await createTicket({
        book_id: form.book_id || null,
        subject: form.subject,
        description: form.description,
        attachment_name: file?.name ?? null, // attachment is UI-only in this version (see README)
      });
      navigate(`/tickets/${ticket.ticket_number}`, { state: { created: true } });
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
    }
  };

  const fieldError = (key) => error?.details?.[key];

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Get help" subtitle="Tell us what's going on. Our support team usually replies within one business day." />
      <form onSubmit={submit} className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm" noValidate>
        {error && !error.details && <Alert tone="error">{error.message}</Alert>}

        <Select id="book" label="Which book is this about?" value={form.book_id} onChange={set("book_id")} error={fieldError("book_id")}>
          <option value="">General / Account level</option>
          {books.map((b) => (
            <option key={b.id} value={b.id}>
              {b.title} {b.is_published ? "" : `(${b.production_stage})`}
            </option>
          ))}
        </Select>

        <Input
          id="subject"
          label="Subject"
          placeholder="e.g. Royalty for last quarter not received"
          maxLength={150}
          value={form.subject}
          onChange={set("subject")}
          error={fieldError("subject")}
        />

        <Textarea
          id="description"
          label="Describe the issue"
          rows={7}
          maxLength={5000}
          placeholder="Include any details that will help us, such as dates, amounts, platform names or order numbers."
          value={form.description}
          onChange={set("description")}
          error={fieldError("description")}
          hint={`${form.description.length}/5000 characters · at least 20`}
        />

        <div>
          <p className="mb-1 text-sm font-medium text-slate-700">Attachment (optional)</p>
          <label className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500 hover:border-brand-500 hover:text-brand-700">
            <input type="file" className="sr-only" accept="image/*,.pdf" onChange={onFile} />
            📎 {file ? <span className="font-medium text-slate-700">{file.name}</span> : "Add a photo or PDF (e.g. a defective page)"}
          </label>
          {fileError && <p className="mt-1 text-xs text-red-600">{fileError}</p>}
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <Link to="/tickets" className="text-sm text-slate-600 hover:underline">
            Cancel
          </Link>
          <Button type="submit" loading={submitting}>
            Submit ticket
          </Button>
        </div>
      </form>
    </div>
  );
}
