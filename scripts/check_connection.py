"""Verify Garmin Personal API access without printing personal data."""

import argparse
import logging
import sys

from requests.exceptions import Timeout as RequestTimeout

from garmin_personal_api import (
    GarminPersonalApiClient,
    PersonalApiAuthenticator,
    resolve_api_key,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout', type=float, default=15, help='Seconds per live request (1–120; default 15)')
    args = parser.parse_args(argv)
    if not 1 <= args.timeout <= 120:
        parser.error('Timeout must be between 1 and 120 seconds per request')
    # The Garmin client can log request URLs; don't print response payloads.
    previous_log_level = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        print(f"Authenticating Garmin (request timeout {args.timeout:g}s)…", file=sys.stderr, flush=True)
        with PersonalApiAuthenticator(timeout=args.timeout) as authenticator:
            token = authenticator.obtain_token(resolve_api_key())
        with GarminPersonalApiClient(token.access_token, timeout=args.timeout) as client:
            print("Checking Garmin profile access…", file=sys.stderr, flush=True)
            client.get_user_profile_settings()
            print("Checking recent activity access…", file=sys.stderr, flush=True)
            activities = client.search_activities(start=0, limit=1)
    except (RequestTimeout, TimeoutError):
        print("Connection check timed out; check connectivity and retry later or adjust --timeout.", file=sys.stderr)
        return 1
    except Exception as error:  # noqa: BLE001 -- avoid exposing response bodies at the CLI boundary
        # Exception text can contain response bodies; expose only its type.
        print(f"Connection check failed ({type(error).__name__}).", file=sys.stderr)
        return 1
    finally:
        logging.disable(previous_log_level)

    print("Garmin Personal API authentication and read requests succeeded.")
    if isinstance(activities, list):
        print("A recent activity is available." if activities else "No recent activity was returned.")
    else:
        print("The activity search returned a response; its format requires inspection.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
