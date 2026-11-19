from datetime import datetime
from typing import Optional
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import IdempotencyRecord, RecordStatus


class IdempotencyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_latest(self, key: str) -> Optional[IdempotencyRecord]:
        self.db.rollback()
        return self.db.get(IdempotencyRecord, key, populate_existing=True)

    def claim(self, key: str, request_hash: str) -> bool:
        record = IdempotencyRecord(key=key, request_hash=request_hash, status=RecordStatus.IN_FLIGHT)
        self.db.add(record)
        try:
            self.db.commit()
            return True
        except IntegrityError:
            self.db.rollback()
            return False

    def complete(self, key: str, status_code: int, body: dict, expires_at: datetime) -> None:
        record = self.db.get(IdempotencyRecord, key)
        record.status = RecordStatus.COMPLETED
        record.response_status_code = status_code
        record.response_body = body
        record.expires_at = expires_at
        self.db.commit()

    def delete(self, key: str) -> None:
        self.db.rollback()
        self.db.execute(delete(IdempotencyRecord).where(IdempotencyRecord.key == key))
        self.db.commit()

    def delete_expired(self, now: datetime) -> int:
        result = self.db.execute(
            delete(IdempotencyRecord).where(
                IdempotencyRecord.expires_at.is_not(None),
                IdempotencyRecord.expires_at <= now,
            )
        )
        self.db.commit()
        return result.rowcount
