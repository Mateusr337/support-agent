import { useEffect, useState } from "react";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL;
if (!API_URL) {
  throw new Error(
    "VITE_API_URL is not set. Copy frontend/.env.example to frontend/.env"
  );
}

export default function App() {
  const [apiStatus, setApiStatus] = useState("loading");
  const [dbStatus, setDbStatus] = useState("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => res.json())
      .then(() => setApiStatus("ok"))
      .catch(() => setApiStatus("error"));

    fetch(`${API_URL}/health/db`)
      .then((res) => res.json())
      .then(() => setDbStatus("ok"))
      .catch(() => setDbStatus("error"));

    fetch(`${API_URL}/api/hello`)
      .then((res) => res.json())
      .then((data) => setMessage(data.message))
      .catch(() => setMessage("Failed to reach API"));
  }, []);

  return (
    <main className="app">
      <h1>Support Agent</h1>
      <p className="subtitle">React + FastAPI monolith</p>

      <section className="status-card">
        <div className="status-row">
          <span>API</span>
          <span className={`badge badge-${apiStatus}`}>{apiStatus}</span>
        </div>
        <div className="status-row">
          <span>Database</span>
          <span className={`badge badge-${dbStatus}`}>{dbStatus}</span>
        </div>
      </section>

      {message && <p className="message">{message}</p>}
    </main>
  );
}
