// List of the author's tickets with live status and new-reply markers.
// Data comes from AuthorLayout, which refreshes it every few seconds.
import { Link, useOutletContext } from "react-router-dom";
import EmptyState from "../../components/common/EmptyState";
import { PageLoader } from "../../components/common/Spinner";
import { PageHeader } from "../../components/layout/Shell";
import ConversationList from "../../components/tickets/ConversationList";

export default function MyTicketsPage() {
  const { tickets } = useOutletContext();
  const unread = tickets?.filter((t) => t.unread_reply).length ?? 0;

  return (
    <>
      <PageHeader
        title="My tickets"
        subtitle={
          unread
            ? `You have ${unread} new ${unread === 1 ? "reply" : "replies"} from BookLeaf Support.`
            : "Updates appear here automatically. No need to refresh."
        }
        actions={
          <Link to="/tickets/new" className="rounded-lg bg-brand-700 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-900">
            New ticket
          </Link>
        }
      />
      {!tickets && <PageLoader />}
      {tickets?.length === 0 && (
        <EmptyState icon="💬" title="No tickets yet" action={<Link to="/tickets/new" className="text-sm font-medium text-brand-700 hover:underline">Raise your first ticket →</Link>}>
          Questions about royalties, ISBNs, printing or your book's progress? Our team is here to help.
        </EmptyState>
      )}
      {tickets?.length > 0 && <ConversationList tickets={tickets} />}
    </>
  );
}
