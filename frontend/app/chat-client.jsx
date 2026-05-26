"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { clearAuthToken, readAuthToken } from "../lib/auth-client";

const examples = [
  "Quels sont les conges poses en juin ?",
  "Y a-t-il un conflit avec un conge du 12 au 14 juin ?",
  "Que dit le document sur les conges maladie ?",
];

export default function ChatClient() {
  const router = useRouter();
  const [question, setQuestion] = useState(examples[0]);
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!readAuthToken()) {
      router.replace("/login");
    }
  }, [router]);

  let statusLabel = "Pret";
  if (loading) {
    statusLabel = "Envoi en cours";
  } else if (error) {
    statusLabel = "Erreur";
  } else if (answer) {
    statusLabel = "Reponse";
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const token = readAuthToken();
    if (!token) {
      router.replace("/login");
      return;
    }

    setLoading(true);
    setError("");
    setAnswer("");

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-agent-rh-token": token,
        },
        body: JSON.stringify({ question }),
      });

      const text = await response.text();
      if (response.status === 401) {
        clearAuthToken();
        router.replace("/login");
        return;
      }
      if (!response.ok) {
        throw new Error(text || `Request failed with status ${response.status}`);
      }

      setAnswer(text);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Une erreur est survenue.");
    } finally {
      setLoading(false);
    }
  }

  async function handleLogout() {
    clearAuthToken();
    router.replace("/login");
  }

  return (
    <main className="shell">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Agent RH</p>
          <h1>SmartRH Assistant</h1>
          <p className="lede">
         Posez une question sur les congés ou les règles RH, puis laissez l’assistant vous guider.
          </p>
          <div className="auth-actions">
            <span className="auth-pill">Acces direct</span>
            <button type="button" className="ghost-button" onClick={handleLogout}>
              Deconnexion
            </button>
          </div>
          <div className="chips" aria-label="Exemples de questions">
            {examples.map((item) => (
              <button
                key={item}
                type="button"
                className="chip"
                onClick={() => setQuestion(item)}
              >
                {item}
              </button>
            ))}
          </div>
        </div>

        <aside className="panel">
          <div className="panel-head">
            <span className="status-dot" />
            <span>{statusLabel}</span>
          </div>

          <form className="composer" onSubmit={handleSubmit}>
            <label htmlFor="question">Question</label>
            <textarea
              id="question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Tapez votre question ici..."
              rows={7}
              required
            />
            <button type="submit" disabled={loading}>
              {loading ? "Traitement..." : "Envoyer"}
            </button>
          </form>

          <div className="response">
            <div className="response-head">
              <h2>Retour</h2>
              <span>POST /api/chat via frontend</span>
            </div>
            {error ? (
              <pre className="response-box error">{error}</pre>
            ) : (
              <pre className="response-box">
                {answer || "La reponse apparaitra ici."}
              </pre>
            )}
          </div>
        </aside>
      </section>
    </main>
  );
}
