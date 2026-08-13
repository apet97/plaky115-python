"""Typed error handling: statuses, retries, and rate limits."""

import os

from plaky115 import PlakyClient, PlakyNotFoundError, PlakyRateLimitError


def main() -> None:
    with PlakyClient(api_key=os.environ["PLAKY_API_KEY"]) as plaky:
        try:
            plaky.spaces.get("999999999")
        except PlakyNotFoundError as error:
            print("not found:", error.status, error.request_id)
        except PlakyRateLimitError as error:
            print("throttled; retry after ms:", error.retry_after_ms)
        print("estimated remaining:", plaky.rate_limit.estimated_remaining())


if __name__ == "__main__":
    main()
