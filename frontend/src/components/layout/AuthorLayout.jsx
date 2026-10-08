// Shell for author pages: My Books, My Tickets, Get Help.
// Polls the author's tickets once here so the nav can show a "new replies" badge on every page;
// child pages read the same data through the outlet context instead of fetching it again.
import { Outlet } from "react-router-dom";
import { listMyTickets } from "../../api/tickets";
import usePolling from "../../hooks/usePolling";
import { POLL_MS } from "../../utils/constants";
import Shell from "./Shell";

export default function AuthorLayout() {
  const { data: tickets, refresh: refreshTickets } = usePolling(listMyTickets, POLL_MS.authorTickets);
  const unread = tickets?.filter((t) => t.unread_reply).length ?? 0;

  const nav = [
    { to: "/books", label: "My Books" },
    { to: "/tickets", label: "My Tickets", end: true, badge: unread || null },
    { to: "/tickets/new", label: "Get Help" },
  ];

  return (
    <Shell nav={nav} badge="Author">
      <Outlet context={{ tickets, refreshTickets }} />
    </Shell>
  );
}
