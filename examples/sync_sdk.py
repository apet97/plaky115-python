"""Sync SDK quick start. Set PLAKY_API_KEY in the environment."""

import os

from plaky115 import PlakyClient


def main() -> None:
    with PlakyClient(api_key=os.environ["PLAKY_API_KEY"]) as plaky:
        for space in plaky.spaces.iterate(page_size=100):
            print(space.id, space.title)


if __name__ == "__main__":
    main()
