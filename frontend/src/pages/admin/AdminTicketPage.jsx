// Ticket workspace: AI draft editor, replies, internal notes, status/category/priority overrides, assignment.
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { addMessage, getDraft, getTicket, listAdmins, updateTicket } from "../../api/admin";
import { useAuth } from "../../context/AuthContext";
import usePolling from "../../hooks/usePolling";
import { CATEGORY, CLASSIFIED_BY, POLL_MS, PRIORITY, STATUS } from "../../utils/constants";
import { date, dateTime, inr, num, timeAgo } from "../../utils/format";
import Alert from "../../components/common/Alert";
import { CategoryBadge, PriorityBadge, StatusBadge } from "../../components/common/Badge";
import Button from "../../components/common/Button";
import { Select } from "../../components/common/Field";
import Spinner, { PageLoader } from "../../components/common/Spinner";
import MessageThread from "../../components/tickets/MessageThread";

export default function AdminTicketPage() {
  const { number } = useParams();
  const { data: ticket, setData, error, loading } = usePolling(() => getTicket(number), POLL_MS.adminTicket, [number]);
  const [admins, setAdmins] = useState([]);
  const [actionError, setActionError] = useState(null);

  useEffect(() => {
    listAdmins().then(setAdmins).catch(() => {});
  }, []);

  const update = async (changes) => {
    setActionError(null);
    try {
      setData(await updateTicket(number, changes));
    } catch (err) {
      setActionError(err);
    }
  };

  if (loading && !ticket) return <PageLoader />;
  if (error && !ticket) {
    return (
      <Alert tone="error" title={error.status === 404 ? "Ticket not found" : "Couldn't load ticket"}>
        {error.message} <Link to="/admin" className="underline">Back to queue</Link>
      </Alert>
    );
  }

  return (
    <>
      <Link to="/admin" className="text-sm text-slate-500 hover:text-slate-800">
        ← Ticket queue
      </Link>
      <div className="mt-3 grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium text-slate-400">#{ticket.ticket_number}</span>
              <PriorityBadge value={ticket.priority} />
              <CategoryBadge value={ticket.category} />
              <StatusBadge value={ticket.status} />
              {ticket.sla_breached && <span className="rounded bg-red-100 px-1.5 py-0.5 text-xs font-semibold text-red-700">First reply overdue</span>}
            </div>
            <h1 className="mt-2 text-xl font-semibold text-slate-900">{ticket.subject}</h1>
            <p className="mt-1 text-sm text-slate-500">
              {ticket.author.name} · {ticket.book ? ticket.book.title : "General / Account level"} · opened {timeAgo(ticket.created_at)} ({dateTime(ticket.created_at)})
            </p>
            {ticket.attachment_name && <p className="mt-2 text-xs text-slate-500">📎 {ticket.attachment_name} (file name only)</p>}
          </header>

          <MessageThread ticket={ticket} authorName={ticket.author.name} messages={ticket.messages} viewerRole="ADMIN" />

          <Composer ticket={ticket} onSent={setData} />
        </div>

        <aside className="space-y-4">
          {actionError && <Alert tone="error">{actionError.message}</Alert>}
          <TriagePanel ticket={ticket} admins={admins} onUpdate={update} />
          <AuthorPanel ticket={ticket} />
        </aside>
      </div>
    </>
  );
}

// ------------------------------------------------------------------ reply / note composer with AI draft

