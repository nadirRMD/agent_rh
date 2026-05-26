"""Appels au modele."""

import os

import httpx
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="gpt-5.4-mini",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    http_client=httpx.Client(trust_env=False),
    api_key=os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY"),
)
