// One ticket's conversation with BookLeaf support (auto-refreshing), plus a follow-up box.
import { useEffect, useState } from "react";
import { Link, useLocation, useOutletContext, useParams } from "react-router-dom";
import { getMyTicket, replyToTicket } from "../../api/tickets";
import { useAuth } from "../../context/AuthContext";
import usePolling from "../../hooks/usePolling";
import { POLL_MS } from "../../utils/constants";
import { dateTime } from "../../utils/format";
import Alert from "../../components/common/Alert";
import { CategoryBadge, StatusBadge } from "../../components/common/Badge";
import Button from "../../components/common/Button";
import { Textarea } from "../../components/common/Field";
import { PageLoader } from "../../components/common/Spinner";
import MessageThread from "../../components/tickets/MessageThread";

const STATUS_HELP = {
  OPEN: "We've received your ticket and a team member will pick it up shortly.",
  IN_PROGRESS: "Our team is working on this.",
  RESOLVED: "We believe this is resolved. Reply below if you still need help and we'll re-open it.",
  CLOSED: "This ticket is closed. Please raise a new ticket if you need further help.",
};

export default function TicketDetailPage() {
  const { number } = useParams();
  const { user } = useAuth();
  const location = useLocation();
  const { data: ticket, setData, error, loading } = usePolling(() => getMyTicket(number), POLL_MS.authorTickets, [number]);
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState(null);
  const { refreshTickets } = useOutletContext();

  // Viewing the ticket marks its replies as read on the server; refresh the nav badge right away.
  const messageCount = ticket?.messages.length;
  useEffect(() => {
    if (messageCount != null) refreshTickets();
  }, [number, messageCount, refreshTickets]);

  if (loading && !ticket) return <PageLoader />;
  if (error && !ticket) {
    return (
      <Alert tone="error" title={error.status === 404 ? "Ticket not found" : "Couldn't load this ticket"}>
        {error.message} <Link to="/tickets" className="underline">Back to my tickets</Link>
      </Alert>
    );
  }

  const send = async (e) => {
    e.preventDefault();
    setSending(true);
    setSendError(null);
    try {
      setData(await replyToTicket(number, reply));
      setReply("");
    } catch (err) {
      setSendError(err);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl">
      <Link to="/tickets" className="text-sm text-slate-500 hover:text-slate-800">
        ← My tickets
      </Link>
      {location.state?.created && (
        <Alert tone="success" className="mt-4" title={`Ticket #${ticket.ticket_number} submitted`}>
          Thanks! Our team has been notified. You'll see replies here as soon as they're sent.
        </Alert>
      )}

      <div className="mt-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-medium text-slate-400">Ticket #{ticket.ticket_number}</p>
            <h1 className="text-xl font-semibold text-slate-900">{ticket.subject}</h1>
            <p className="mt-1 text-sm text-slate-500">
              {ticket.book ? ticket.book.title : "General / Account level"} · Opened {dateTime(ticket.created_at)}
            </p>
          </div>
          <div className="flex gap-2">
            <CategoryBadge value={ticket.category} />
            <StatusBadge value={ticket.status} />
          </div>
        </div>
        <p className="mt-3 text-sm text-slate-600">{STATUS_HELP[ticket.status]}</p>
        {ticket.attachment_name && <p className="mt-2 text-xs text-slate-500">📎 {ticket.attachment_name}</p>}
      </div>

      <div className="mt-6">
        <MessageThread ticket={ticket} authorName={user.name} messages={ticket.messages} viewerRole="AUTHOR" />
        {ticket.messages.length === 0 && (
          <p className="mt-4 text-center text-sm text-slate-500">
            <span className="mr-1 inline-block h-2 w-2 animate-pulse rounded-full bg-brand-500" /> Waiting for a reply from BookLeaf Support…
          </p>
        )}
      </div>

      {ticket.status !== "CLOSED" && (
        <form onSubmit={send} className="mt-6 space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          {sendError && <Alert tone="error">{sendError.message}</Alert>}
          <Textarea
            id="reply"
            label="Add a message"
            rows={3}
            placeholder="Add more details or reply to our team…"
            value={reply}
            onChange={(e) => setReply(e.target.value)}
          />
          <div className="flex justify-end">
            <Button type="submit" loading={sending} disabled={!reply.trim()}>
              Send
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
