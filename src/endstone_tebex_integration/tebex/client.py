from __future__ import annotations
from typing import List
import aiohttp
from . import (
    TebexInformation,
    TebexDuePlayersInfo,
    TebexQueuedOnlineCommandsInfo,
    TebexQueuedOfflineCommandsInfo,
)


class TebexClient:
    BASE_URL = "https://plugin.tebex.io"

    def __init__(self, secret: str) -> None:
        self.secret = secret
        self._session: aiohttp.ClientSession | None = None

    def _headers(self) -> dict:
        return {
            "X-Tebex-Secret": self.secret,
            "Accept": "application/json",
        }

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get(self, endpoint: str) -> dict:
        session = await self._ensure_session()
        async with session.get(
            f"{self.BASE_URL}{endpoint}",
            headers=self._headers(),
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def _delete(self, endpoint: str, json: dict) -> None:
        session = await self._ensure_session()
        async with session.delete(
            f"{self.BASE_URL}{endpoint}",
            headers=self._headers(),
            json=json,
        ) as response:
            response.raise_for_status()

    async def get_information(self) -> TebexInformation:
        data = await self._get("/information")
        return TebexInformation(**data)

    async def get_due_players(self) -> TebexDuePlayersInfo:
        data = await self._get("/queue")
        return TebexDuePlayersInfo(**data)

    async def get_online_commands(self, player_id: int) -> TebexQueuedOnlineCommandsInfo:
        data = await self._get(f"/queue/online-commands/{player_id}")
        return TebexQueuedOnlineCommandsInfo(**data)

    async def get_offline_commands(self) -> TebexQueuedOfflineCommandsInfo:
        data = await self._get("/queue/offline-commands")
        return TebexQueuedOfflineCommandsInfo(**data)

    async def delete_commands(self, command_ids: List[int]) -> None:
        await self._delete("/queue", {"ids": command_ids})

    async def get_listing(self) -> dict:
        return await self._get("/listing")

    async def get_payment(self, transaction_id: str) -> dict:
        return await self._get(f"/payments/{transaction_id}")

    async def get_package(self, package_id: int) -> dict:
        return await self._get(f"/package/{package_id}")

    async def get_all_payments(self) -> dict:
        return await self._get("/payments")

    async def delete_offline_commands(self, command_ids: List[int]) -> None:
        await self._delete("/queue", {"ids": command_ids})