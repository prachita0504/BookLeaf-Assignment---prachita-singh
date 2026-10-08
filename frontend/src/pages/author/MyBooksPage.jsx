// Author's books with sales and royalty earned / paid / pending, plus production progress.
import { useEffect, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import { getMyBooks } from "../../api/books";
import { useAuth } from "../../context/AuthContext";
import { PRODUCTION_STAGES } from "../../utils/constants";
import { date, inr, num } from "../../utils/format";
import Alert from "../../components/common/Alert";
import { Badge } from "../../components/common/Badge";
import EmptyState from "../../components/common/EmptyState";
import { PageLoader } from "../../components/common/Spinner";
import { PageHeader } from "../../components/layout/Shell";
import ConversationList from "../../components/tickets/ConversationList";

export default function MyBooksPage() {
  const { user } = useAuth();
  const { tickets } = useOutletContext();
  const [books, setBooks] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getMyBooks().then(setBooks).catch(setError);
  }, []);

  if (error) return <Alert tone="error" title="Couldn't load your books">{error.message}</Alert>;
  if (!books) return <PageLoader label="Loading your books..." />;

  const totals = books.reduce(
    (t, b) => ({
      sold: t.sold + b.total_copies_sold,
      earned: t.earned + b.total_royalty_earned,
      paid: t.paid + b.royalty_paid,
      pending: t.pending + b.royalty_pending,
    }),
    { sold: 0, earned: 0, paid: 0, pending: 0 },
  );

  return (
    <>
      <PageHeader
        title={`Hello, ${user.name.split(" ")[0]}`}
        subtitle="Your books, sales and royalties at a glance"
        actions={
          <Link to="/tickets/new" className="rounded-lg bg-brand-700 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-900">
            Get help
          </Link>
        }
      />

      <SupportConversations tickets={tickets} />

      {books.length === 0 ? (
        <EmptyState
          icon="📚"
          title="No books yet"
          action={
            <Link to="/tickets/new" className="text-sm font-medium text-brand-700 hover:underline">
              Have a question about getting started? Ask us →
            </Link>
          }
        >
          Once your manuscript is received, your book will appear here with its production progress, sales and royalties.
        </EmptyState>
      ) : (
        <>
          <section className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Stat label="Copies sold" value={num(totals.sold)} />
            <Stat label="Royalty earned" value={inr(totals.earned)} />
            <Stat label="Royalty paid" value={inr(totals.paid)} tone="text-emerald-700" />
            <Stat label="Royalty pending" value={inr(totals.pending)} tone="text-amber-700" />
          </section>
          <Alert tone="info" className="mb-6">
            Royalties are calculated quarterly and paid within 45 days of each quarter ending. Amounts under ₹1,000 roll over to the next quarter.
          </Alert>
          <section className="grid gap-5 lg:grid-cols-2">
            {books.map((b) => (b.is_published ? <PublishedBook key={b.id} book={b} /> : <InProductionBook key={b.id} book={b} />))}
          </section>
        </>
      )}
    </>
  );
}

const DASHBOARD_CONVERSATIONS = 3;

/** Latest support conversations, so replies from BookLeaf are visible right on the dashboard. */
function SupportConversations({ tickets }) {
  if (!tickets || tickets.length === 0) return null;
  const unread = tickets.filter((t) => t.unread_reply).length;
  // New replies first, then most recently updated (the API already sorts by updated time).
  const shown = [...tickets].sort((a, b) => b.unread_reply - a.unread_reply).slice(0, DASHBOARD_CONVERSATIONS);
  return (
    <section className="mb-8">
      <div className="mb-3 flex items-end justify-between">
        <h2 className="flex items-center gap-2 text-base font-semibold text-slate-900">
          Support conversations
          {unread > 0 && (
            <span className="rounded-full bg-red-500 px-2 py-0.5 text-xs font-semibold text-white">
              {unread} new {unread === 1 ? "reply" : "replies"}
            </span>
          )}
        </h2>
        <Link to="/tickets" className="text-sm font-medium text-brand-700 hover:underline">
          View all ({tickets.length}) →
        </Link>
      </div>
      <ConversationList tickets={shown} />
    </section>
  );
}

