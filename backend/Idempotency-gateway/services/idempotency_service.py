import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.orm import Session

from models import RecordStatus, utc_now
from repositories.idempotency_repository import IdempotencyRepository
from repositories.payment_repository import PaymentRepository
from schemas.payment import PaymentRequest
from services.exceptions import IdempotencyKeyReusedError, RequestStillProcessingError
from services.payment_service import PaymentService

KEY_TTL_SECONDS = int(os.getenv("KEY_TTL_SECONDS", str(24 * 60 * 60)))
IN_FLIGHT_WAIT_SECONDS = float(os.getenv("IN_FLIGHT_WAIT_SECONDS", "30"))
POLL_INTERVAL_SECONDS = 0.1


@dataclass
class PaymentResult:
    status_code: int
    body: dict
    cache_hit: bool


def fingerprint(payment: PaymentRequest) -> str:
    canonical = json.dumps(payment.model_dump(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class IdempotencyService:
    def __init__(self, repository: IdempotencyRepository, payment_service: PaymentService):
        self.repository = repository
        self.payment_service = payment_service

    def process_payment(self, key: str, payment: PaymentRequest) -> PaymentResult:
        self.repository.delete_expired(utc_now())
        request_hash = fingerprint(payment)

        if self.repository.claim(key, request_hash):
            return self._process_first_request(key, payment)

        return self._handle_existing_key(key, request_hash, payment)

    def _process_first_request(self, key: str, payment: PaymentRequest) -> PaymentResult:
        try:
            status_code, body = self.payment_service.charge(key, payment)
        except Exception:
            self.repository.delete(key)
            raise

        expires_at = utc_now() + timedelta(seconds=KEY_TTL_SECONDS)
        self.repository.complete(key, status_code, body, expires_at)
        return PaymentResult(status_code=status_code, body=body, cache_hit=False)

    def _handle_existing_key(self, key: str, request_hash: str, payment: PaymentRequest) -> PaymentResult:
        record = self.repository.get_latest(key)
        if record is None:
            return self.process_payment(key, payment)

        if record.request_hash != request_hash:
            raise IdempotencyKeyReusedError()

        if record.status == RecordStatus.IN_FLIGHT:
            record = self._wait_for_completion(key)
            if record is None:
                return self.process_payment(key, payment)

        return PaymentResult(
            status_code=record.response_status_code,
            body=record.response_body,
            cache_hit=True,
        )

    def _wait_for_completion(self, key: str):
        deadline = time.monotonic() + IN_FLIGHT_WAIT_SECONDS
        while time.monotonic() < deadline:
            time.sleep(POLL_INTERVAL_SECONDS)
            record = self.repository.get_latest(key)
            if record is None or record.status == RecordStatus.COMPLETED:
                return record
        raise RequestStillProcessingError()


def build_idempotency_service(db: Session) -> IdempotencyService:
    payment_service = PaymentService(PaymentRepository(db))
    return IdempotencyService(IdempotencyRepository(db), payment_service)
