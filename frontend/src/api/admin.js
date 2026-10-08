// Admin API calls: queue, ticket detail, updates, replies/notes, AI draft, stats.
import client from "./client";

// Drop empty filter values so the request stays clean.
const clean = (params) => Object.fromEntries(Object.entries(params).filter(([, v]) => v !== "" && v != null));

export const listQueue = (filters) => client.get("/admin/tickets", { params: clean(filters) }).then((r) => r.data);
export const getTicket = (number) => client.get(`/admin/tickets/${number}`).then((r) => r.data);
export const updateTicket = (number, changes) => client.patch(`/admin/tickets/${number}`, changes).then((r) => r.data);
export const addMessage = (number, data) => client.post(`/admin/tickets/${number}/messages`, data).then((r) => r.data);
export const getDraft = (number, regenerate = false) =>
  client.post(`/admin/tickets/${number}/draft`, { regenerate }).then((r) => r.data);
export const getStats = () => client.get("/admin/stats").then((r) => r.data);
export const listAdmins = () => client.get("/admin/users").then((r) => r.data);
