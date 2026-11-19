from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Payment


class PaymentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, transaction_id: str, idempotency_key: str, amount: float, currency: str) -> Payment:
        payment = Payment(
            transaction_id=transaction_id,
            idempotency_key=idempotency_key,
            amount=amount,
            currency=currency,
        )
        self.db.add(payment)
        self.db.commit()
        return payment

    def count_by_key(self, idempotency_key: str) -> int:
        statement = select(func.count()).select_from(Payment).where(Payment.idempotency_key == idempotency_key)
        return self.db.scalar(statement)
