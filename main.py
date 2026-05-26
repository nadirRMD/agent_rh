"""FastAPI entrypoint for the Agent RH project."""

import os
import time

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field

from agent import agent
from monitoring import get_dashboard, log_request


app = FastAPI(title="Agent RH")


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)


def _extract_text(message) -> str:
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)

    content_blocks = getattr(message, "content_blocks", None)
    if isinstance(content_blocks, list):
        parts: list[str] = []
        for block in content_blocks:
            if isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)

    return str(message)


def _extract_tokens(result, message) -> tuple[int, int]:
    usage = getattr(message, "usage_metadata", None)
    if isinstance(usage, dict):
        tokens_in = usage.get("input_tokens", 0) or 0
        tokens_out = usage.get("output_tokens", 0) or 0
        return int(tokens_in), int(tokens_out)

    response_metadata = getattr(message, "response_metadata", None)
    if isinstance(response_metadata, dict):
        usage = response_metadata.get("token_usage")
        if isinstance(usage, dict):
            tokens_in = usage.get("prompt_tokens", 0) or 0
            tokens_out = usage.get("completion_tokens", 0) or 0
            return int(tokens_in), int(tokens_out)

    if isinstance(result, dict):
        usage = result.get("usage_metadata")
        if isinstance(usage, dict):
            tokens_in = usage.get("input_tokens", 0) or 0
            tokens_out = usage.get("output_tokens", 0) or 0
            return int(tokens_in), int(tokens_out)

    return 0, 0


def ask_agent(question: str) -> str:
    start_time = time.perf_counter()
    try:
        result = agent.invoke({"messages": [{"role": "user", "content": question}]})
        message = result["messages"][-1]
        answer = _extract_text(message)
        tokens_in, tokens_out = _extract_tokens(result, message)
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        log_request(question, latency_ms, tokens_in, tokens_out)
        return answer
    except Exception as exc:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        log_request(question, latency_ms, 0, 0, error=exc)
        raise HTTPException(status_code=500, detail="Erreur lors du traitement de la requête.")


@app.get("/", response_class=PlainTextResponse)
def healthcheck() -> str:
    return "Agent RH API is running."


@app.post("/chat", response_class=PlainTextResponse)
def chat(payload: ChatRequest) -> str:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question vide.")

    return ask_agent(question)


@app.get("/chat", response_class=HTMLResponse)
def chat_form() -> str:
    return """
    <!doctype html>
    <html lang="fr">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Agent RH Chat</title>
        <style>
          body {
            font-family: Arial, sans-serif;
            max-width: 720px;
            margin: 3rem auto;
            padding: 0 1rem;
            line-height: 1.5;
          }
          form {
            display: grid;
            gap: 1rem;
            margin-top: 1.5rem;
          }
          textarea {
            width: 100%;
            min-height: 140px;
            padding: 0.75rem;
            font: inherit;
          }
          button {
            width: fit-content;
            padding: 0.75rem 1.25rem;
            font: inherit;
            cursor: pointer;
          }
          pre {
            white-space: pre-wrap;
            background: #f5f5f5;
            padding: 1rem;
            min-height: 4rem;
          }
          code {
            background: #f5f5f5;
            padding: 0.1rem 0.3rem;
          }
        </style>
      </head>
      <body>
        <h1>Agent RH Chat</h1>
        <p>Cette page permet d'envoyer une question au <code>POST /chat</code> depuis le navigateur.</p>
        <form id="chat-form">
          <label for="question">Question</label>
          <textarea id="question" name="question" placeholder="Posez une question RH..." required></textarea>
          <button type="submit">Envoyer</button>
        </form>
        <h2>Réponse</h2>
        <pre id="response">En attente de votre question...</pre>
        <script>
          const form = document.getElementById("chat-form");
          const questionInput = document.getElementById("question");
          const responseBox = document.getElementById("response");

          form.addEventListener("submit", async (event) => {
            event.preventDefault();
            responseBox.textContent = "Réflexion en cours...";

            try {
              const response = await fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: questionInput.value }),
              });

              const text = await response.text();
              responseBox.textContent = response.ok ? text : `Erreur ${response.status}: ${text}`;
            } catch (error) {
              responseBox.textContent = `Échec de la requête: ${error}`;
            }
          });
        </script>
      </body>
    </html>
    """


@app.get("/metrics")
def metrics() -> dict[str, object]:
    return get_dashboard()


def main() -> None:
    host = os.getenv("AGENT_RH_HOST", "127.0.0.1")
    port = int(os.getenv("AGENT_RH_PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
