from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import msal
import requests
from msal_extensions import FilePersistence, PersistedTokenCache


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
DEFAULT_SCOPES = ["User.Read", "Calendars.Read"]
DEFAULT_AUTHORITY_TENANT = "common"


@dataclass(slots=True)
class OutlookCalendarConfig:
    """Configuration for Microsoft Graph calendar access."""

    client_id: str
    tenant_id: str = DEFAULT_AUTHORITY_TENANT
    scopes: list[str] = field(default_factory=lambda: DEFAULT_SCOPES.copy())
    timezone: str = "Europe/Paris"
    cache_path: Path = Path.home() / ".agent-rh" / "msal_token_cache.bin"

    @property
    def authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}"


class OutlookCalendarClient:
    """Authenticate against Microsoft Graph and fetch Outlook calendar events."""

    def __init__(self, config: OutlookCalendarConfig):
        if not config.client_id:
            raise ValueError("OutlookCalendarConfig.client_id must not be empty.")

        self.config = config
        self.session = requests.Session()
        self.session.trust_env = False
        self.persistence = FilePersistence(str(self.config.cache_path))
        self.cache = self._build_cache()
        self.app = msal.PublicClientApplication(
            client_id=self.config.client_id,
            authority=self.config.authority,
            token_cache=self.cache,
            http_client=self.session,
        )

    def _build_cache(self) -> PersistedTokenCache:
        self.config.cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache = PersistedTokenCache(self.persistence)
        if self.config.cache_path.exists():
            cache.deserialize(self.persistence.load())
        return cache

    def _save_cache(self) -> None:
        if self.cache.has_state_changed:
            self.persistence.save(self.cache.serialize())

    def clear_cache(self) -> None:
        """Supprime le cache de jetons persistant et vide le cache en mémoire."""
        self.cache.deserialize(None)
        if self.config.cache_path.exists():
            self.config.cache_path.unlink()

    def acquire_token(self) -> str:
        """Acquire an access token using silent auth first, then browser-based sign-in."""
        accounts = self.app.get_accounts()
        result: dict[str, Any] | None = None

        if accounts:
            result = self.app.acquire_token_silent(
                scopes=self.config.scopes,
                account=accounts[0],
            )

        if not result or "access_token" not in result:
            result = self.app.acquire_token_interactive(
                scopes=self.config.scopes,
                prompt="select_account",
                port=8400,
            )

        self._save_cache()

        if "access_token" not in result:
            raise RuntimeError(
                "Microsoft authentication failed: "
                f"{result.get('error')} - {result.get('error_description')}"
            )

        return result["access_token"]

    def _graph_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.acquire_token()}",
            "Accept": "application/json",
            "Prefer": f'outlook.timezone="{self.config.timezone}"',
        }

    @staticmethod
    def _resolve_timezone(timezone_name: str) -> timezone | ZoneInfo:
        try:
            return ZoneInfo(timezone_name)
        except Exception:
            return datetime.now().astimezone().tzinfo or timezone.utc

    def _parse_start(self, value: date | datetime | str) -> datetime:
        local_tz = self._resolve_timezone(self.config.timezone)
        if isinstance(value, datetime):
            start_dt = value
        elif isinstance(value, date):
            start_dt = datetime.combine(value, datetime.min.time(), tzinfo=local_tz)
        else:
            start_dt = datetime.fromisoformat(value)
            if len(value) == 10:
                start_dt = datetime.combine(start_dt.date(), datetime.min.time(), tzinfo=local_tz)

        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=local_tz)
        return start_dt

    def _parse_end(self, value: date | datetime | str) -> datetime:
        local_tz = self._resolve_timezone(self.config.timezone)
        if isinstance(value, datetime):
            end_dt = value
        elif isinstance(value, date):
            end_dt = datetime.combine(value, datetime.max.time(), tzinfo=local_tz)
        else:
            end_dt = datetime.fromisoformat(value)
            if len(value) == 10:
                end_dt = datetime.combine(end_dt.date(), datetime.max.time(), tzinfo=local_tz)

        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=local_tz)
        return end_dt

    @staticmethod
    def _format_graph_datetime(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _build_overlap_filter(query_start: str, query_end: str | None = None) -> str:
        if query_end is None:
            return f"end/dateTime ge '{query_start}'"
        return f"start/dateTime le '{query_end}' and end/dateTime ge '{query_start}'"

    def list_events_from(
        self,
        start: date | datetime | str,
        end_date: date | datetime | str | None = None,
        top: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch events starting from the given date/time, optionally up to an end date."""
        start_dt = self._parse_start(start)
        query_start = self._format_graph_datetime(start_dt)
        query_end = self._format_graph_datetime(self._parse_end(end_date)) if end_date is not None else None
        filter_expr = self._build_overlap_filter(query_start, query_end)
        url = (
            f"{GRAPH_BASE_URL}/me/events"
            f"?$filter={filter_expr}"
            f"&$orderby=start/dateTime"
            f"&$top={top}"
            f"&$select=subject,start,end,location,isAllDay,organizer,webLink"
        )

        events: list[dict[str, Any]] = []
        next_url: str | None = url
        headers = self._graph_headers()

        while next_url:
            response = self.session.get(next_url, headers=headers, timeout=30)
            response.raise_for_status()
            payload = response.json()
            events.extend(payload.get("value", []))
            next_url = payload.get("@odata.nextLink")

        return events

    def list_events_from_today(
        self,
        end_date: date | datetime | str | None = None,
        top: int = 100,
    ) -> list[dict[str, Any]]:
        """Convenience wrapper for events starting today in the configured timezone."""
        today = datetime.now(self._resolve_timezone(self.config.timezone)).date()
        return self.list_events_from(today, end_date=end_date, top=top)

    @staticmethod
    def _event_label(event: dict[str, Any]) -> str:
        subject = event.get("subject") or "(no subject)"
        start = event.get("start", {}).get("dateTime", "n/a")
        end = event.get("end", {}).get("dateTime", "n/a")
        location = event.get("location", {}).get("displayName") or "no location"
        return f"{start} -> {end} | {subject} | {location}"

    def display_events_from(
        self,
        start: date | datetime | str,
        end_date: date | datetime | str | None = None,
        top: int = 10,
    ) -> None:
        """Affiche simplement les événements du calendrier à partir d'une date donnée."""
        events = self.list_events_from(start, end_date=end_date, top=top)
        if not events:
            print("Aucun événement trouvé.")
            return

        for event in events:
            print(self._event_label(event))

    def display_events_from_today(
        self,
        end_date: date | datetime | str | None = None,
        top: int = 100,
    ) -> None:
        """Affiche les événements à partir d'aujourd'hui."""
        self.display_events_from(
            datetime.now(self._resolve_timezone(self.config.timezone)).date(),
            end_date=end_date,
            top=top,
        )
