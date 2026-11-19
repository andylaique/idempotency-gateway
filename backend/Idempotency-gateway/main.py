import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from repositories.database import create_tables
from routers.health_router import router as health_router
from routers.payment_router import router as payment_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="Idempotency Gateway",
    description="Pay-Once Protocol: every payment is processed exactly once per Idempotency-Key.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    errors = [f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}" for item in error.errors()]
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Invalid request.", "errors": errors},
    )


app.include_router(health_router)
app.include_router(payment_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
