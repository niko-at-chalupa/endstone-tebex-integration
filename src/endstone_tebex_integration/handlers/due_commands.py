from typing import Optional, Dict, List
from time import time
from endstone import Server
from endstone.plugin import Plugin

from endstone_tebex_integration.tebex.models import (
    TebexDuePlayer, TebexQueuedOnlineCommand, TebexQueuedOfflineCommand,
    TebexDuePlayersInfo, TebexQueuedOnlineCommandsInfo, TebexQueuedOfflineCommandsInfo
)
from endstone_tebex_integration.api_client import TebexAPIClient, TebexAPIError
from endstone_tebex_integration.utils import TebexApiUtils
from endstone_tebex_integration.events import TebexExecuteOfflineCommandEvent
from endstone_tebex_integration.handlers.player_list import TebexDuePlayerList, TebexDuePlayerHolder
from endstone_tebex_integration.handlers.session import TebexPlayerSession


class DueCommandsHandler:
    """Handles both online and offline command queues from Tebex"""

    def __init__(self, plugin: Plugin, api_client: TebexAPIClient):
        self.plugin = plugin
        self.server: Server = plugin.server
        self.api = api_client
        self.logger = plugin.logger

        self._due_players_list = TebexDuePlayerList(self._on_player_match)
        self._pending_command_ids: List[int] = []
        self._batch_counter = 0
        self._is_idle = True

        # Start periodic check for offline commands
        check_interval = plugin.config.check_interval
        if check_interval > 0:
            self.server.scheduler.run_task(
                plugin,
                self._check_offline_commands,
                delay=check_interval * 20,
                period=check_interval * 20
            )

    def on_player_join(self, player: Player) -> None:
        self._due_players_list.on_player_join(player)
        self._schedule_due_players_check()

    def on_player_quit(self, player: Player) -> None:
        self._due_players_list.on_player_quit(player)

    def _schedule_due_players_check(self) -> None:
        """Schedule a check for due players if not already scheduled"""
        if not self._is_idle:
            return

        self._is_idle = False
        self._check_due_players()
        self._is_idle = True

    def _on_player_match(self, player, holder: TebexDuePlayerHolder) -> None:
        """Called when a player with pending commands joins"""
        session = self._due_players_list.get_online_player(player)
        if not session:
            return

        try:
            result = self.api.get_queued_online_commands(holder.player.id)
            self._on_online_commands_fetched(player, session, holder, result)
        except TebexAPIError as e:
            self.logger.error(f"Failed to fetch online commands: {e}")

    def _on_online_commands_fetched(self, player, session: TebexPlayerSession,
                                    holder: TebexDuePlayerHolder,
                                    result: TebexQueuedOnlineCommandsInfo) -> None:
        if not player.online:
            return

        commands = result.commands
        total_commands = len(commands)
        timestamp = time()

        for cmd in commands:
            command_str = session.execute_online_command(self.server, cmd, holder.player)
            if command_str is None:
                self.logger.warning(f"Failed to execute online command #{cmd.id}")
            else:
                self.queue_command_deletion(cmd.id)
                self.logger.info(f"Executed online command #{cmd.id}: {command_str}")

        # Check if all commands for this player are done
        if total_commands > 0:
            current_holder = self._due_players_list.get_tebex_awaiting_player(player)
            if current_holder and current_holder.created < timestamp:
                self._due_players_list.remove(current_holder)

    def _check_due_players(self) -> None:
        """Fetch due players from Tebex API"""
        try:
            result = self.api.get_due_players()
            self._on_due_players_fetched(result)
        except TebexAPIError as e:
            self.logger.error(f"Failed to fetch due players: {e}")

    def _on_due_players_fetched(self, result: TebexDuePlayersInfo) -> None:
        self._due_players_list.update(result.players)
        player_count = len(result.players)
        self.logger.debug(f"{player_count} player(s) are in the online commands queue")

    def _check_offline_commands(self) -> None:
        """Periodic check for offline commands"""
        try:
            result = self.api.get_queued_offline_commands()
            commands = result.commands
            self.logger.debug(f"Fetched {len(commands)} offline command(s)")
            for cmd in commands:
                self._execute_offline_command(cmd)
        except TebexAPIError as e:
            self.logger.error(f"Failed to fetch offline commands: {e}")

    def _execute_offline_command(self, command: TebexQueuedOfflineCommand) -> None:
        """Execute a single offline command"""
        delay = command.conditions.delay

        if delay > 0:
            # Schedule delayed execution
            self.server.scheduler.run_task(
                self.plugin,
                lambda: self._execute_offline_command_immediately(command),
                delay=delay * 20
            )
        else:
            self._execute_offline_command_immediately(command)

    def _execute_offline_command_immediately(self, command: TebexQueuedOfflineCommand) -> None:
        """Execute an offline command immediately"""
        original_placeholders = TebexApiUtils.offline_command_parameters(command.player)

        event = TebexExecuteOfflineCommandEvent(
            command.player, command,
            original_placeholders, original_placeholders.copy()
        )
        self.server.plugin_manager.call_event(event)

        if event.is_cancelled:
            return

        command_string = event.get_final_command()

        if not self.server.dispatch_command(self.server.command_sender, command_string):
            self.logger.warning(f"Failed to execute offline command: {command_string}")
            return

        self.queue_command_deletion(command.id)
        self.logger.info(f"Executed offline command #{command.id}: {command_string}")

    def queue_command_deletion(self, command_id: int) -> None:
        """Queue a command ID for batch deletion"""
        self._pending_command_ids.append(command_id)

        if len(self._pending_command_ids) == 1:
            # Schedule deletion in 1 tick
            self.server.scheduler.run_task(
                self.plugin,
                self._delete_pending_commands,
                delay=1
            )

    def _delete_pending_commands(self) -> None:
        """Delete all queued command IDs in a batch"""
        if not self._pending_command_ids:
            return

        command_ids = self._pending_command_ids.copy()
        self._pending_command_ids.clear()
        self._batch_counter += 1

        self.logger.info(f"Executing pending command deletion batch #{self._batch_counter} "
                         f"consisting of: ({len(command_ids)}) {command_ids}")

        try:
            self.api.delete_commands(command_ids)
            self.logger.info(f"Successfully executed pending command deletion batch #{self._batch_counter}")
        except TebexAPIError as e:
            self.logger.info(f"Failed to execute pending command deletion batch #{self._batch_counter} "
                             f"due to: {e}, queueing into next batch")
            for cid in command_ids:
                self.queue_command_deletion(cid)

    def refresh(self) -> None:
        """Manually refresh both online and offline queues"""
        try:
            # Fetch offline commands
            offline_result = self.api.get_queued_offline_commands()
            self.logger.info(f"Refreshed offline commands: {len(offline_result.commands)} commands")
        except TebexAPIError as e:
            self.logger.error(f"Failed to refresh offline commands: {e}")

        # Trigger online check
        self._check_due_players()
        self.logger.info("Online commands refresh triggered")

    def mark_all_as_executed(self) -> int:
        """Mark all queued commands as executed (drop them)"""
        marked = 0

        # Process offline commands
        try:
            offline_result = self.api.get_queued_offline_commands()
            for cmd in offline_result.commands:
                self.queue_command_deletion(cmd.id)
                marked += 1
        except TebexAPIError as e:
            self.logger.error(f"Failed to fetch offline commands for dropall: {e}")

        # Process online commands
        try:
            due_players = self.api.get_due_players()
            for player in due_players.players:
                try:
                    online_result = self.api.get_queued_online_commands(player.id)
                    for cmd in online_result.commands:
                        self.queue_command_deletion(cmd.id)
                        marked += 1
                except TebexAPIError as e:
                    self.logger.error(f"Failed to fetch online commands for player {player.id}: {e}")
        except TebexAPIError as e:
            self.logger.error(f"Failed to fetch due players for dropall: {e}")

        return marked

    def shutdown(self) -> None:
        """Clean up on plugin disable"""
        self._delete_pending_commands()