from endstone.event import Event, Cancellable
from endstone import Player
from typing import Dict
from endstone_tebex_integration.tebex.models import TebexDuePlayer, TebexQueuedOnlineCommand, TebexQueuedOfflineCommand

class TebexExecuteOnlineCommandEvent(Event, Cancellable):
    """Called before executing an online command from Tebex queue"""

    def __init__(
            self,
            player: Player,
            due_player: TebexDuePlayer,
            command: TebexQueuedOnlineCommand,
            original_placeholders: Dict[str, str],
            placeholders: Dict[str, str]
    ):
        super().__init__()
        self._player = player
        self._due_player = due_player
        self._command = command
        self._original_placeholders = original_placeholders
        self._placeholders = placeholders

    @property
    def player(self) -> Player:
        return self._player

    @property
    def due_player(self) -> TebexDuePlayer:
        return self._due_player

    @property
    def command(self):
        return self._command

    @property
    def original_placeholders(self) -> Dict[str, str]:
        return self._original_placeholders

    @property
    def placeholders(self) -> Dict[str, str]:
        return self._placeholders

    @placeholders.setter
    def placeholders(self, value: Dict[str, str]) -> None:
        self._placeholders = value

    def get_final_command(self) -> str:
        command_str = self._command.command.as_raw_string()
        for placeholder, value in self._placeholders.items():
            command_str = command_str.replace(placeholder, value)
        return command_str


class TebexExecuteOfflineCommandEvent(Event, Cancellable):
    """Called before executing an offline command from Tebex queue"""

    def __init__(
            self,
            due_player: TebexDuePlayer,
            command: TebexQueuedOfflineCommand,
            original_placeholders: Dict[str, str],
            placeholders: Dict[str, str]
    ):
        super().__init__()
        self._due_player = due_player
        self._command = command
        self._original_placeholders = original_placeholders
        self._placeholders = placeholders

    @property
    def due_player(self) -> TebexDuePlayer:
        return self._due_player

    @property
    def command(self):
        return self._command

    @property
    def original_placeholders(self) -> Dict[str, str]:
        return self._original_placeholders

    @property
    def placeholders(self) -> Dict[str, str]:
        return self._placeholders

    @placeholders.setter
    def placeholders(self, value: Dict[str, str]) -> None:
        self._placeholders = value

    def get_final_command(self) -> str:
        command_str = self._command.command.as_raw_string()
        for placeholder, value in self._placeholders.items():
            command_str = command_str.replace(placeholder, value)
        return command_str