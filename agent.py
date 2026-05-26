from contextvars import ContextVar
from datetime import timedelta
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool

from calendarAPI import OutlookCalendarClient, OutlookCalendarConfig
from config import MICROSOFT_CLIENT_ID
from jibble.demande_conge import demander_conge as jibble_demander_conge
from jibble.jibble_connect import jibble_member_exists as jibble_member_exists_api
from llm import model
from rag.rag_qa import answer_question

load_dotenv()

CURRENT_AUTHENTICATED_LOGIN: ContextVar[str | None] = ContextVar(
    "CURRENT_AUTHENTICATED_LOGIN",
    default=None,
)


def set_authenticated_login(login: str | None) -> None:
    """Store the authenticated login for the current request context."""
    CURRENT_AUTHENTICATED_LOGIN.set(login.strip() if isinstance(login, str) and login.strip() else None)


def get_authenticated_login() -> str | None:
    """Return the login attached to the current request context."""
    return CURRENT_AUTHENTICATED_LOGIN.get()


def _build_calendar_client() -> OutlookCalendarClient:
    """Create a calendar client with the current environment settings."""
    return OutlookCalendarClient(
        OutlookCalendarConfig(
            client_id=MICROSOFT_CLIENT_ID,
            tenant_id=os.getenv("MICROSOFT_TENANT_ID", "common"),
            timezone=os.getenv("MICROSOFT_TIMEZONE", "Europe/Paris"),
        )
    )


@tool
def get_calendar(
    from_date: str,
    end_date: str | None = None,
    days: float | None = None,
    top: int = 10,
) -> str:
    """Get Outlook calendar events between two dates."""
    if not MICROSOFT_CLIENT_ID:
        return "Missing MICROSOFT_CLIENT_ID in config.py."

    if days is not None and end_date is not None:
        return "Use either days or end_date, not both."

    client = _build_calendar_client()

    try:
        resolved_end_date = end_date
        if days is not None:
            start_dt = client._parse_start(from_date)
            resolved_end_date = (start_dt + timedelta(days=days)).isoformat()

        events = client.list_events_from(from_date, end_date=resolved_end_date, top=top)
    except Exception as exc:
        return f"Calendar lookup failed: {exc}"

    if not events:
        return "Aucun evenement trouve."

    return "\n".join(client._event_label(event) for event in events)


@tool
def ask_rag(question: str) -> str:
    """Query the local RH RAG documents."""
    if not question.strip():
        return "Veuillez fournir une question non vide."

    try:
        result = answer_question(question)
    except Exception as exc:
        return f"RAG lookup failed: {exc}"

    return str(result.get("answer", ""))


@tool
def jibble_member_exists(user_id: str) -> str:
    """Check whether a Jibble member exists by id."""
    if not user_id.strip():
        return "Veuillez fournir un identifiant valide."

    try:
        exists = jibble_member_exists_api(user_id.strip())
    except Exception as exc:
        return f"Jibble member lookup failed: {exc}"

    if exists:
        return f"Le membre Jibble '{user_id}' existe."

    return f"Le membre Jibble '{user_id}' n'existe pas."


@tool
def demander_conge(
    start_date: str,
    end_date: str,
    note: str,
    person_id: str | None = None,
) -> str:
    """Submit a Jibble leave request for an existing member."""
    authenticated_login = get_authenticated_login()
    resolved_person_id = person_id.strip() if isinstance(person_id, str) and person_id.strip() else authenticated_login

    if not all(value.strip() for value in (start_date, end_date, note)):
        return "Veuillez fournir start_date, end_date et note."

    if not resolved_person_id:
        return "Impossible de determiner l'identifiant du membre authentifie."

    try:
        status_code, body = jibble_demander_conge(
            start_date=start_date.strip(),
            end_date=end_date.strip(),
            note=note.strip(),
            person_id=resolved_person_id,
        )
    except Exception as exc:
        return f"Demande de conge Jibble echouee: {exc}"

    return f"Status: {status_code}. Response: {body}"


agent = create_agent(
    model=model,
    tools=[get_calendar, ask_rag, demander_conge],
    system_prompt=(
        "Tu es un assistant RH. tu dois expliquer que "
        "tu peux aider a poser des conges avec demander_conge, verifier les conflits de "
        "planning dans le calendrier avec get_calendar, et verifier les regles RH dans les "
        "documents indexes avec ask_rag. "
        "Pour poser un conge, tu dois demander les informations manquantes: date de debut, "
        "date de fin et note. Si un identifiant authentifie est disponible dans le contexte, "
        "utilise-le comme identifiant du membre et ne le redemande pas. "
        "Pour verifier le planning, tu dois utiliser get_calendar. "
        "Pour verifier les regles RH, tu dois utiliser ask_rag. "
        "Ne lance aucune demande de conge avant d'avoir verifie que le membre existe."
    ),
)
