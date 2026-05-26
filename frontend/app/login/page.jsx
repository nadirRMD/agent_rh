"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { writeAuthToken } from "../../lib/auth-client";

export default function LoginPage() {
  const router = useRouter();
  const [login, setLogin] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

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
        body: JSON.stringify({ login }),
      });

      const text = await response.text();
      if (!response.ok) {
        throw new Error(text || `Login failed with status ${response.status}`);
      }

      const payload = JSON.parse(text);
      if (typeof payload?.token !== "string" || !payload.token) {
        throw new Error("Login response missing token.");
      }

      writeAuthToken(payload.token);
      router.replace("/");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Une erreur est survenue.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell login-shell">
      <section className="login-panel">
        <p className="eyebrow">Agent RH</p>
        <h1>Connexion</h1>
        <p className="lede">
          Entrez votre identifiant Jibble pour acceder au chat RH.
        </p>

        <form className="composer" onSubmit={handleSubmit}>
          <label htmlFor="login">Identifiant</label>
          <input
            id="login"
            value={login}
            onChange={(event) => setLogin(event.target.value)}
            placeholder="Votre identifiant"
            autoComplete="username"
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? "Verification..." : "Se connecter"}
          </button>
        </form>

        {error ? <pre className="response-box error">{error}</pre> : null}
      </section>
    </main>
  );
}
