from __future__ import annotations
import logging
from typing import TYPE_CHECKING
from endstone import Server, Logger
from .tebex import TebexClient
from endstone.asyncio import submit, get_loop

if TYPE_CHECKING:
    from .main import TebexIntegrationPlugin

class TebexExecutor:
    def __init__(self, client: TebexClient, server: Server, logger: Logger, plugin: 'TebexIntegrationPlugin') -> None:
        self.client = client
        self.server = server
        self.logger = logger
        self.plugin = plugin

        self.server.scheduler.run_task(self.plugin, self._routine, period=20*self.plugin.config.check_interval)

    def _routine(self):
        """Runs for every time the check interval hits."""

        online_player_ids = []
        for player in self.server.online_players:
            # Is the xuid correct? Who knows.
            online_player_ids.append(player.xuid)
        submit(self.run(online_player_ids))

    async def run(self, online_player_ids: list[int]) -> None:
        due = await self.client.get_due_players()
        online_set = set(online_player_ids)
        executed: list[int] = []

        for player in due.players:
            if player.id not in online_set:
                continue
            
            try:
                in_game_player = self.server.get_player(player.name)
            except Exception: # Don't know what this would raise
                self.logger.error(f"Error while handling ")
                continue

            queue_info = await self.client.get_online_commands(player.id)
            for cmd in queue_info.commands:
                try:
                    # Executing as the player so we can do stuff like `setblock ~ ~ ~ ...` or some bogus
                    # like that. I'm unsure of how offline commands work.
                    self.server.dispatch_command(in_game_player, cmd.command.command)
                    executed.append(cmd.id)
                except Exception as e:
                    self.logger.error(f"Online command {cmd.id} failed: {e}")

        if executed:
            # Scary!!
            await self.client.delete_commands(executed)