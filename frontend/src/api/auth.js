// Auth API calls: login, register (author sign-up), logout, me.
import client from "./client";

export const login = (email, password) => client.post("/auth/login", { email, password }).then((r) => r.data.user);
export const register = (data) => client.post("/auth/register", data).then((r) => r.data.user);
export const logout = () => client.post("/auth/logout");
export const me = () => client.get("/auth/me").then((r) => r.data);
