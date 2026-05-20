from pathlib import Path
from typing import Any, cast, Optional
from endstone_tebex_integration.api_client import TebexAPIClient, TebexAPIError
from endstone.plugin import Plugin
from endstone.command import CommandSender, Command
from endstone.event import PlayerJoinEvent, PlayerQuitEvent, event_handler
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from pydantic import BaseModel, Field
from endstone_tebex_integration.commands import TebexCommands, TebexAdminCommands
from endstone_tebex_integration.handlers.due_commands import DueCommandsHandler

class TebexConfig(BaseModel):
    secret_key: str = ""
    webhook_secret: str = ""
    check_interval: int = 60
    messages: dict[str, str] = Field(default_factory=dict)
    help: dict[str, str] = Field(default_factory=dict)
    help_admin: dict[str, str] = Field(default_factory=dict)

class TebexIntegrationPlugin(Plugin):
    config: TebexConfig | None
    _api_client: TebexAPIClient | None
    _due_commands_handler: Optional['DueCommandsHandler']

    commands = {
        "tebex": {
            "description": "General Tebex commands.",
            "usages": [
                "/tebex secret <secret: string>",
                "/tebex info",
                "/tebex refresh",
                "/tebex dropall",
                "/tebex help"
            ],
            "permissions": ["tebex_integration.command.general"],
        },

        "tebexadmin": {
            "description": "Administrative commands for Tebex.",
            "usages": [
                "/tebexadmin <subcommand: string>",
                "/tebexadmin help"
            ],
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
            "default": False,
        }
    }

    def on_enable(self) -> None:
        self._config: TebexConfig = self._load_config()

        # Initialize API client if secret exists
        if self.config.secret_key:
            try:
                self._api_client = TebexAPIClient(self.config.secret_key)
                assert self._api_client is not None
                # Validate connection
                info = self._api_client.get_information()
                self._due_commands_handler = DueCommandsHandler(self, self._api_client)
                account = info.get("account", {})
                self.logger.info(f"Tebex integration initialized for account: {account.get('name', 'Unknown')}")
            except Exception as e:
                self.logger.error(f"Failed to initialize API client: {e}")
                self._api_client = None
                self._due_commands_handler = None
        else:
            self._api_client = None
            self._due_commands_handler = None

        self.register_events(self)
        self.logger.info("Tebex Integration Plugin enabled.")

        if not self.server.online_mode:
            self.logger.warning("*" * 60)
            self.logger.warning("online-mode is set to FALSE!!!!")
            self.logger.warning("Player XUIDs can't be verified!!!! Payments can be FAKED!!!!!!!")
            self.logger.warning("It is highly recommended to enable online-mode in server.properties.")
            self.logger.warning("*" * 60)

        self.tebex_subcommands = TebexCommands(self)
        self.tebex_admin_subcommands = TebexAdminCommands(self)

    def on_disable(self) -> None:
        if self._due_commands_handler:
            self._due_commands_handler.shutdown()
        self.logger.info("Tebex Integration Plugin disabled.")

    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        if command.name != "tebex" and command.name != "tebexadmin":
            return True
        if len(args) == 0:
            sender.send_error_message(self.config.messages.get("no_subcommand", "no subcommand"))
            return False

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

        return True

    def set_secret(self, secret_key: str, sender: Optional[CommandSender] = None) -> bool:
        try:
            # Validate secret by fetching information
            test_client = TebexAPIClient(secret_key)
            info = test_client.get_information()

            # Success - update config
            self._config.secret_key = secret_key
            self._save_config()

            # Initialize API client
            self._api_client = TebexAPIClient(secret_key)

            # Initialize handlers
            assert self._api_client is not None
            self._due_commands_handler = DueCommandsHandler(self, self._api_client)

            if sender:
                account = info.get("account", {})
                server = info.get("server", {})
                sender.send_message(f"§aSecret key validated successfully!")
                sender.send_message(f"§7Account: §f{account.get('name', 'Unknown')}")
                sender.send_message(f"§7Server: §f{server.get('name', 'Unknown')}")

            account_name = info.get("account", {}).get('name', 'Unknown')
            self.logger.info(f"Tebex integration initialized for account: {account_name}")
            return True

        except TebexAPIError as e:
            if sender:
                sender.send_error_message(f"§cInvalid secret key: {e}")
            self.logger.error(f"Failed to validate secret key: {e}")
            return False
        except Exception as e:
            if sender:
                sender.send_error_message(f"§cError: {e}")
            self.logger.error(f"Failed to initialize Tebex client: {e}")
            return False

    def show_tebex_info(self, sender: CommandSender) -> None:
        if not self._api_client:
            sender.send_error_message("§cTebex API not configured. Use /tebex secret <key> first.")
            return

        try:
            info = self._api_client.get_information()
            account = info.get("account", {})
            server = info.get("server", {})

            sender.send_message("§6§l=== Tebex Information ===§r")
            sender.send_message(f"§6Account:§e {account.get('name', 'N/A')} §7(ID: {account.get('id', 'N/A')})")
            sender.send_message(f"§6Domain:§e {account.get('domain', 'N/A')}")
            sender.send_message(f"§6Currency:§e {account.get('currency', {}).get('iso_4217', 'N/A')}")
            sender.send_message(f"§6Game Type:§e {account.get('game_type', 'N/A')}")
            sender.send_message(f"§6Online Mode:§e {account.get('online_mode', False)}")
            sender.send_message(f"§6Server:§e {server.get('name', 'N/A')} §7(ID: {server.get('id', 'N/A')})")
            sender.send_message(f"§6API Latency:§e {round(self._api_client.get_latency() * 1000)}ms")
        except TebexAPIError as e:
            sender.send_error_message(f"§cFailed to fetch info: {e}")

    def refresh_commands(self, sender: CommandSender) -> None:
        if not self._due_commands_handler:
            sender.send_error_message("§cTebex not configured. Use /tebex secret <key> first.")
            return

        sender.send_message("§7Refreshing command queues...")
        self._due_commands_handler.refresh()
        sender.send_message("§aRefresh completed!")

    def drop_all_commands(self, sender: CommandSender) -> None:
        # TODO: Mark all queued commands as executed
        sender.send_message("Dropping all commands - Not implemented yet")

    def _load_config(self) -> TebexConfig:
        folder = Path(self.data_folder)
        folder.mkdir(parents=True, exist_ok=True)
        cfg_path = folder / "config.yml"

        yml = YAML()
        yml.version = (1, 2)
        yml.preserve_quotes = False

        defaults = [
            ("secret_key", "", "Your Tebex secret key"),
            ("webhook_secret", "", "Your tebex webhook secret (leave empty if not using webhooks)"),
            ("check_interval", 60, "Interval in seconds to check for new payments"),
            ("messages.payment_success", "Thank you! The payment was successful",
             "Message shown to the player after a successful payment"),
            ("messages.no_subcommand", "No subcommand was provided. Try /tebex help.",
             "Shown when /tebex | /tebexadmin is used with no arguments"),
            ("messages.invalid_subcommand", "The subcommand provided isn't valid. Try /tebex help.",
             "Shown when /tebex | /tebexadmin is used with an invalid subcommand"),
            ("help.help", "Show this help message", "/tebex help"),
            ("help.secret", "Set Tebex secret key", "/tebex secret <key>"),
            ("help.info", "Fetch Tebex account, server and API info", "/tebex info"),
            ("help.refresh", "Refresh offline and online command queues", "/tebex refresh"),
            ("help.dropall", "Drop all queued commands", "/tebex dropall"),
            ("help_admin.help", "Show this help message", "/tebexadmin help")
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

    def _save_config(self) -> None:
        folder = Path(self.data_folder)
        folder.mkdir(parents=True, exist_ok=True)
        cfg_path = folder / "config.yml"

        yml = YAML()
        yml.version = (1, 2)

        # Build config dict from current config
        config_dict = {
            "secret_key": self._config.secret_key,
            "webhook_secret": self._config.webhook_secret,
            "check_interval": self._config.check_interval,
            "messages": self._config.messages,
            "help": self._config.help,
            "help_admin": self._config.help_admin,
        }

        with open(cfg_path, "w", encoding="utf-8") as f:
            yml.dump(config_dict, f)

    def _commented_map_to_dict(self, data: Any) -> Any:
        if isinstance(data, CommentedMap):
            return {k: self._commented_map_to_dict(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._commented_map_to_dict(v) for v in data]
        return data

    @property
    def config(self) -> TebexConfig:
        return cast(TebexConfig, self._config)

    @event_handler
    def on_player_join(self, player: PlayerJoinEvent) -> None:
        if self._due_commands_handler:
            self._due_commands_handler.on_player_join(event.player)

    @event_handler
    def on_player_quit(self, event: PlayerQuitEvent):
        if self._due_commands_handler:
            self._due_commands_handler.on_player_quit(event.player)