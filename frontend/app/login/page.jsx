"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AUTH_STORAGE_KEY } from "../../lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (window.localStorage.getItem(AUTH_STORAGE_KEY)) {
      router.replace("/");
    }
  }, [router]);

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ login, password }),
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
      window.location.assign("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed.");
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
          Entrez votre login et votre mot de passe pour accéder à l'assistant RH.
        </p>

        <form className="composer" onSubmit={handleSubmit}>
          <label htmlFor="login">Username</label>
          <input
            id="login"
            type="text"
            value={login}
            onChange={(event) => setLogin(event.target.value)}
            placeholder="Username"
            autoComplete="username"
            required
          />
          <label htmlFor="password">Mot de passe</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Mot de passe"
            autoComplete="current-password"
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? "Connexion..." : "Se connecter"}
          </button>
        </form>

        {error ? <pre className="response-box error">{error}</pre> : null}
      </section>
    </main>
  );
}
