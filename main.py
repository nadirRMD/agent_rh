"""FastAPI entrypoint for the Agent RH project."""

import os

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from agent import agent


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


def ask_agent(question: str) -> str:
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    return _extract_text(result["messages"][-1])


@app.get("/", response_class=PlainTextResponse)
def healthcheck() -> str:
    return "Agent RH API is running."


@app.post("/chat", response_class=PlainTextResponse)
def chat(payload: ChatRequest) -> str:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question vide.")

    return ask_agent(question)


def main() -> None:
    host = os.getenv("AGENT_RH_HOST", "127.0.0.1")
    port = int(os.getenv("AGENT_RH_PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
