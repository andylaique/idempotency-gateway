import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test_idempotency.db"
os.environ["PROCESSING_DELAY_SECONDS"] = "0.5"

import pytest
from fastapi.testclient import TestClient

from main import app
from repositories.database import SessionLocal
from repositories.payment_repository import PaymentRepository


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def count_charges():
    def _count(key: str) -> int:
        with SessionLocal() as db:
            return PaymentRepository(db).count_by_key(key)

    return _count
