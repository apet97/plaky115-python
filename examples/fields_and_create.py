"""Create an item with typed field builders (dry-run by default)."""

import os

from plaky115 import PlakyClient, field_values, person_field, status_field, timeline_field


def main() -> None:
    with PlakyClient(api_key=os.environ["PLAKY_API_KEY"]) as plaky:
        plan = plaky.items.create(
            space_id=os.environ["PLAKY_SPACE_ID"],
            board_id=os.environ["PLAKY_BOARD_ID"],
            body={
                "title": "Example item",
                "fields": field_values(
                    {
                        "Status": status_field("To do"),
                        "Assignee": person_field(users=[1]),
                        "Timeline": timeline_field(
                            start="2026-01-01T00:00:00Z", end="2026-01-31T00:00:00Z"
                        ),
                    }
                ),
            },
            dry_run=True,  # remove to perform the single write
        )
        print(plan)


if __name__ == "__main__":
    main()
