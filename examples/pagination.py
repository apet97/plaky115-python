"""Pagination: iterators, first_page, and bounded list_all."""

import os

from plaky115 import PlakyClient


def main() -> None:
    with PlakyClient(api_key=os.environ["PLAKY_API_KEY"]) as plaky:
        iterator = plaky.spaces.iterate(page_size=100, limit=250)
        first = iterator.first_page()
        print("first page:", len(first.data), "hasMore:", first.has_more)
        for space in iterator:
            print(space.id, space.title)


if __name__ == "__main__":
    main()
