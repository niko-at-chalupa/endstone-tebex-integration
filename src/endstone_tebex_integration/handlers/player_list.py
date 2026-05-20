from typing import Dict, Optional, Callable
from endstone import Player

from endstone_tebex_integration.tebex.models import TebexDuePlayer
from endstone_tebex_integration.handlers.session import TebexPlayerSession


class TebexDuePlayerHolder:
    """Holds pending player data from Tebex queue"""

    def __init__(self, player: TebexDuePlayer):
        self.player = player
        self.created = __import__("time").time()


class TebexDuePlayerList:
    """Manages list of players with pending online commands"""

    def __init__(self, on_match: Callable[[Player, TebexDuePlayerHolder], None]):
        self._on_match = on_match
        self._tebex_due_players_by_id: Dict[int, TebexDuePlayerHolder] = {}
        self._tebex_due_players_by_xuid: Dict[str, int] = {}
        self._online_players: Dict[str, TebexPlayerSession] = {}

    def _get_player_index(self, player: Player) -> str:
        """Get index key for a player (XUID or name)"""
        # Use XUID as primary index, fallback to name if XUID empty (should not happen in online-mode)
        return player.xuid if player.xuid else player.name

    def _get_tebex_index(self, due_player: TebexDuePlayer) -> str:
        """Get index key for a TebexDuePlayer (XUID or name)"""
        return due_player.uuid if due_player.uuid else due_player.name

    def on_player_join(self, player: Player) -> None:
        """Called when a player joins the server"""
        index = self._get_player_index(player)
        self._online_players[index] = TebexPlayerSession(player)

        holder = self.get_tebex_awaiting_player(player)
        if holder is not None:
            self._on_match(player, holder)

    def on_player_quit(self, player: Player) -> None:
        """Called when a player leaves the server"""
        index = self._get_player_index(player)
        if index in self._online_players:
            self._online_players[index].destroy()
            del self._online_players[index]

    def get_all(self) -> Dict[int, TebexDuePlayerHolder]:
        """Get all pending due players"""
        return self._tebex_due_players_by_id

    def update(self, due_players: list[TebexDuePlayer]) -> None:
        """Update the list of pending players from Tebex API"""
        self._tebex_due_players_by_id.clear()
        self._tebex_due_players_by_xuid.clear()

        for player in due_players:
            holder = TebexDuePlayerHolder(player)
            self._tebex_due_players_by_id[player.id] = holder

            index = self._get_tebex_index(player)
            self._tebex_due_players_by_xuid[index] = player.id

            # Check if this player is currently online
            if index in self._online_players:
                self._on_match(self._online_players[index].get_player(), holder)

    def remove(self, holder: TebexDuePlayerHolder) -> None:
        """Remove a player from the pending list after commands are executed"""
        player = holder.player
        if player.id in self._tebex_due_players_by_id:
            del self._tebex_due_players_by_id[player.id]

        index = self._get_tebex_index(player)
        if index in self._tebex_due_players_by_xuid:
            del self._tebex_due_players_by_xuid[index]

    def get_tebex_awaiting_player(self, player: Player) -> Optional[TebexDuePlayerHolder]:
        """Get the pending player data for an online player if they have commands waiting"""
        index = self._get_player_index(player)
        if index in self._tebex_due_players_by_xuid:
            player_id = self._tebex_due_players_by_xuid[index]
            return self._tebex_due_players_by_id.get(player_id)
        return None

    def get_online_player(self, player: Player) -> Optional[TebexPlayerSession]:
        """Get the session for an online player"""
        index = self._get_player_index(player)
        return self._online_players.get(index)