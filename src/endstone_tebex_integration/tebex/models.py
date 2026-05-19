from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict

@dataclass
class Account:
    id: int
    name: str
    description: str
    webstore_url: str
    currency: str
    lang: str
    logo: Optional[str]
    platform_type: str
    platform_type_id: str
    created_at: str

@dataclass
class Package:
    id: int
    name: str
    description: str
    image: Optional[str]
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

@dataclass
class Category:
    id: int
    name: str
    slug: str
    description: str
    order: int
    display_type: str
    packages: List[Package] = field(default_factory=list)
    parent: Optional[int] = None
