from typing import Dict, Optional
from time import time
from endstone import Player
from endstone import Server

from endstone_tebex_integration.tebex.models import TebexDuePlayer, TebexQueuedOnlineCommand
from endstone_tebex_integration.utils import TebexApiUtils
from endstone_tebex_integration.events import TebexExecuteOnlineCommandEvent


class DelayedOnlineCommandHandler:
    """Handles delayed command execution"""
    def __init__(self, command: TebexQueuedOnlineCommand, task_id: int):
        self.command = command
        self.task_id = task_id


class TebexPlayerSession:
    """Manages online player's command execution"""
    def __init__(self, player: Player):
        self._player = player
        self._delayed_handlers: Dict[int, DelayedOnlineCommandHandler] = {}

    def get_player(self) -> Player:
        return self._player

    def destroy(self) -> None:
        """Cancel all pending delayed commands for this player"""
        server = self._player.server
        for handler in self._delayed_handlers.values():
            server.scheduler.cancel_task(handler.task_id)
        self._delayed_handlers.clear()

    def _check_inventory_slots(self, required_slots: int) -> bool:
        """Check if player has enough free inventory slots"""
        if required_slots <= 0:
            return True

        inventory = self._player.inventory
        free_slots = inventory.get_size() - len(inventory.get_contents())
        return free_slots >= required_slots

    def _execute_online_command_immediately(
            self,
            server: Server,
            due_player: TebexDuePlayer,
            command: TebexQueuedOnlineCommand
    ) -> Optional[str]:
        """Execute a command immediately, returns command string if successful"""
        conditions = command.conditions

        # Check inventory slots
        if not self._check_inventory_slots(conditions.slots):
            return None

        # Prepare placeholders
        original_placeholders = TebexApiUtils.online_command_parameters(self._player, due_player)

        # Create and call event
        event = TebexExecuteOnlineCommandEvent(
            self._player, due_player, command,
            original_placeholders, original_placeholders.copy()
        )
        server.plugin_manager.call_event(event)

        if event.is_cancelled:
            return None

        command_string = event.get_final_command()

        # Dispatch command using console sender
        if not server.dispatch_command(server.command_sender, command_string):
            return None

        return command_string

    def execute_online_command(
            self,
            server: Server,
            command: TebexQueuedOnlineCommand,
            due_player: TebexDuePlayer
    ) -> Optional[str]:
        """Execute an online command, returns command string if executed immediately"""
        delay = command.conditions.delay

        if delay > 0:
            # Schedule delayed execution
            if command.id in self._delayed_handlers:
                return None

            task = server.scheduler.run_task(
                server.plugin_manager.get_plugin("endstone_tebex_integration"),
                lambda: self._execute_delayed_command(server, due_player, command),
                delay * 20
            )
            self._delayed_handlers[command.id] = DelayedOnlineCommandHandler(command, task.task_id)
            return None  # Command scheduled for later
        else:
            # Execute immediately
            return self._execute_online_command_immediately(server, due_player, command)

    def _execute_delayed_command(
            self,
            server: Server,
            due_player: TebexDuePlayer,
            command: TebexQueuedOnlineCommand
    ) -> None:
        """Execute a delayed command and clean up"""
        self._execute_online_command_immediately(server, due_player, command)
        if command.id in self._delayed_handlers:
            del self._delayed_handlers[command.id]