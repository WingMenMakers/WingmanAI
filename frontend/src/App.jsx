// src/App.jsx
import { useEffect, useState } from "react";
import Chat from "./components/chat/Chat";

export default function App() {
  const [authLoading, setAuthLoading] = useState(true);
  const [user, setUser] = useState(null);

  useEffect(() => {
    async function checkAuth() {
      try {
        const res = await fetch("http://localhost:8000/me", {
          credentials: "include",
        });

        if (!res.ok) throw new Error("Not authenticated");

        const data = await res.json();
        setUser(data);
      } catch (err) {
        setUser(null);
      } finally {
        setAuthLoading(false);
      }
    }

    checkAuth();
  }, []);

  // -------------------------
  // 1️⃣ Auth loading state
  // -------------------------
  if (authLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-slate-950 text-white">
        <span className="text-sm text-slate-400">Checking authentication…</span>
      </div>
    );
  }

  // -------------------------
  // 2️⃣ Not logged in
  // -------------------------
  if (!user) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-slate-950 text-white">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-semibold">Welcome to WingMan</h1>
          <p className="text-slate-400 text-sm">
            Your personal AI orchestrator
          </p>

          <a
            href="http://localhost:8000/login/google"
            className="inline-block rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium hover:bg-blue-500"
          >
            Sign in with Google
          </a>
        </div>
      </div>
    );
  }

  // -------------------------
  // 3️⃣ Logged in
  // -------------------------
  return (
    <div className="h-screen w-screen bg-slate-950 text-white">
      <Chat />
    </div>
  );
}
