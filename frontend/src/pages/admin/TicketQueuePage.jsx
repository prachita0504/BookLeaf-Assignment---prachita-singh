// All tickets, filterable by status/category/priority/assignee/date. Urgent and oldest first.
// Filters live in the URL, so a filtered view can be bookmarked or shared with a teammate.
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getStats, listQueue } from "../../api/admin";
import usePolling from "../../hooks/usePolling";
import { CATEGORY, CLASSIFIED_BY, POLL_MS, PRIORITY, STATUS } from "../../utils/constants";
import { dateTime, timeAgo } from "../../utils/format";
import Alert from "../../components/common/Alert";
import { CategoryBadge, PriorityBadge, StatusBadge } from "../../components/common/Badge";
import EmptyState from "../../components/common/EmptyState";
import { Input, Select } from "../../components/common/Field";
import { PageLoader } from "../../components/common/Spinner";
import { PageHeader } from "../../components/layout/Shell";

const DEFAULT_STATUS = "UNRESOLVED";
const FILTER_KEYS = ["status", "category", "priority", "assigned", "from", "to", "q"];

export default function TicketQueuePage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const filters = Object.fromEntries(FILTER_KEYS.map((k) => [k, params.get(k) ?? (k === "status" ? DEFAULT_STATUS : "")]));
  const [search, setSearch] = useState(filters.q);

  // Debounce the search box so we don't query on every keystroke.
  useEffect(() => {
    const id = setTimeout(() => setFilter("q", search.trim()), 350);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  // Functional update: always applies to the latest URL, even from the delayed search callback.
  const setFilter = (key, value) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (value) next.set(key, value);
        else next.delete(key);
        return next;
      },
      { replace: true },
    );

  const apiFilters = {
    ...filters,
    status: filters.status === "ALL" ? "" : filters.status,
    to: filters.to ? `${filters.to}T23:59:59` : "", // include the whole "to" day
  };
  const filterKey = JSON.stringify(apiFilters);
  const { data: tickets, error, loading } = usePolling(() => listQueue(apiFilters), POLL_MS.adminQueue, [filterKey]);
  const { data: stats } = usePolling(getStats, POLL_MS.adminQueue);

  const hasFilters = FILTER_KEYS.some((k) => (k === "status" ? filters.status !== DEFAULT_STATUS : filters[k]));

  return (
    <>
      <PageHeader title="Ticket queue" subtitle="Most urgent and longest-waiting tickets first · refreshes automatically" />

      {stats && <StatsBar stats={stats} onPick={(k, v) => setFilter(k, v)} />}

      <section className="mb-4 grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-8">
        <div className="lg:col-span-2">
          <Input id="q" placeholder="Search subject, author or #number" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <Select id="status" value={filters.status} onChange={(e) => setFilter("status", e.target.value)} aria-label="Status">
          <option value="UNRESOLVED">Unresolved</option>
          <option value="ALL">All statuses</option>
          {Object.entries(STATUS).map(([k, v]) => (
            <option key={k} value={k}>
              {v.label}
            </option>
          ))}
        </Select>
        <Select id="priority" value={filters.priority} onChange={(e) => setFilter("priority", e.target.value)} aria-label="Priority">
          <option value="">All priorities</option>
          {Object.entries(PRIORITY).map(([k, v]) => (
            <option key={k} value={k}>
              {v.label}
            </option>
          ))}
        </Select>
        <Select id="category" value={filters.category} onChange={(e) => setFilter("category", e.target.value)} aria-label="Category">
          <option value="">All categories</option>
          {Object.entries(CATEGORY).map(([k, v]) => (
            <option key={k} value={k}>
              {v.label}
            </option>
          ))}
        </Select>
        <Select id="assigned" value={filters.assigned} onChange={(e) => setFilter("assigned", e.target.value)} aria-label="Assignee">
          <option value="">Anyone</option>
          <option value="me">Assigned to me</option>
          <option value="unassigned">Unassigned</option>
        </Select>
        <div className="flex items-center gap-2 lg:col-span-2" title="Created between">
          <span className="text-xs text-slate-500">From</span>
          <input
            type="date"
            aria-label="Created from"
            value={filters.from}
            onChange={(e) => setFilter("from", e.target.value)}
            className="w-full min-w-0 rounded-lg border-0 px-2 py-2 text-xs ring-1 ring-slate-300"
          />
          <span className="text-xs text-slate-500">to</span>
          <input
            type="date"
            aria-label="Created to"
            value={filters.to}
            onChange={(e) => setFilter("to", e.target.value)}
            className="w-full min-w-0 rounded-lg border-0 px-2 py-2 text-xs ring-1 ring-slate-300"
          />
        </div>
        {hasFilters && (
          <button
            type="button"
            className="text-left text-xs font-medium text-brand-700 hover:underline lg:col-span-8"
            onClick={() => {
              setSearch("");
              setParams(new URLSearchParams(), { replace: true });
            }}
          >
            Clear filters
          </button>
        )}
      </section>

      {error && <Alert tone="error" className="mb-4">{error.message}</Alert>}
      {loading && !tickets && <PageLoader label="Loading tickets..." />}
      {tickets?.length === 0 && (
        <EmptyState icon="🎉" title={hasFilters ? "No tickets match these filters" : "Queue is clear"}>
          {hasFilters ? "Try widening the filters." : "No unresolved tickets right now."}
        </EmptyState>
      )}
      {tickets?.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-100 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Ticket</th>
                <th className="px-4 py-3">Priority</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Assignee</th>
                <th className="px-4 py-3">Waiting</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {tickets.map((t) => (
                <tr
                  key={t.ticket_number}
                  onClick={() => navigate(`/admin/tickets/${t.ticket_number}`)}
                  className={`cursor-pointer hover:bg-slate-50 ${t.priority === "CRITICAL" && t.status !== "RESOLVED" && t.status !== "CLOSED" ? "bg-red-50/40" : ""}`}
                >
                  <td className="max-w-md px-4 py-3">
                    <div className="flex items-center gap-2">
                      {t.awaiting_reply && <span className="h-2 w-2 shrink-0 rounded-full bg-brand-500" title="Awaiting our reply" />}
                      <span className="text-xs text-slate-400">#{t.ticket_number}</span>
                      <span className="truncate font-medium text-slate-900">{t.subject}</span>
                    </div>
                    <p className="mt-0.5 truncate pl-4 text-xs text-slate-500">
                      {t.author_name} · {t.book ? t.book.title : "Account level"}
                    </p>
                  </td>
                  <td className="px-4 py-3">
                    <PriorityBadge value={t.priority} />
                  </td>
                  <td className="px-4 py-3">
                    <CategoryBadge value={t.category} title={`Classified by: ${CLASSIFIED_BY[t.classified_by]}`} />
                    <span className="ml-1 text-[10px] text-slate-400" title={`Classified by: ${CLASSIFIED_BY[t.classified_by]}`}>
                      {t.classified_by === "AI" ? "✨AI" : t.classified_by === "ADMIN" ? "✎" : "rules"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge value={t.status} />
                  </td>
                  <td className="px-4 py-3 text-slate-600">{t.assigned_to?.name ?? <span className="text-slate-400">Unassigned</span>}</td>
                  <td className="whitespace-nowrap px-4 py-3" title={`Created ${dateTime(t.created_at)}`}>
                    <span className={t.sla_breached ? "font-semibold text-red-600" : "text-slate-600"}>{timeAgo(t.created_at)}</span>
                    {t.sla_breached && <span className="ml-1.5 rounded bg-red-100 px-1 py-0.5 text-[10px] font-semibold text-red-700">SLA</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function StatsBar({ stats, onPick }) {
  const unresolved = (stats.by_status.OPEN ?? 0) + (stats.by_status.IN_PROGRESS ?? 0);
  const urgent = (stats.unresolved_by_priority.CRITICAL ?? 0) + (stats.unresolved_by_priority.HIGH ?? 0);
  const ai = stats.ai.last_7_days ?? {};
  const aiCalls = Object.values(ai).reduce((n, t) => n + t.calls, 0);
  const aiTokens = Object.values(ai).reduce((n, t) => n + t.prompt_tokens + t.completion_tokens, 0);
  const overrideRate = stats.ai.category_override_rate;

  const cards = [
    { label: "Unresolved", value: unresolved, onClick: () => onPick("status", "UNRESOLVED") },
    { label: "Critical + High", value: urgent, tone: urgent ? "text-red-600" : "" },
    { label: "First reply overdue", value: stats.sla_breached, tone: stats.sla_breached ? "text-red-600" : "" },
    { label: "Unassigned", value: stats.unassigned_unresolved, onClick: () => onPick("assigned", "unassigned") },
  ];
  return (
    <section className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-5">
      {cards.map((c) => (
        <button
          key={c.label}
          type="button"
          onClick={c.onClick}
          disabled={!c.onClick}
          className="rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm enabled:hover:border-brand-500"
        >
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{c.label}</p>
          <p className={`mt-1 text-2xl font-semibold ${c.tone || "text-slate-900"}`}>{c.value}</p>
        </button>
      ))}
      <div className="col-span-2 rounded-xl border border-violet-200 bg-violet-50/60 p-4 lg:col-span-1">
        <p className="text-xs font-medium uppercase tracking-wide text-violet-700">✨ AI · last 7 days</p>
        <p className="mt-1 text-sm text-slate-700">
          <span className="font-semibold">{aiCalls}</span> calls · <span className="font-semibold">{aiTokens.toLocaleString("en-IN")}</span> tokens
        </p>
        <p className="text-xs text-slate-500">
          Category overrides: {overrideRate == null ? "—" : `${Math.round(overrideRate * 100)}%`}
        </p>
      </div>
    </section>
  );
}
