const API_URL = import.meta.env.VITE_API_URL;

if (!API_URL) {
  throw new Error(
    "VITE_API_URL is not set. Copy frontend/.env.example to frontend/.env"
  );
}

export { API_URL };
