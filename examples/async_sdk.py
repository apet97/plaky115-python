"""Async SDK quick start. Set PLAKY_API_KEY in the environment."""

import asyncio
import os

from plaky115 import AsyncPlakyClient


async def main() -> None:
    async with AsyncPlakyClient(api_key=os.environ["PLAKY_API_KEY"]) as plaky:
        page = await plaky.spaces.list(page_size=50)
        for space in page.data:
            print(space.id, space.title)


if __name__ == "__main__":
    asyncio.run(main())
