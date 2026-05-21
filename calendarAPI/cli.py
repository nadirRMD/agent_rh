from __future__ import annotations

import argparse
import os
from datetime import date, timedelta

from config import MICROSOFT_CLIENT_ID

from .client import OutlookCalendarClient, OutlookCalendarConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Microsoft Outlook calendar helper")
    parser.add_argument("--tenant-id", default=os.getenv("MICROSOFT_TENANT_ID", "common"))
    parser.add_argument("--timezone", default=os.getenv("MICROSOFT_TIMEZONE", "Europe/Paris"))
    parser.add_argument("--from-date", default=str(date.today()))
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--days", type=float, default=None)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Remove the saved Microsoft login cache before authenticating.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not MICROSOFT_CLIENT_ID:
        raise SystemExit("Missing MICROSOFT_CLIENT_ID in config.py.")

    config = OutlookCalendarConfig(
        client_id=MICROSOFT_CLIENT_ID,
        tenant_id=args.tenant_id,
        timezone=args.timezone,
    )
    client = OutlookCalendarClient(config)
    if args.clear_cache:
        client.clear_cache()

    if args.days is not None and args.end_date is not None:
        raise SystemExit("Use either --days or --end-date, not both.")

    end_date = args.end_date
    if args.days is not None:
        start_dt = client._parse_start(args.from_date)
        end_date = (start_dt + timedelta(days=args.days)).isoformat()

    client.display_events_from(args.from_date, end_date=end_date, top=args.top)


if __name__ == "__main__":
    main()
