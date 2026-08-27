from pydantic import BaseModel


class TaxLine(BaseModel):
    description: str
    amount: float
    tax_rate: float
    recorded_tax: float


class TaxResult(BaseModel):
    description: str
    expected_tax: float
    recorded_tax: float
    difference: float
    status: str