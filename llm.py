"""Appels au modele."""
from langchain_openai import ChatOpenAI
import os

model = ChatOpenAI(
model="gpt-5.4-mini",
temperature=0,
max_tokens=None,
timeout=None,
max_retries=2,
 api_key=os.getenv("OPENAI_API_KEY"),
)

