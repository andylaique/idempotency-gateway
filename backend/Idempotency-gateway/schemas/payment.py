from typing import Annotated

from fastapi import Header
from pydantic import BaseModel, ConfigDict, Field, field_validator

IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=255, pattern=r"\S"),
]


class PaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: float = Field(gt=0, strict=True)
    currency: str = Field(pattern=r"^[A-Za-z]{3}$")

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class PaymentResponse(BaseModel):
    status: str
    message: str
    transaction_id: str
    amount: float
    currency: str
    processed_at: str


class ErrorResponse(BaseModel):
    detail: str