function Stat({ label, value, tone = "text-slate-900" }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${tone}`}>{value}</p>
    </div>
  );
}

function BookCard({ book, children, status }) {
  return (
    <article className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{book.title}</h2>
          <p className="text-sm text-slate-500">{book.genre}</p>
        </div>
        {status}
      </div>
      <dl className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-500">
        <div>
          ISBN <span className="font-mono text-slate-700">{book.isbn}</span>
        </div>
        <div>
          Published <span className="text-slate-700">{date(book.publication_date)}</span>
        </div>
        <div>
          MRP <span className="text-slate-700">{inr(book.mrp)}</span>
        </div>
      </dl>
      <div className="mt-4 flex-1">{children}</div>
      <div className="mt-4 border-t border-slate-100 pt-3 text-right">
        <Link to={`/tickets/new?book=${book.id}`} className="text-sm font-medium text-brand-700 hover:underline">
          Ask about this book →
        </Link>
      </div>
    </article>
  );
}

function PublishedBook({ book: b }) {
  const paidPct = b.total_royalty_earned ? Math.round((b.royalty_paid / b.total_royalty_earned) * 100) : 0;
  return (
    <BookCard book={b} status={<Badge className="bg-emerald-50 text-emerald-700 ring-emerald-200">Published & Live</Badge>}>
      <div className="grid grid-cols-4 gap-3 text-sm">
        <Figure label="Sold" value={num(b.total_copies_sold)} />
        <Figure label="Earned" value={inr(b.total_royalty_earned)} />
        <Figure label="Paid" value={inr(b.royalty_paid)} tone="text-emerald-700" />
        <Figure label="Pending" value={inr(b.royalty_pending)} tone={b.royalty_pending ? "text-amber-700" : "text-slate-900"} />
      </div>
      {b.total_royalty_earned > 0 && (
        <div className="mt-3">
          <div className="h-2 overflow-hidden rounded-full bg-amber-100" title={`${paidPct}% of earned royalty paid`}>
            <div className="h-full rounded-full bg-emerald-500" style={{ width: `${paidPct}%` }} />
          </div>
          <p className="mt-1.5 text-xs text-slate-500">
            {paidPct}% paid · Last payout: {b.last_royalty_payout_date ? date(b.last_royalty_payout_date) : "none yet"}
          </p>
        </div>
      )}
      {b.below_payout_threshold && (
        <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">
          Your pending {inr(b.royalty_pending)} is below the ₹1,000 payout minimum and will roll over to the next quarter.
        </p>
      )}
      {b.royalty_pending === 0 && b.total_royalty_earned > 0 && (
        <p className="mt-3 text-xs text-emerald-700">✓ All royalties earned so far have been paid.</p>
      )}
      {b.total_copies_sold === 0 && <p className="mt-3 text-xs text-slate-500">No sales recorded yet.</p>}
      {b.available_on.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {b.available_on.map((p) => (
            <span key={p} className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
              {p}
            </span>
          ))}
        </div>
      )}
    </BookCard>
  );
}

function Figure({ label, value, tone = "text-slate-900" }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`font-semibold ${tone}`}>{value}</p>
    </div>
  );
}

function InProductionBook({ book: b }) {
  return (
    <BookCard book={b} status={<Badge className="bg-sky-50 text-sky-700 ring-sky-200">In production</Badge>}>
      <p className="text-sm text-slate-600">
        Current stage: <span className="font-semibold text-slate-900">{b.production_stage}</span>
      </p>
      <ol className="mt-4 flex items-center gap-1" aria-label="Production progress">
        {PRODUCTION_STAGES.map((stage, i) => (
          <li
            key={stage}
            title={stage}
            className={`h-2 flex-1 rounded-full ${
              i < b.production_stage_index ? "bg-brand-500" : i === b.production_stage_index ? "bg-brand-700 ring-2 ring-brand-100" : "bg-slate-200"
            }`}
          />
        ))}
      </ol>
      <div className="mt-1.5 flex justify-between text-[11px] text-slate-400">
        <span>Manuscript</span>
        <span>Published</span>
      </div>
      <p className="mt-4 text-xs text-slate-500">Sales and royalties will appear here once your book is live.</p>
    </BookCard>
  );
}
