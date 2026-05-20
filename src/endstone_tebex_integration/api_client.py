import requests
from typing import Optional, Dict, Any, List, Callable

from endstone_tebex_integration.tebex.models import (
    TebexDuePlayersInfo, TebexQueuedOnlineCommandsInfo,
    TebexQueuedOfflineCommandsInfo, TebexInformation
)

class TebexAPIError(Exception):
    def __init__(self, message: str, status_code: int = 0):
        self.status_code = status_code
        super().__init__(message)

class TebexAPIClient:
    BASE_URL = "https://plugin.tebex.io"
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self._session = requests.Session()
        self._session.headers.update({
            "X-Tebex-Secret": secret_key,
            "Content-Type": "application/json"
        })
        self._latency: float = 0.0

    def close(self) -> None:
        self._session.close()

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Any:
        import time
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"

        start_time = time.time()
        response = self._session.request(method, url, json=data)
        self._latency = time.time() - start_time

        if response.status_code == 204:
            return None

        json_response = response.json()

        if response.status_code != 200:
            error_msg = json_response.get("error_message", "Unknown error")
            raise TebexAPIError(error_msg, response.status_code)

        return json_response

    def get_information(self) -> Dict[str, Any]:
        return self._request("GET", "/information")

    def get_due_players(self) -> TebexDuePlayersInfo:
        result = self._request("GET", "/queue/due-player-list")
        return TebexDuePlayersInfo(**result)

    def get_queued_online_commands(self, player_id: int) -> TebexQueuedOnlineCommandsInfo:
        result = self._request("GET", f"/queue/online-commands/{player_id}")
        return TebexQueuedOnlineCommandsInfo(**result)

    def get_queued_offline_commands(self) -> TebexQueuedOfflineCommandsInfo:
        result = self._request("GET", "/queue/offline-commands")
        return TebexQueuedOfflineCommandsInfo(**result)

    def delete_commands(self, command_ids: List[int]) -> bool:
        if not command_ids:
            return True
        self._request("DELETE", "/queue", {"ids": command_ids})
        return True

    def get_latency(self) -> float:
        return self._latency