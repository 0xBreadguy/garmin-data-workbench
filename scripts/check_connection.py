"""Verify Garmin Personal API access without printing personal data."""

import logging
import sys

from garmin_personal_api import (
    GarminPersonalApiClient,
    PersonalApiAuthenticator,
    resolve_api_key,
)


def main() -> int:
    # The Garmin client can log request URLs; don't print response payloads.
    logging.disable(logging.CRITICAL)
    try:
        with PersonalApiAuthenticator() as authenticator:
            token = authenticator.obtain_token(resolve_api_key())
        with GarminPersonalApiClient(token.access_token) as client:
            client.get_user_profile_settings()
            activities = client.search_activities(start=0, limit=1)
    except Exception as error:  # noqa: BLE001 -- avoid exposing response bodies at the CLI boundary
        # Exception text can contain response bodies; expose only its type.
        print(f"Connection check failed ({type(error).__name__}).", file=sys.stderr)
        return 1

    print("Garmin Personal API authentication and read requests succeeded.")
    if isinstance(activities, list):
        print("A recent activity is available." if activities else "No recent activity was returned.")
    else:
        print("The activity search returned a response; its format requires inspection.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
