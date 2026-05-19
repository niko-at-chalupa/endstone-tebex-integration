from pydantic import BaseModel, Field
from typing import List, Optional

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
