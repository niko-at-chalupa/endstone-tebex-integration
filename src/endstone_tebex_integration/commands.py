from endstone.command import CommandSender, Command
from abc import ABC
from typing import Callable, Any, TYPE_CHECKING
from .tebex import TebexClient

if TYPE_CHECKING:
    from . import TebexIntegrationPlugin

# For each method that a subcommand maps to, please have args be [1:] (i.e., everything after the first item)
# instead of just the args that on_command gives you. Thank you!

class Subcommands(ABC):
    # def a_function(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
    # { "a": self.a_function }
    # ^ this is what we're asking for (the dict)
    # This should also accept unbound methods (methods that aren't object.method, but rather method(object)), but
    # we won't be using unbount methods anyways so it doesn't matter
    subcommand_map: dict[str, Callable[[CommandSender, Command, list[str]], bool]]
    tebex_client: TebexClient

class TebexCommands(Subcommands):
    """Defines all general subcommands for /tebex"""

    def help(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        messages = self.plugin.config.messages
        help_messages = self.plugin.config.help

        for subcommand in self.subcommand_map:
            if subcommand in help_messages:
                description = help_messages.get(subcommand)
            else:
                description = "[no description]"
            sender.send_message(f"{subcommand} - {description}")

        return True

    def info(self, sender: CommandSender, command: Command, args: list[str]):
        pass

    def __init__(self, plugin: 'TebexIntegrationPlugin', tebex_client: TebexClient):
        self.plugin = plugin
        self.tebex_client = tebex_client

        self.subcommand_map = {
            "help": self.help,
        }

class TebexAdminCommands(Subcommands):
    """Defines all general subcommands for /tebexadmin"""

    def help(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        messages = self.plugin.config.messages
        help_messages = self.plugin.config.help_admin

        for subcommand in self.subcommand_map:
            if subcommand in help_messages:
                description = help_messages.get(subcommand)
            else:
                description = "[no description]"
            sender.send_message(f"{subcommand} - {description}")

        return True
    
    def refresh(self, sender: CommandSender, command: Command, args: list[str]):
        pass

    def dropall(self, sender: CommandSender, command: Command, args: list[str]):
        pass

    def __init__(self, plugin: 'TebexIntegrationPlugin', tebex_client: TebexClient):
        self.plugin = plugin
        self.tebex_client = tebex_client

        self.subcommand_map = {
            "help": self.help,
        }