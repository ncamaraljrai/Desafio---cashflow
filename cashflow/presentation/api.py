import json
import logging
import secrets
import sqlite3
import time
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from cashflow.application.services import Consolidate, RecordEntry
from cashflow.domain.model import Conflict

logger = logging.getLogger("cashflow.http")
security = HTTPBearer(auto_error=False)


class EntryInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    kind: Literal["credit", "debit"]
    amount_cents: int = Field(gt=0, le=10**12)
    business_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    description: str = Field(default="", max_length=200)


def require_token(expected):
    def dependency(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)]):
        if credentials is None or not secrets.compare_digest(credentials.credentials, expected):
            raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Bearer"})

    return dependency


def base_app(name, store):
    app = FastAPI(title=name, version="1.0.0")

    @app.middleware("http")
    async def observe(request: Request, call_next):
        request_id = str(uuid4())
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["Cache-Control"] = "no-store"
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                }
            )
        )
        return response

    @app.exception_handler(Conflict)
    async def conflict(request, exc):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(sqlite3.Error)
    async def unavailable(request, exc):
        logger.error("database_unavailable error_type=%s", type(exc).__name__)
        return JSONResponse(
            status_code=503, content={"detail": "Storage unavailable"}, headers={"Retry-After": "1"}
        )

    @app.get("/health/live")
    def live():
        return {"status": "alive"}

    @app.get("/health/ready")
    def ready():
        store.health()
        return {"status": "ready"}

    return app


def ledger_app(store, token):
    app = base_app("Cashflow • Lançamentos", store)
    auth = [Depends(require_token(token))]
    use_case = RecordEntry(store)

    @app.post("/entries", status_code=201, dependencies=auth)
    def record(
        body: EntryInput,
        response: Response,
        idempotency_key: Annotated[str, Header(min_length=1, max_length=128)],
    ):
        data, replay = use_case.execute(idempotency_key, **body.model_dump())
        response.status_code = 200 if replay else 201
        response.headers["Location"] = "/entries/" + data["id"]
        return {**data, "replayed": replay}

    @app.get("/entries/{entry_id}", dependencies=auth)
    def get(entry_id: UUID):
        data = store.get(str(entry_id))
        if data is None:
            raise HTTPException(404, "Entry not found")
        return data

    @app.get("/ops/outbox", dependencies=auth)
    def stats():
        return store.stats()

    return app


def summary_app(store, api_token, event_token):
    app = base_app("Cashflow • Consolidado", store)
    use_case = Consolidate(store)

    @app.get("/balances/{day}", dependencies=[Depends(require_token(api_token))])
    def report(day: str):
        return use_case.report(day)

    @app.post("/internal/events", dependencies=[Depends(require_token(event_token))])
    def event(payload: dict):
        try:
            applied = use_case.receive(payload)
        except (TypeError, KeyError) as exc:
            raise HTTPException(422, "Malformed event") from exc
        return {"applied": applied}

    return app