function Composer({ ticket, onSent }) {
  const [mode, setMode] = useState("reply"); // "reply" | "note"
  const [reply, setReply] = useState("");
  const [note, setNote] = useState("");
  const [draft, setDraft] = useState({ state: "idle" }); // idle | loading | ready | unavailable | none
  const [fromDraft, setFromDraft] = useState(false); // reply text started from the AI draft
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const replyRef = useRef(reply);
  replyRef.current = reply;

  const loadDraft = useCallback(
    async (regenerate = false) => {
      setDraft({ state: "loading" });
      try {
        const d = await getDraft(ticket.ticket_number, regenerate);
        setDraft({ state: "ready", ...d });
        // Never overwrite something the admin already typed, unless they asked to regenerate.
        if (regenerate || !replyRef.current.trim()) {
          setReply(d.text);
          setFromDraft(true);
        }
      } catch (err) {
        setDraft({ state: err.status === 409 ? "none" : "unavailable", message: err.message });
      }
    },
    [ticket.ticket_number],
  );

  // Draft automatically when the ticket is opened, and again when the author sends something new.
  const replyCount = ticket.messages.filter((m) => m.kind === "REPLY").length;
  useEffect(() => {
    if (ticket.awaiting_reply) loadDraft(false);
    else setDraft({ state: "none" });
  }, [ticket.ticket_number, ticket.awaiting_reply, replyCount, loadDraft]);

  const send = async (setStatus) => {
    const body = mode === "reply" ? reply : note;
    setSending(true);
    setError(null);
    try {
      const updated = await addMessage(ticket.ticket_number, {
        body,
        internal: mode === "note",
        ai_assisted: mode === "reply" && fromDraft,
        ...(setStatus ? { set_status: setStatus } : {}),
      });
      onSent(updated);
      if (mode === "reply") {
        setReply("");
        setFromDraft(false);
      } else {
        setNote("");
      }
    } catch (err) {
      setError(err);
    } finally {
      setSending(false);
    }
  };

  const body = mode === "reply" ? reply : note;
  const closed = ticket.status === "CLOSED";

  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex border-b border-slate-200 text-sm">
        {[
          ["reply", "Reply to author"],
          ["note", "🔒 Internal note"],
        ].map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setMode(key)}
            className={`px-4 py-2.5 font-medium ${mode === key ? "border-b-2 border-brand-700 text-brand-700" : "text-slate-500 hover:text-slate-800"}`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="space-y-3 p-4">
        {mode === "reply" && <DraftStatus draft={draft} onRegenerate={() => loadDraft(true)} />}
        {mode === "note" && <p className="text-xs text-amber-800">Internal notes are only visible to the BookLeaf team.</p>}
        {error && <Alert tone="error">{error.message}</Alert>}
        {closed && mode === "reply" && <Alert tone="warning">This ticket is closed. Re-open it to reply.</Alert>}

        <textarea
          rows={mode === "reply" ? 11 : 4}
          value={body}
          disabled={draft.state === "loading" && mode === "reply" && !reply}
          onChange={(e) => (mode === "reply" ? setReply(e.target.value) : setNote(e.target.value))}
          placeholder={mode === "reply" ? "Write your reply to the author…" : "Add context for your teammates…"}
          className={`block w-full rounded-lg border-0 px-3 py-2 text-sm leading-relaxed ring-1 ring-inset focus:ring-2 focus:ring-brand-500 ${
            mode === "note" ? "bg-amber-50/50 ring-amber-200" : "ring-slate-300"
          }`}
        />

        <div className="flex flex-wrap items-center justify-end gap-2">
          {mode === "reply" ? (
            <>
              <Button variant="secondary" disabled={!reply.trim() || closed} loading={sending} onClick={() => send("RESOLVED")}>
                Send & mark resolved
              </Button>
              <Button disabled={!reply.trim() || closed} loading={sending} onClick={() => send()}>
                Send reply
              </Button>
            </>
          ) : (
            <Button variant="secondary" disabled={!note.trim()} loading={sending} onClick={() => send()}>
              Add note
            </Button>
          )}
        </div>
      </div>
    </section>
  );
}

function DraftStatus({ draft, onRegenerate }) {
  if (draft.state === "loading") {
    return (
      <div className="flex items-center gap-2 rounded-lg bg-violet-50 px-3 py-2 text-sm text-violet-800">
        <Spinner className="h-4 w-4" /> Drafting a reply with BookLeaf's knowledge base…
      </div>
    );
  }
  if (draft.state === "ready") {
    return (
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-violet-50 px-3 py-2 text-sm text-violet-800">
        <span>
          ✨ AI draft {draft.cached ? "(saved)" : "ready"}. Review and edit before sending.
        </span>
        <Button variant="ghost" size="sm" onClick={onRegenerate}>
          ↻ Regenerate
        </Button>
      </div>
    );
  }
  if (draft.state === "unavailable") {
    return (
      <Alert tone="warning" title="AI draft unavailable">
        {draft.message}. Please write the reply manually.{" "}
        <button type="button" className="font-medium underline" onClick={onRegenerate}>
          Try again
        </button>
      </Alert>
    );
  }
  if (draft.state === "none") {
    return (
      <div className="flex items-center justify-between gap-2 text-xs text-slate-500">
        <span>The latest message is already from BookLeaf.</span>
        <Button variant="ghost" size="sm" onClick={onRegenerate}>
          ✨ Draft a follow-up
        </Button>
      </div>
    );
  }
  return null;
}

// ------------------------------------------------------------------ side panels

