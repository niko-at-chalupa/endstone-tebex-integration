from endstone.command import CommandSender, Command
from abc import ABC
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from . import TebexIntegrationPlugin


class Subcommands(ABC):
    subcommand_map: dict[str, Callable[[CommandSender, Command, list[str]], bool]]


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

    def secret(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        if len(args) == 0:
            sender.send_error_message("Usage: /tebex secret <key>")
            return False

        secret_key = args[0]
        # Will call plugin.set_secret(secret_key)
        self.plugin.set_secret(secret_key, sender)
        return True

    def info(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        # Will call plugin.show_info(sender)
        self.plugin.show_tebex_info(sender)
        return True

    def refresh(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        # Will call plugin.refresh_commands(sender)
        self.plugin.refresh_commands(sender)
        return True

    def dropall(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        # Will call plugin.drop_all_commands(sender)
        self.plugin.drop_all_commands(sender)
        return True

    def __init__(self, plugin: 'TebexIntegrationPlugin'):
        self.plugin = plugin

        self.subcommand_map = {
            "help": self.help,
            "secret": self.secret,
            "info": self.info,
            "refresh": self.refresh,
            "dropall": self.dropall,
        }


class TebexAdminCommands(Subcommands):
    """Defines all admin subcommands for /tebexadmin"""

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

    def __init__(self, plugin: 'TebexIntegrationPlugin'):
        self.plugin = plugin

        self.subcommand_map = {
            "help": self.help,
        }