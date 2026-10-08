// A ticket's conversation: the original query followed by replies (and, for admins, internal notes).
import { dateTime, timeAgo } from "../../utils/format";

export default function MessageThread({ ticket, authorName, messages, viewerRole }) {
  const items = [
    {
      id: "original",
      kind: "REPLY",
      sender_role: "AUTHOR",
      sender_name: authorName,
      body: ticket.description,
      created_at: ticket.created_at,
      original: true,
    },
    ...messages,
  ];

  return (
    <ol className="space-y-4">
      {items.map((m) => (
        <MessageBubble key={m.id} message={m} mine={m.sender_role === viewerRole} viewerRole={viewerRole} />
      ))}
    </ol>
  );
}

function MessageBubble({ message: m, mine, viewerRole }) {
  const note = m.kind === "NOTE";
  const fromBookLeaf = m.sender_role === "ADMIN";
  const who = fromBookLeaf && viewerRole === "AUTHOR" ? "BookLeaf Support" : m.sender_name;

  const tone = note
    ? "bg-amber-50 ring-amber-200"
    : fromBookLeaf
      ? "bg-brand-50 ring-brand-100"
      : "bg-white ring-slate-200";

  return (
    <li className={`flex ${mine ? "justify-end" : "justify-start"}`}>
      <div className={`w-full max-w-2xl rounded-xl px-4 py-3 shadow-sm ring-1 ${tone}`}>
        <div className="mb-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
          <Avatar name={who} admin={fromBookLeaf} />
          <span className="font-semibold text-slate-800">{who}</span>
          {m.original && <span className="text-slate-500">· original query</span>}
          {note && (
            <span className="rounded bg-amber-200/70 px-1.5 py-0.5 font-semibold text-amber-900">🔒 Internal note</span>
          )}
          {m.ai_assisted && viewerRole === "ADMIN" && (
            <span className="rounded bg-violet-100 px-1.5 py-0.5 font-medium text-violet-700">✨ AI-assisted</span>
          )}
          <span className="ml-auto text-slate-500" title={dateTime(m.created_at)}>
            {timeAgo(m.created_at)}
          </span>
        </div>
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{m.body}</p>
      </div>
    </li>
  );
}

function Avatar({ name, admin }) {
  const initials = (name || "?")
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  return (
    <span
      className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-semibold ${
        admin ? "bg-brand-700 text-white" : "bg-slate-200 text-slate-700"
      }`}
    >
      {initials}
    </span>
  );
}
