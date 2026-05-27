from __future__ import annotations
import logging
from typing import TYPE_CHECKING
from endstone import Server, Logger
from .tebex import TebexClient
from endstone.asyncio import submit, get_loop

if TYPE_CHECKING:
    from .main import TebexIntegrationPlugin

class TebexExecutor:
    def __init__(self, plugin: 'TebexIntegrationPlugin') -> None:
        self.plugin = plugin

        self.server.scheduler.run_task(self.plugin, self._routine, period=20*self.plugin.config.check_interval)

    @property
    def server(self):
        return self.plugin.server

    @property
    def logger(self):
        return self.plugin.logger
    
    @property
    def client(self):
        return self.plugin.tebex_client

    def _routine(self):
        """Runs for every time the check interval hits."""

        online_player_ids = []
        for player in self.server.online_players:
            online_player_ids.append(player.xuid)
        submit(self.run(online_player_ids))

    async def run(self, online_player_xuids: list[int]) -> None:
        due = await self.client.get_due_players()
        online_set = set(online_player_xuids)
        executed: list[int] = []

        for player in due.players:
            if player.uuid not in online_set:
                continue
            
            try:
                in_game_player = self.server.get_player(player.name)
            except Exception: # Don't know what this would raise
                self.logger.error(f"Error while getting player {player.name}")
                continue

            queue_info = await self.client.get_online_commands(player.id)
            for cmd in queue_info.commands:
                try:
                    self.logger.info(f"--- Executing command {cmd.command} for online command {cmd.id} ---")
                    def dispatch_command():
                        self.server.dispatch_command(self.server.command_sender, cmd.command)
                    self.plugin.server.scheduler.run_task(self.plugin, dispatch_command)
                    executed.append(cmd.id)
                except Exception as e:
                    self.logger.error(f"Online command {cmd.id} failed: {e}")

        if executed:
            await self.client.delete_commands(executed)