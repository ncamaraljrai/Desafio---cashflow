"""Optional AI composition root; never imported by ledger or consolidation."""

import logging
import os
import threading
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from cashflow.application.assistant import Assistant
from cashflow.config import Settings
from cashflow.infrastructure.rag import (
    AnthropicModel,
    ExtractiveModel,
    HttpBalanceReader,
    KnowledgeIndex,
)
from cashflow.presentation.api import base_app, require_token


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    question: str = Field(min_length=1, max_length=1000)
    business_date: str


def create_app():
    settings = Settings.from_env()
    index = KnowledgeIndex(os.getenv("KNOWLEDGE_DB", "data/knowledge.db"))
    index.rebuild(os.getenv("KNOWLEDGE_DIR", "knowledge"))
    client = httpx.Client(trust_env=False, timeout=20)
    provider = os.getenv("AI_PROVIDER", "offline")
    if provider not in ("offline", "anthropic"):
        raise ValueError("AI_PROVIDER must be offline or anthropic")
    model = (
        ExtractiveModel()
        if provider == "offline"
        else AnthropicModel(
            client, os.getenv("ANTHROPIC_API_KEY", ""), os.getenv("ANTHROPIC_MODEL", "")
        )
    )
    assistant = Assistant(
        index, HttpBalanceReader(client, settings.summary_url, settings.api_token), model
    )
    app = base_app("Cashflow • Assistente RAG", index)

    @asynccontextmanager
    async def lifespan(app):
        yield
        client.close()

    app.router.lifespan_context = lifespan
    capacity = threading.BoundedSemaphore(2)

    @app.post("/assistant/ask", dependencies=[Depends(require_token(settings.api_token))])
    def ask(body: Question):
        if not capacity.acquire(blocking=False):
            raise HTTPException(429, "AI capacity reached", headers={"Retry-After": "5"})
        try:
            return {**assistant.ask(body.question, body.business_date), "provider": provider}
        except (httpx.HTTPError, KeyError, TypeError) as exc:
            logging.warning("ai_dependency_failed type=%s", type(exc).__name__)
            raise HTTPException(503, "AI dependency unavailable") from exc
        finally:
            capacity.release()

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    uvicorn.run(create_app(), host="0.0.0.0", port=8002, access_log=False)
