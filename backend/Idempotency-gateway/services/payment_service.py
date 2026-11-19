from typing import Union
import os
import time
import uuid

from models import utc_now
from repositories.payment_repository import PaymentRepository
from schemas.payment import PaymentRequest

PROCESSING_DELAY_SECONDS = float(os.getenv("PROCESSING_DELAY_SECONDS", "2"))


def format_amount(amount: float) -> Union[int, float]:
    return int(amount) if float(amount).is_integer() else amount


class PaymentService:
    def __init__(self, payment_repository: PaymentRepository):
        self.payment_repository = payment_repository

    def charge(self, idempotency_key: str, payment: PaymentRequest) -> tuple[int, dict]:
        time.sleep(PROCESSING_DELAY_SECONDS)

        transaction_id = f"txn_{uuid.uuid4().hex}"
        self.payment_repository.create(
            transaction_id=transaction_id,
            idempotency_key=idempotency_key,
            amount=payment.amount,
            currency=payment.currency,
        )

        amount = format_amount(payment.amount)
        body = {
            "status": "success",
            "message": f"Charged {amount} {payment.currency}",
            "transaction_id": transaction_id,
            "amount": amount,
            "currency": payment.currency,
            "processed_at": utc_now().isoformat() + "Z",
        }
        return 201, body
