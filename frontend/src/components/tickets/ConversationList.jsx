// Author's tickets as conversations: subject, book, latest message preview and a "New reply" marker.
// Used on the My Tickets page and (limited to the latest few) on the My Books dashboard.
import { Link } from "react-router-dom";
import { timeAgo } from "../../utils/format";
import { CategoryBadge, StatusBadge } from "../common/Badge";

export default function ConversationList({ tickets }) {
  return (
    <ul className="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      {tickets.map((t) => {
        const last = t.messages[t.messages.length - 1];
        const fromUs = last?.sender_role === "ADMIN";
        const preview = last ? last.body : t.description;
        return (
          <li key={t.ticket_number}>
            <Link
              to={`/tickets/${t.ticket_number}`}
              className={`flex flex-col gap-2 px-5 py-4 hover:bg-slate-50 sm:flex-row sm:items-center ${t.unread_reply ? "bg-brand-50/50" : ""}`}
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  {t.unread_reply && <span className="h-2 w-2 shrink-0 rounded-full bg-red-500" aria-hidden="true" />}
                  <span className="text-xs font-medium text-slate-400">#{t.ticket_number}</span>
                  <p className={`truncate text-slate-900 ${t.unread_reply ? "font-semibold" : "font-medium"}`}>{t.subject}</p>
                  {t.unread_reply && (
                    <span className="shrink-0 rounded-full bg-red-500 px-2 py-0.5 text-[11px] font-semibold text-white">New reply</span>
                  )}
                </div>
                <p className="mt-0.5 truncate text-sm text-slate-500">
                  <span className="text-slate-400">{t.book ? t.book.title : "General / Account level"} · </span>
                  <span className={fromUs ? "text-brand-700" : ""}>
                    {last ? (fromUs ? "BookLeaf Support: " : "You: ") : "You: "}
                  </span>
                  {preview.replace(/\s+/g, " ")}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <span className="text-xs text-slate-400">{timeAgo(last?.created_at ?? t.created_at)}</span>
                <CategoryBadge value={t.category} />
                <StatusBadge value={t.status} />
              </div>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
