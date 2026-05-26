"""FastAPI entrypoint for the Agent RH project."""

import base64
import hashlib
import hmac
import json
import os
import time
from contextlib import contextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field

from agent import agent, set_authenticated_login
from jibble.demande_conge import demander_conge
from jibble.jibble_connect import get_jibble_access_token, jibble_member_exists
from monitoring import get_dashboard, log_request


app = FastAPI(title="Agent RH")
AUTH_SECRET = os.getenv("FRONTEND_AUTH_SECRET", "agent-rh-dev-secret")

frontend_origin = os.getenv("AGENT_RH_FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin, "http://127.0.0.1:3000"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)


class LeaveRequest(BaseModel):
    start_date: str = Field(min_length=1)
    end_date: str = Field(min_length=1)
    note: str = Field(default="Just a vacation", min_length=1)
    person_id: str = Field(min_length=1)


def _base64_url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign_auth_payload(payload_part: str) -> str:
    digest = hmac.new(
        AUTH_SECRET.encode("utf-8"),
        payload_part.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("utf-8")


def _extract_login_from_token(token: str) -> str | None:
    if not isinstance(token, str) or not token:
        return None

    try:
        payload_part, signature = token.split(".", 1)
    except ValueError:
        return None

    if not payload_part or not signature:
        return None

    if not hmac.compare_digest(_sign_auth_payload(payload_part), signature):
        return None

    try:
        payload = json.loads(_base64_url_decode(payload_part))
    except (ValueError, json.JSONDecodeError):
        return None

    login = payload.get("login")
    exp = payload.get("exp")
    if not isinstance(login, str) or not login.strip():
        return None

    if not isinstance(exp, int) or exp < int(time.time()):
        return None

    return login.strip()


def _get_authenticated_login(headers) -> str | None:
    token = headers.get("x-agent-rh-token")
    if not token:
        authorization = headers.get("authorization")
        if authorization:
            scheme, _, bearer_token = authorization.partition(" ")
            if scheme.lower() == "bearer":
                token = bearer_token.strip()

    return _extract_login_from_token(token or "")


@contextmanager
def _auth_context(login: str | None):
    set_authenticated_login(login)
    try:
        yield
    finally:
        set_authenticated_login(None)


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


def ask_agent(question: str, authenticated_login: str | None = None) -> str:
    start_time = time.perf_counter()
    try:
        messages = []
        if authenticated_login:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Identifiant utilisateur authentifie: "
                        f"{authenticated_login}. "
                        "Utilise cet identifiant comme person_id pour demander_conge "
                        "sauf si l'utilisateur fournit explicitement un autre identifiant."
                    ),
                }
            )
        messages.append({"role": "user", "content": question})

        with _auth_context(authenticated_login):
            result = agent.invoke({"messages": messages})
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
def chat(payload: ChatRequest, request: Request) -> str:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question vide.")

    authenticated_login = _get_authenticated_login(request.headers)
    if not authenticated_login:
        raise HTTPException(status_code=401, detail="Unauthorized.")

    return ask_agent(question, authenticated_login=authenticated_login)


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


@app.get("/jibble/token")
def jibble_token() -> dict[str, object]:
    try:
        return get_jibble_access_token()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur Jibble: {exc}") from exc


@app.get("/jibble/member-exists")
def jibble_member_exists_endpoint(user_id: str = Query(min_length=1)) -> dict[str, object]:
    try:
        exists = jibble_member_exists(user_id)
        return {"exists": exists}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur Jibble: {exc}") from exc


@app.post("/jibble/demande-conge")
def jibble_demande_conge(payload: LeaveRequest) -> dict[str, object]:
    try:
        status_code, body = demander_conge(
            start_date=payload.start_date,
            end_date=payload.end_date,
            note=payload.note,
            person_id=payload.person_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur Jibble: {exc}") from exc

    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=body)

    return {"status_code": status_code, "body": body}


def main() -> None:
    host = os.getenv("AGENT_RH_HOST", "127.0.0.1")
    port = int(os.getenv("AGENT_RH_PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
