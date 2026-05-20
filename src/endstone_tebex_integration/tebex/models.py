from pydantic import BaseModel, Field
from typing import List, Optional, Any

class Account(BaseModel):
    id: int
    name: str
    description: str
    webstore_url: str
    currency: str
    lang: str
    logo: Optional[str] = None
    platform_type: str
    platform_type_id: str
    created_at: str

class Package(BaseModel):
    id: int
    name: str
    description: str
    image: Optional[str] = None
    type: str
    base_price: float
    sales_tax: float
    total_price: float
    currency: str
    discount: float
    disable_quantity: bool
    disable_gifting: bool
    created_at: str
    updated_at: str

class Category(BaseModel):
    id: int
    name: str
    slug: str
    description: str
    order: int
    display_type: str
    packages: List[Package] = Field(default_factory=list)
    parent: Optional[int] = None

class TebexDuePlayer(BaseModel):
    id: int
    name: str
    uuid: Optional[str] = None

class TebexCommandConditions(BaseModel):
    delay: int = 0
    slots: int = 0

class TebexQueuedCommand(BaseModel):
    id: int
    command: str

class TebexQueuedOnlineCommand(BaseModel):
    id: int
    command: TebexQueuedCommand
    conditions: TebexCommandConditions = Field(default_factory=TebexCommandConditions)

class TebexQueuedOfflineCommand(BaseModel):
    id: int
    command: TebexQueuedCommand
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