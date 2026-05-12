from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional

class TestModel(BaseModel):
    price: Optional[Decimal] = Field(None, decimal_places=2)

print("Success!")
