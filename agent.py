from datetime import timedelta
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool

from calendarAPI import OutlookCalendarClient, OutlookCalendarConfig
from config import MICROSOFT_CLIENT_ID
from llm import model

load_dotenv()

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
    """Get Outlook calendar events between two dates.

    Args:
        from_date: Start date in ISO format, for example 2026-05-06.
        end_date: Optional end date in ISO format.
        days: Optional duration in days. Mutually exclusive with end_date.
        top: Maximum number of events per Graph page.
    """
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
        return "Aucun événement trouvé."

    return "\n".join(client._event_label(event) for event in events)


agent = create_agent(
    model=model,
    tools=[get_calendar],
    system_prompt=(
        "Tu es un assistant RH. Tu aides l'utilisateur à poser un congé et à vérifier "
        "si ce congé coïncide avec des événements dans le calendrier de l'entreprise. "
        "L'utilisateur doit fournir soit une date de début et une date de fin, soit "
        "une date de début et un nombre de jours. Si l'information est incomplète ou "
        "ambiguë, tu dois la demander avant de lancer la vérification. Si un événement "
        "est trouvé, tu dois répondre avec le nom de l'événement, la date de début et "
        "la date de fin."
    ),
)
