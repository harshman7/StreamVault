import axios from "axios";

const baseURL =
  import.meta.env.VITE_BACKEND_URL?.replace(/\/$/, "") || "http://localhost:8000";

export const api = axios.create({
  baseURL,
  headers: {
    Accept: "application/json",
  },
});

export function getBackendOrigin(): string {
  return baseURL;
}
