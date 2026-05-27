from pydantic import BaseModel, Field
from typing import List, Optional

class TebexDuePlayer(BaseModel):
    id: int
    name: str
    uuid: Optional[str] = None
    xuid: Optional[str] = None

class TebexCommandConditions(BaseModel):
    delay: int = 0
    slots: int = 0

class TebexQueuedCommand(BaseModel):
    id: int
    command: str

class TebexQueuedOnlineCommand(BaseModel):
    id: int
    command: str
    conditions: TebexCommandConditions = Field(default_factory=TebexCommandConditions)

class TebexQueuedOfflineCommand(BaseModel):
    id: int
    command: str
    player: TebexDuePlayer
    conditions: TebexCommandConditions = Field(default_factory=TebexCommandConditions)

class TebexDuePlayersInfo(BaseModel):
    players: List[TebexDuePlayer] = Field(default_factory=list)
    meta: Optional[dict] = None

class TebexQueuedOnlineCommandsInfo(BaseModel):
    commands: List[TebexQueuedOnlineCommand] = Field(default_factory=list)

class TebexQueuedOfflineCommandsInfo(BaseModel):
    commands: List[TebexQueuedOfflineCommand] = Field(default_factory=list)

class TebexServer(BaseModel):
    id: int
    name: str

class TebexAccountInfo(BaseModel):
    id: int
    name: str
    domain: str
    currency: dict
    online_mode: bool
    game_type: str
    log_events: bool

class TebexInformation(BaseModel):
    account: TebexAccountInfo
    server: TebexServer