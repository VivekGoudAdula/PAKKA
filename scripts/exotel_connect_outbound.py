#!/usr/bin/env python3
"""
scripts/exotel_connect_outbound.py
Triggers an outbound call via Exotel's Calls/connect API with bidirectional WebSocket streaming.

Uses credentials from .env:
  EXOTEL_API_KEY, EXOTEL_API_TOKEN, EXOTEL_SID, EXOTEL_SUBDOMAIN, PUBLIC_WSS_URL

Usage:
  python scripts/exotel_connect_outbound.py --to +919876543210 [--caller-id 080XXXXXXXX] [--dry-run]
"""

import argparse
import logging
import sys
from pathlib import Path

# Add apps/api to path
API_DIR = Path(__file__).resolve().parent.parent / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

import httpx
from app.config import settings

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("exotel_outbound")


def trigger_outbound_call(
    to_number: str,
    caller_id: str | None = None,
    stream_url: str | None = None,
    dry_run: bool = False,
) -> dict:
    """
    Initiate outbound call to to_number with bidirectional audio streaming to stream_url.
    """
    account_sid = settings.exotel_sid
    api_key = settings.exotel_api_key
    api_token = settings.exotel_api_token
    subdomain = settings.exotel_subdomain or "api.in.exotel.com"
    stream_url = stream_url or settings.public_wss_url

    if not stream_url:
        stream_url = "wss://placeholder.ngrok-free.app/ws/exotel"

    caller_id = caller_id or settings.exophone_number or "080XXXXXXXX"

    endpoint = f"https://{subdomain}/v1/Accounts/{account_sid}/Calls/connect.json"

    print("=" * 60)
    print("  PAKKA — EXOTEL OUTBOUND CALL INITIATOR")
    print("=" * 60)
    print(f"Target Number: {to_number}")
    print(f"Caller ID:     {caller_id}")
    print(f"Stream URL:    {stream_url}")
    print(f"Account SID:   {account_sid}")
    print(f"Endpoint:      {endpoint}")
    print("-" * 60)

    if (
        dry_run
        or not api_key
        or "your_" in api_token
        or api_key in ("mock", "placeholder")
    ):
        logger.info("[DRY_RUN] Simulating Exotel POST %s", endpoint)
        mock_response = {
            "Call": {
                "Sid": f"mock_call_{account_sid}_001",
                "AccountSid": account_sid,
                "From": to_number,
                "To": caller_id,
                "Status": "in-progress",
                "StartTime": "2026-11-03 10:45:00",
                "StreamUrl": stream_url,
            }
        }
        print("Response (MOCK):")
        print(mock_response)
        return mock_response

    payload = {
        "From": to_number,
        "CallerId": caller_id,
        "CallType": "trans",
        "StreamUrl": stream_url,
        "StreamType": "bidirectional",
    }

    logger.info("Executing POST to %s with auth (%s:...)", endpoint, api_key[:6])
    with httpx.Client(timeout=15.0) as client:
        response = client.post(
            endpoint,
            auth=(api_key, api_token),
            data=payload,
        )

        logger.info("Exotel HTTP Status: %d", response.status_code)
        try:
            data = response.json()
            print("Response from Exotel:")
            print(data)
            return data
        except Exception:  # noqa: BLE001
            print(f"Raw Response: {response.text}")
            return {"raw": response.text, "status_code": response.status_code}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Trigger Exotel Outbound Voicebot Call"
    )
    parser.add_argument(
        "--to", required=False, default="+919876543210", help="Destination phone number"
    )
    parser.add_argument("--caller-id", required=False, help="Virtual ExoPhone number")
    parser.add_argument(
        "--stream-url", required=False, help="Public wss:// URL for audio stream"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate without external HTTP call"
    )
    args = parser.parse_args()

    trigger_outbound_call(
        to_number=args.to,
        caller_id=args.caller_id,
        stream_url=args.stream_url,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
