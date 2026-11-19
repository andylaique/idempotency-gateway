from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from repositories.database import get_db
from schemas.payment import ErrorResponse, IdempotencyKey, PaymentRequest, PaymentResponse
from services.exceptions import IdempotencyKeyReusedError, RequestStillProcessingError
from services.idempotency_service import build_idempotency_service

router = APIRouter(tags=["Payments"])


@router.post(
    "/process-payment",
    status_code=status.HTTP_201_CREATED,
    response_model=PaymentResponse,
    responses={
        400: {"description": "Missing header or invalid body"},
        409: {"model": ErrorResponse, "description": "Original request still processing after the wait limit"},
        422: {"model": ErrorResponse, "description": "Key already used for a different body"},
    },
)
def process_payment(
    payment: PaymentRequest,
    idempotency_key: IdempotencyKey,
    db: Session = Depends(get_db),
):
    service = build_idempotency_service(db)

    try:
        result = service.process_payment(idempotency_key, payment)
    except IdempotencyKeyReusedError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))
    except RequestStillProcessingError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

    return JSONResponse(
        status_code=result.status_code,
        content=result.body,
        headers={
            "X-Cache-Hit": "true" if result.cache_hit else "false",
            "Idempotency-Key": idempotency_key,
        },
    )
