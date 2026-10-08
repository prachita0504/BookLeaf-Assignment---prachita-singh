// Shell for admin (BookLeaf ops team) pages.
import { Outlet } from "react-router-dom";
import Shell from "./Shell";

const NAV = [{ to: "/admin", label: "Ticket Queue", end: true }];

export default function AdminLayout() {
  return (
    <Shell nav={NAV} badge="Support Ops">
      <Outlet />
    </Shell>
  );
}
