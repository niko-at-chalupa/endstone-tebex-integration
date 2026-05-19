from pathlib import Path
from typing import Any, cast
from endstone.plugin import Plugin
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from pydantic import BaseModel, Field

class TebexConfig(BaseModel):
    secret_key: str = ""
    webhook_secret: str = ""
    check_interval: int = 60
    messages: dict[str, str] = Field(default_factory=dict)

class TebexIntegrationPlugin(Plugin):
    def on_enable(self) -> None:
        self._config: TebexConfig = self._load_config()
        self.register_events(self)
        self.logger.info("Tebex Integration Plugin enabled.")

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
            ("messages.payment_success", "Thank you!! The payment was successful", "Message shown to the player after a successful payment"),
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
