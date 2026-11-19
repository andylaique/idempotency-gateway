import time
from concurrent.futures import ThreadPoolExecutor

from services import idempotency_service

PAYMENT = {"amount": 100, "currency": "GHS"}


def pay(client, key, body=PAYMENT):
    return client.post("/process-payment", json=body, headers={"Idempotency-Key": key})


def test_first_request_processes_the_payment(client, count_charges):
    started = time.monotonic()
    response = pay(client, "first-request")
    elapsed = time.monotonic() - started

    assert response.status_code == 201
    assert response.json()["message"] == "Charged 100 GHS"
    assert response.headers["X-Cache-Hit"] == "false"
    assert elapsed >= 0.5
    assert count_charges("first-request") == 1


def test_duplicate_request_replays_saved_response_without_charging_again(client, count_charges):
    first = pay(client, "duplicate-request")

    started = time.monotonic()
    second = pay(client, "duplicate-request")
    elapsed = time.monotonic() - started

    assert second.status_code == first.status_code
    assert second.json() == first.json()
    assert second.headers["X-Cache-Hit"] == "true"
    assert elapsed < 0.5
    assert count_charges("duplicate-request") == 1


def test_same_key_with_different_body_is_rejected(client):
    pay(client, "reused-key", {"amount": 100, "currency": "GHS"})
    response = pay(client, "reused-key", {"amount": 500, "currency": "GHS"})

    assert response.status_code == 422
    assert response.json()["detail"] == "Idempotency key already used for a different request body."


def test_missing_idempotency_key_returns_400(client):
    response = client.post("/process-payment", json=PAYMENT)

    assert response.status_code == 400


def test_invalid_body_returns_400(client):
    response = pay(client, "invalid-body", {"amount": -5, "currency": "GHS"})

    assert response.status_code == 400


def test_concurrent_duplicates_wait_and_charge_once(client, count_charges):
    with ThreadPoolExecutor(max_workers=2) as pool:
        request_a = pool.submit(pay, client, "in-flight-key")
        time.sleep(0.2)
        request_b = pool.submit(pay, client, "in-flight-key")
        response_a, response_b = request_a.result(), request_b.result()

    assert response_a.status_code == 201
    assert response_b.status_code == 201
    assert response_b.json() == response_a.json()
    assert {response_a.headers["X-Cache-Hit"], response_b.headers["X-Cache-Hit"]} == {"true", "false"}
    assert count_charges("in-flight-key") == 1


def test_expired_key_is_processed_as_a_new_payment(client, count_charges, monkeypatch):
    monkeypatch.setattr(idempotency_service, "KEY_TTL_SECONDS", 0)

    pay(client, "expiring-key")
    response = pay(client, "expiring-key")

    assert response.headers["X-Cache-Hit"] == "false"
    assert count_charges("expiring-key") == 2
