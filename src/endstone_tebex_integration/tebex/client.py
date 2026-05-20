from __future__ import annotations
from typing import List
import aiohttp
from . import Account, Package, Category


class TebexClient:
    BASE_URL = "https://headless.tebex.io/api"

    def __init__(self, secret: str) -> None:
        self.secret = secret

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.secret}",
            "Accept": "application/json",
        }

    async def _get(self, endpoint: str) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.BASE_URL}{endpoint}",
                headers=self._headers(),
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def get_account(self) -> Account:
        data = await self._get("/accounts")
        return Account(**data["data"])

    async def get_packages(self) -> List[Package]:
        data = await self._get("/packages")
        return [Package(**pkg) for pkg in data["data"]]

    async def get_package(self, package_id: int) -> Package:
        data = await self._get(f"/packages/{package_id}")
        return Package(**data["data"])

    async def get_categories(self, include_packages: bool = False) -> List[Category]:
        endpoint = "/categories"
        if include_packages:
            endpoint += "?includePackages=1"
        data = await self._get(endpoint)
        return [Category(**cat) for cat in data["data"]]

    async def get_category(self, category_id: int, include_packages: bool = False) -> Category:
        endpoint = f"/categories/{category_id}"
        if include_packages:
            endpoint += "?includePackages=1"
        data = await self._get(endpoint)
        return Category(**data["data"])

    async def get_packages_in_category(self, category_id: int) -> List[Package]:
        category = await self.get_category(category_id, include_packages=True)
        return category.packages