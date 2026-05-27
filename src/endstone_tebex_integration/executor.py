from __future__ import annotations
from endstone.scheduler import Scheduler
import sched
import logging
from typing import TYPE_CHECKING
from endstone import Server, Logger, Player
from .tebex import TebexClient, TebexQueuedOnlineCommandsInfo
from endstone.asyncio import submit, get_loop
from .etc import get_free_slots
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from .main import TebexIntegrationPlugin

class Executor(ABC):
    def __init__(self, plugin: 'TebexIntegrationPlugin') -> None:
        self.plugin = plugin

    delay: int

    @property
    def server(self) -> Server:
        return self.plugin.server

    @property
    def logger(self) -> Logger:
        return self.plugin.logger
    
    @property
    def client(self) -> TebexClient:
        if self.plugin.tebex_client:
            return self.plugin.tebex_client
        else:
            # Unreachable
            raise RuntimeError

    def _handle_future_result(self, future) -> None:
        try:
            future.result()
        except Exception as e:
            self.logger.error(str(e))
            
    @abstractmethod
    def routine(self):
        """Called by the main executor's routine."""
        ...

class OnlinePackagesExecutor(Executor):
    delay = 0

    def routine(self):
        online_player_ids = []
        for player in self.server.online_players:
            online_player_ids.append(player.xuid)

        run = submit(self.run(online_player_ids))
        run.add_done_callback(self._handle_future_result)

    async def run(self, online_player_xuids: list[int]):
        try:
            due = await self.client.get_due_players()
        except Exception as e:
            self.logger.error(f"Failed to fetch due players from Tebex: {e}")
            return

        online_set = set(online_player_xuids)
        
        for player in due.players:
            if player.uuid not in online_set:
                continue
            
            try:
                in_game_player = self.server.get_player(player.name)
                if not in_game_player:
                    continue
            except Exception as e:
                self.logger.error(f"Error while getting player {player.name}: {e}")
                continue

            process_player_packages = submit(self.process_player_packages(in_game_player, player.id))
            process_player_packages.add_done_callback(self._handle_future_result)

    async def process_player_packages(self, in_game_player: Player, tebex_player_id: int):
        try:
            queue_info: TebexQueuedOnlineCommandsInfo = await self.client.get_online_commands(tebex_player_id)
        except Exception as e:
            self.logger.error(f"Failed to fetch commands for player {in_game_player.name}: {e}")
            return

        total_required_slots = sum(cmd.conditions.slots for cmd in queue_info.commands)
        self.logger.debug(f"Total required slots for {in_game_player.name}: {total_required_slots}")

        if total_required_slots > 0:
            def check_and_dispatch():
                empty_slots = 0
                inventory = in_game_player.inventory
                for slot in range(inventory.size):
                    item = inventory.get_item(slot)
                    if item is None:
                        empty_slots += 1
                
                self.verify_and_dispatch(in_game_player, queue_info, empty_slots, total_required_slots)

            self.server.scheduler.run_task(self.plugin, check_and_dispatch)
        else:
            self.server.scheduler.run_task(self.plugin, lambda: self.verify_and_dispatch(in_game_player, queue_info, 0, 0))

    def verify_and_dispatch(self, in_game_player: Player, queue_info: TebexQueuedOnlineCommandsInfo, empty_slots: int, total_required_slots: int) -> None:
        if empty_slots < total_required_slots:
            in_game_player.send_message(self.plugin.config.messages.get("inventory_too_full", "inventory too full").replace("[slots_left]", str(total_required_slots)))
            return

        executed = []
        for cmd in queue_info.commands:
            try:
                resolved_cmd = cmd.command.replace("{username}", in_game_player.name).replace("{name}", in_game_player.name).replace("{player}", in_game_player.name).replace("{id}", str(in_game_player.unique_id))
                self.logger.info(f"--- Executing command {resolved_cmd} for online command {cmd.id} ---")
                if self.server.dispatch_command(self.server.command_sender, resolved_cmd):
                    executed.append(cmd.id)
            except Exception as e:
                self.logger.error(f"Online command {cmd.id} failed: {e}")

        if executed:
            delete_commands = submit(self.client.delete_commands(executed))
            delete_commands.add_done_callback(self._handle_future_result)

class ExecutorScheduler:
    def __init__(self, plugin: 'TebexIntegrationPlugin') -> None:
        self.plugin = plugin

        self.executors: list[Executor] = [
            OnlinePackagesExecutor(self.plugin)
        ]

        self.scheduler.run_task(self.plugin, self.routine, period=20*self.plugin.config.check_interval)

    @property
    def scheduler(self) -> Scheduler:
        return self.plugin.server.scheduler

    def routine(self):
        """Runs for every time the check interval hits."""
        
        for executor in self.executors:
            self.scheduler.run_task(self.plugin, executor.routine, delay=executor.delay)