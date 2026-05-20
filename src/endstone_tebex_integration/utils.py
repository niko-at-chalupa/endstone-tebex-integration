from typing import Dict
from endstone import Player
from endstone_tebex_integration.tebex.models import TebexDuePlayer

class TebexApiUtils:
    @staticmethod
    def online_command_parameters(player: Player, due_player: TebexDuePlayer) -> Dict[str, str]:
        """Generate placeholder replacements for online commands"""
        gamertag = f'"{player.name}"'
        return {
            "{name}": gamertag,
            "{player}": gamertag,
            "{username}": f'"{due_player.name}"',
            "{id}": player.xuid or ""
        }

    @staticmethod
    def online_format_command(command: str, player: Player, due_player: TebexDuePlayer) -> str:
        """Replace placeholders in command string for online commands"""
        params = TebexApiUtils.online_command_parameters(player, due_player)
        result = command
        for placeholder, value in params.items():
            result = result.replace(placeholder, value)
        return result

    @staticmethod
    def offline_command_parameters(due_player: TebexDuePlayer) -> Dict[str, str]:
        """Generate placeholder replacements for offline commands"""
        gamertag = f'"{due_player.name}"'
        return {
            "{name}": gamertag,
            "{player}": gamertag,
            "{username}": gamertag,
            "{id}": due_player.uuid or ""
        }

    @staticmethod
    def offline_format_command(command: str, due_player: TebexDuePlayer) -> str:
        """Replace placeholders in command string for offline commands"""
        params = TebexApiUtils.offline_command_parameters(due_player)
        result = command
        for placeholder, value in params.items():
            result = result.replace(placeholder, value)
        return result