class IdempotencyKeyReusedError(Exception):
    def __init__(self):
        super().__init__("Idempotency key already used for a different request body.")


class RequestStillProcessingError(Exception):
    def __init__(self):
        super().__init__("A request with this Idempotency-Key is still being processed. Retry shortly.")
