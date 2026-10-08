// Author ticket API calls.
import client from "./client";

export const listMyTickets = () => client.get("/tickets").then((r) => r.data);
export const getMyTicket = (number) => client.get(`/tickets/${number}`).then((r) => r.data);
export const createTicket = (data) => client.post("/tickets", data).then((r) => r.data);
export const replyToTicket = (number, body) => client.post(`/tickets/${number}/messages`, { body }).then((r) => r.data);
