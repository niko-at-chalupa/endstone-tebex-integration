from endstone import Player
from endstone.command import CommandSender, Command
from abc import ABC
from typing import Callable, Any, TYPE_CHECKING
from .tebex import TebexClient
from endstone.asyncio import submit, get_loop
from .etc import give_player_qr_code_map
import json

if TYPE_CHECKING:
    from . import TebexIntegrationPlugin
    from .main import TebexConfig

# For each method that a subcommand maps to, please have args be [1:] (i.e., everything after the first item)
# instead of just the args that on_command gives you. Thank you!

class Subcommands(ABC):
    # def a_function(self, sender: CommandSender, command: Command, args: list[str]) -> bool: ...
    # { "a": self.a_function }
    # ^ this is what we're asking for (the dict)
    # This should also accept unbound methods (methods that aren't object.method, but rather method(object)), but
    # we won't be using unbound methods anyways so it doesn't matter
    subcommand_map: dict[str, Callable[[CommandSender, Command, list[str]], bool]]
    tebex_client: TebexClient
    plugin: 'TebexIntegrationPlugin'

    @property
    def config(self) -> 'TebexConfig':
        return self.plugin.config

class TebexCommands(Subcommands):
    """Defines all general subcommands for /tebex"""

    def help(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        messages = self.plugin.config.messages
        help_messages = self.plugin.config.help

        sender.send_message(self.plugin.config.messages.get("help_header", ""))
        for subcommand in self.subcommand_map:
            if subcommand in help_messages:
                description = help_messages.get(subcommand)
            else:
                description = "[no description]"
            sender.send_message(f"{subcommand} - {description}")

        return True

    def info(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        async def _run():
            info = await self.tebex_client.get_information()
            store_line = self.config.commands.get("info", {}).get("store", "Store: [store_name]")
            currency_line = self.config.commands.get("info", {}).get("currency", "Currency: [currency]")
            domain_line = self.config.commands.get("info", {}).get("domain", "URL: [domain]")

            def send_everything():
                sender.send_message(self.config.commands.get("info", {}).get("header", "--- Info ---"))
                sender.send_message(store_line.replace("[store_name]", info.account.name))
                sender.send_message(currency_line.replace("[currency]", info.account.currency.get("iso_4217", "N/A")))
                sender.send_message(domain_line.replace("[domain]", info.account.domain))
            self.plugin.server.scheduler.run_task(self.plugin, send_everything)
        submit(_run())
        return True

    def store(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        async def _run():
            info = await self.tebex_client.get_information()
            
            def send_everything():
                sender.send_message(info.account.domain)
            self.plugin.server.scheduler.run_task(self.plugin, send_everything)

            if isinstance(sender, Player) and self.config.commands.get("store", {}).get("qr_codes", True):
                await give_player_qr_code_map(self.plugin, info.account.domain, sender)
            
        submit(_run())
        return True

    def __init__(self, plugin: 'TebexIntegrationPlugin', tebex_client: TebexClient):
        self.plugin = plugin
        self.tebex_client = tebex_client

        self.subcommand_map = {
            "help": self.help,
            "info": self.info,
            "store": self.store,
        }

class TebexAdminCommands(Subcommands):
    """Defines all general subcommands for /tebexadmin"""

    def help(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        messages = self.plugin.config.messages
        help_messages = self.plugin.config.help_admin

        sender.send_message(self.plugin.config.messages.get("help_header", ""))
        for subcommand in self.subcommand_map:
            if subcommand in help_messages:
                description = help_messages.get(subcommand)
            else:
                description = "[no description]"
            sender.send_message(f"{subcommand} - {description}")

        return True

    def debug(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        if not args:
            sender.send_message("§cUsage: /tebexadmin debug <player_name>")
            return False
            
        target_name = args[0]
        
        async def _debug_async():
            try:
                due = await self.tebex_client.get_due_players()
                player = next((p for p in due.players if p.name == target_name), None)
                
                if not player:
                    def send_not_found():
                        sender.send_message(f"Player {target_name} is not in the due-players queue.")
                    self.plugin.server.scheduler.run_task(self.plugin, send_not_found)
                    return

                online_info = await self.tebex_client.get_online_commands(player.id)
                
                debug_dump = {
                    "player_info": player.model_dump(),
                    "online_queue": online_info.model_dump(),
                }
                
                dump_str = json.dumps(debug_dump, indent=2)

                def send_everything():
                    sender.send_message(f"Debug data for {target_name} has been dumped to the server console!")
                    self.plugin.logger.info(f"DEBUG DUMP for {target_name}:\n{dump_str}")
                self.plugin.server.scheduler.run_task(self.plugin, send_everything)
                
            except Exception as e:
                error_msg = str(e) 
                self.plugin.logger.error(f"Async debug task failed for {target_name}: {error_msg}")

        submit(_debug_async())
        sender.send_message("Worked!!")
        return True

    def fulfill(self, sender: CommandSender, command: Command, args: list[str]) -> bool:        
        async def _fulfill_async():
            try:
                online_player_ids = []
                for player in self.plugin.server.online_players:
                    online_player_ids.append(player.xuid)
                submit(self.plugin.tebex_executor.run(online_player_ids))
            except Exception as e:
                error_msg = str(e) 
                self.plugin.logger.error(f"Async fulfill task failed: {error_msg}")

        submit(_fulfill_async())
        sender.send_message("Worked!!")
        return True
        
    def __init__(self, plugin: 'TebexIntegrationPlugin', tebex_client: TebexClient):
        self.plugin = plugin
        self.tebex_client = tebex_client

        self.subcommand_map = {
            "help": self.help,
            "debug": self.debug,
            "fulfill": self.fulfill,
        }