function TriagePanel({ ticket, admins, onUpdate }) {
  const { user } = useAuth();
  const ai = ticket.ai;
  const aiDisagrees = ai && (ai.category !== ticket.category || ai.priority !== ticket.priority);

  return (
    <Panel title="Ticket">
      <div className="space-y-3">
        <Select id="status" label="Status" value={ticket.status} onChange={(e) => onUpdate({ status: e.target.value })}>
          {Object.entries(STATUS).map(([k, v]) => (
            <option key={k} value={k}>
              {v.label}
            </option>
          ))}
        </Select>
        <Select id="priority" label="Priority" value={ticket.priority} onChange={(e) => onUpdate({ priority: e.target.value })}>
          {Object.entries(PRIORITY).map(([k, v]) => (
            <option key={k} value={k}>
              {v.label}
            </option>
          ))}
        </Select>
        <Select id="category" label="Category" value={ticket.category} onChange={(e) => onUpdate({ category: e.target.value })}>
          {Object.entries(CATEGORY).map(([k, v]) => (
            <option key={k} value={k}>
              {v.label}
            </option>
          ))}
        </Select>

        <div className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
          <p>
            Classified by <span className="font-semibold">{CLASSIFIED_BY[ticket.classified_by]}</span>
          </p>
          {ai ? (
            <p className="mt-1">
              ✨ AI suggested <span className="font-medium">{CATEGORY[ai.category]?.label}</span> ·{" "}
              <span className="font-medium">{PRIORITY[ai.priority]?.label}</span>
              {ai.reason && <span className="block italic text-slate-500">“{ai.reason}”</span>}
              {aiDisagrees && <span className="mt-1 block text-amber-700">Overridden by the team.</span>}
            </p>
          ) : (
            <p className="mt-1 text-slate-500">AI triage not available for this ticket; keyword rules were used.</p>
          )}
        </div>

        <div>
          <p className="mb-1 text-sm font-medium text-slate-700">Assignee</p>
          <div className="flex gap-2">
            <select
              aria-label="Assignee"
              value={ticket.assigned_to?.id ?? ""}
              onChange={(e) => onUpdate({ assigned_to_id: e.target.value || null })}
              className="block w-full rounded-lg border-0 px-3 py-2 text-sm ring-1 ring-inset ring-slate-300"
            >
              <option value="">Unassigned</option>
              {admins.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
            {ticket.assigned_to?.id !== user.id && (
              <Button variant="secondary" size="sm" onClick={() => onUpdate({ assigned_to_id: user.id })}>
                Assign to me
              </Button>
            )}
          </div>
        </div>
        {ticket.first_response_at && <p className="text-xs text-slate-500">First response {dateTime(ticket.first_response_at)}</p>}
      </div>
    </Panel>
  );
}

function AuthorPanel({ ticket }) {
  const a = ticket.author;
  const book = ticket.book_details;
  const others = ticket.author_books.filter((b) => b.id !== book?.id);
  return (
    <>
      <Panel title="Author">
        <p className="font-medium text-slate-900">{a.name}</p>
        <p className="text-sm text-slate-600">{a.email}</p>
        <p className="mt-1 text-xs text-slate-500">
          {[a.author_id, a.city, a.phone, a.joined_date && `joined ${date(a.joined_date)}`].filter(Boolean).join(" · ")}
        </p>
      </Panel>
      {book && (
        <Panel title="Book in this ticket">
          <BookFacts book={book} />
        </Panel>
      )}
      {others.length > 0 && (
        <Panel title={book ? "Other books" : "Author's books"}>
          <ul className="space-y-3">
            {others.map((b) => (
              <li key={b.id} className="border-b border-slate-100 pb-3 last:border-0 last:pb-0">
                <BookFacts book={b} compact />
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </>
  );
}

function BookFacts({ book: b, compact }) {
  return (
    <div className="text-sm">
      <p className="font-medium text-slate-900">{b.title}</p>
      <p className="text-xs text-slate-500">
        <span className="font-mono">{b.isbn}</span> · {b.status}
      </p>
      {b.is_published ? (
        <dl className={`mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs ${compact ? "" : "sm:grid-cols-2"}`}>
          <Fact label="Sold" value={num(b.total_copies_sold)} />
          <Fact label="MRP" value={inr(b.mrp)} />
          <Fact label="Earned" value={inr(b.total_royalty_earned)} />
          <Fact label="Paid" value={inr(b.royalty_paid)} />
          <Fact label="Pending" value={inr(b.royalty_pending)} highlight={b.royalty_pending > 0} />
          <Fact label="Last payout" value={b.last_royalty_payout_date ? date(b.last_royalty_payout_date) : "Never"} />
          {!compact && <Fact label="Printed by" value={b.print_partner ?? "—"} />}
          {!compact && <Fact label="Published" value={date(b.publication_date)} />}
        </dl>
      ) : (
        <p className="mt-1 text-xs text-sky-700">In production · stage: {b.production_stage}</p>
      )}
      {b.below_payout_threshold && <p className="mt-1 text-xs text-amber-700">Pending is below the ₹1,000 payout threshold.</p>}
      {!compact && b.available_on.length > 0 && <p className="mt-2 text-xs text-slate-500">On: {b.available_on.join(", ")}</p>}
    </div>
  );
}

function Fact({ label, value, highlight }) {
  return (
    <div>
      <dt className="text-slate-500">{label}</dt>
      <dd className={`font-medium ${highlight ? "text-amber-700" : "text-slate-800"}`}>{value}</dd>
    </div>
  );
}

function Panel({ title, children }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</h2>
      {children}
    </section>
  );
}
