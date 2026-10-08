// Author book API calls.
import client from "./client";

export const getMyBooks = () => client.get("/books").then((r) => r.data);
