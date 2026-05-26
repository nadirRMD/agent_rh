"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AUTH_STORAGE_KEY } from "../../lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [login, setLogin] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (window.localStorage.getItem(AUTH_STORAGE_KEY)) {
      router.replace("/");
    }
  }, [router]);

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setStatus("");

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ login }),
      });

      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || "Authentication failed.");
      }

      const data = await response.json();
      if (typeof data?.token !== "string" || !data.token) {
        throw new Error("Authentication failed.");
      }

      window.localStorage.setItem(AUTH_STORAGE_KEY, data.token);
      setStatus("success");
      window.location.assign("/");
    } catch (err) {
      setStatus("fail");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell login-shell">
      <section className="login-panel">
        <p className="eyebrow">Agent RH</p>
        <h1>Connexion requise</h1>
        <p className="lede">
          Entrez votre identifiant pour acceder a l'assistant RH.
        </p>

        <form className="composer" onSubmit={handleSubmit}>
          <label htmlFor="login">Identifiant</label>
          <input
            id="login"
            type="text"
            value={login}
            onChange={(event) => setLogin(event.target.value)}
            placeholder="Identifiant"
            autoComplete="username"
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? "Connexion..." : "Se connecter"}
          </button>
        </form>

        {status ? (
          <pre className={`response-box ${status === "fail" ? "error" : ""}`}>
            {status}
          </pre>
        ) : null}
      </section>
    </main>
  );
}
