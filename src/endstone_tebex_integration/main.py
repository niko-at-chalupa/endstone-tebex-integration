from endstone.asyncio import submit
from endstone import Player
from click.decorators import T
from pathlib import Path
from typing import Any, cast
from endstone.plugin import Plugin
from endstone.command import CommandSender, Command
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from pydantic import BaseModel, Field
from .commands import TebexCommands, TebexAdminCommands, TebexClient
from .executor import TebexExecutor
from endstone.event import event_handler, PlayerJoinEvent

class TebexConfig(BaseModel):
    secret_key: str = ""
    webhook_secret: str = ""
    check_interval: int = 60
    messages: dict[str, str] = Field(default_factory=dict)
    help: dict[str, str] = Field(default_factory=dict)
    help_admin: dict[str, str] = Field(default_factory=dict)
    commands: dict[str, dict[str, Any]]

class TebexIntegrationPlugin(Plugin):
    api_version = "0.11"
    config: TebexConfig

    commands = {
        "tebex": {
            "description": "General Tebex commands.",
            "usages": [
                "/tebex <subcommand: string> [args: message]", 
                "/tebex help",
                "/tebex info",
                "/tebex store",
            ], # please make sure this mirrors subcommands in commands.py
            "permissions": ["tebex_integration.command.general"],
        },
        
        "tebexadmin": {
            "description": "Administrative commands for Tebex.",
            "usages": [
                "/tebexadmin <subcommand: string> [args: message]",
                "/tebexadmin help",
                "/tebexadmin debug",
                "/tebexadmin fulfill",
            ], # please make sure this mirrors subcommands in commands.py
            "permissions": ["tebex_integration.command.admin"],
        }
    }

    permissions = {
        "tebex_integration.command.general": {
            "description": "Allow users to access basic tebex commands.",
            "default": True, 
        },

        "tebex_integration.command.admin": {
            "description": "Allow users to access administrative tebex commands.",
            "default": "op", 
        }
    }

    def on_enable(self) -> None:
        self._config: TebexConfig = self._load_config()
        self.register_events(self)
        self.logger.info("Tebex Integration Plugin enabled.")

        #if self.server.online_mode == False:
            #self.logger.warning("*" * 60)
            #self.logger.warning("online-mode is set to FALSE!!!!")
            #self.logger.warning("Player XUIDs can't be verified!!!! Payments can be FAKED!!!!!!!")
            #self.logger.warning("It is highly recommended to enable online-mode in server.properties.")
            #self.logger.warning("*" * 60)
            
            # ~~We will use usernames instead. Uncessessary!~~
            # We might not? Looks like XUIDs work fine, and are likely better.

        if not self.config.secret_key:
            self.active = False
            self.logger.error("There is no secret key set in config. Please set it and then reload the plugin, or run tebex secret <secret> in this console.")
            return

        self.tebex_client = TebexClient(self.config.secret_key)

        self.tebex_subcommands = TebexCommands(self, self.tebex_client)
        self.tebex_admin_subcommands = TebexAdminCommands(self, self.tebex_client)

        self.tebex_executor = TebexExecutor(self)

        self.active = True

        self.logger.info("If you want to reset the config, delete it and reload the plugin.")

    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        if command.name == "tebex" and len(args) > 0 and args[0] == "secret":
            if sender != self.server.command_sender:
                # Here, we lie and tell non-server console senders that the subcommand is invalid.
                # /tebex secret will only work in the server console.
                sender.send_error_message(self.config.messages.get("invalid_subcommand", "invalid subcommand"))
                return False

            if len(args) < 2:
                sender.send_error_message("Usage: /tebex secret <key>")
                return False

            self._save_secret_key(args[1])
            sender.send_message("Tebex secret key has been updated and saved to config.yml.")
            self.active = True
            return True

        if not self.active:
            sender.send_error_message(self.config.messages.get("generic_error", "generic error"))
            return False

        if command.name != "tebex" and command.name != "tebexadmin":
            return True

        if len(args) == 0:
            sender.send_error_message(self.config.messages.get("no_subcommand", "no subcommand"))
            return False

        try:
            if command.name == "tebex":
                subcommand = self.tebex_subcommands.subcommand_map.get(args[0])
                if subcommand:
                    return subcommand(sender, command, args[1:])
                else:
                    sender.send_error_message(self.config.messages.get("invalid_subcommand", "invalid subcommand"))
                    return False

            if command.name == "tebexadmin":
                subcommand = self.tebex_admin_subcommands.subcommand_map.get(args[0])
                if subcommand:
                    return subcommand(sender, command, args[1:])
                else:
                    sender.send_error_message(self.config.messages.get("invalid_subcommand", "invalid subcommand"))
        except Exception as e:
            sender.send_error_message(self.config.messages.get("generic_error", "generic error"))
            self.logger.error(str(e))
            return False

        return True

    def _load_config(self) -> TebexConfig:
        folder = Path(self.data_folder)
        folder.mkdir(parents=True, exist_ok=True)
        cfg_path = folder / "config.yml"
        
        yml = YAML()
        yml.version = (1, 2)
        yml.preserve_quotes = False
        
        defaults = [
            ("secret_key", "", "Your Tebex secret key"),
            ("check_interval", 60, "Interval in seconds to check for new payments"),

            ("messages.no_subcommand", "No subcommand was provided. Try /tebex help.", "Shown when /tebex | /tebexadmin is used with no arguments"),
            ("messages.invalid_subcommand", "The subcommand provided isn't valid. Try /tebex help.", "Shown when /tebex | /tebexadmin is used with an invalid subcommand"),
            ("messages.generic_error", "A technical error has occoured. Please contact a server admin or owner.", "Generic error for commands"),
            ("messages.help_header", "--- Tebex Help ---", "Goes atop the help area."),

            # The help section MUST have each of its items to be aligned with a real subcommand.
            ("help.help", "Show this help message", "/tebex help"),
            ("help.info", "Show info about the server's Tebex webstore", "/tebex info"),
            ("help.store", "Show the server's webstore URL", "/tebex store"),
            ("help_admin.help", "Show this help message", "/tebexadmin help"),
            ("help_admin.debug", "Send debug info to the console", "/tebexadmin debug"),
            ("help_admin.fulfill", "Force the executor to fulfill all online commands", "/tebexadmin fulfill"),

            ("commands.info.header", "--- Info ---", "Header for the /tebex info's output"),
            ("commands.info.store", "Store: [store_name]", "Line for the store in /tebex info. [store_name] will resolve to the store's name."),
            ("commands.info.currency", "Currency: [currency]", "Line for the currency in /tebex info. [currency] will resolve to the server's currency."),
            ("commands.info.domain", "URL: [domain]", "Line for the domain in /tebex info. [domain] will resolve to the server's domain (i.e., URL)"),
            ("commands.store.qr_codes", True, "Weather to use QR codes alongside URL upon players using /tebex store")
        ]
        
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                existing = yml.load(f)
            if not isinstance(existing, CommentedMap):
                existing = CommentedMap(existing or {})
        else:
            existing = CommentedMap()

        for key, default, comment in defaults:
            keys = key.split(".")
            current = existing
            for i, k in enumerate(keys[:-1]):
                if k not in current:
                    current[k] = CommentedMap()
                current = current[k]
            
            if keys[-1] not in current:
                current[keys[-1]] = default
                current.yaml_add_eol_comment(comment, keys[-1])

        with open(cfg_path, "w", encoding="utf-8") as f:
            yml.dump(existing, f)

        config_dict = self._commented_map_to_dict(existing)
        return TebexConfig(**config_dict)

    def _commented_map_to_dict(self, data: Any) -> Any:
        if isinstance(data, CommentedMap):
            return {k: self._commented_map_to_dict(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._commented_map_to_dict(v) for v in data]
        return data

    @property
    def config(self) -> TebexConfig:
        return cast(TebexConfig, self._config)

    def _save_secret_key(self, key: str) -> None:
        folder = Path(self.data_folder)
        cfg_path = folder / "config.yml"
        
        yml = YAML()
        yml.version = (1, 2)
        
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                existing = yml.load(f)
            if not isinstance(existing, CommentedMap):
                existing = CommentedMap(existing or {})
        else:
            existing = CommentedMap()
            
        existing["secret_key"] = key
        
        with open(cfg_path, "w", encoding="utf-8") as f:
            yml.dump(existing, f)
            
        self.config.secret_key = key
        if hasattr(self, "tebex_client"):
            self.tebex_client.secret = key
        else:
            self.tebex_client = TebexClient(key)
            self.tebex_subcommands = TebexCommands(self, self.tebex_client)
            self.tebex_admin_subcommands = TebexAdminCommands(self, self.tebex_client)
            self.active = True

    @event_handler
    def on_player_join(self, event: PlayerJoinEvent):
        submit(self.tebex_client.identify_player(event.player.name, event.player.xuid))