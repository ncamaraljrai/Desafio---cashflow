"""Read-only RAG orchestration. A generated explanation never becomes ledger data."""

import re
from typing import Protocol

from cashflow.domain.model import validate_day


class Retriever(Protocol):
    def search(self, query: str, limit: int = 4) -> list[dict]: ...


class BalanceReader(Protocol):
    def report(self, day: str) -> dict: ...


class LanguageModel(Protocol):
    def generate(self, question: str, sources: list[dict], facts: dict) -> str: ...


class Assistant:
    def __init__(self, retriever: Retriever, balances: BalanceReader, model: LanguageModel):
        self.retriever, self.balances, self.model = retriever, balances, model

    def ask(self, question: str, day: str):
        validate_day(day)
        if not question.strip() or len(question) > 1000:
            raise ValueError("question must contain 1..1000 characters")
        sources = self.retriever.search(question)
        facts = self.balances.report(day)
        if not sources:
            return {
                "answer": "Não encontrei documentação suficiente para responder.",
                "sources": [],
                "facts": facts,
                "mode": "abstention",
            }
        answer = self.model.generate(question, sources, facts)
        cited = set(re.findall(r"\[([^\[\]\n]+)\]", answer))
        allowed = {source["id"] for source in sources} | {"balance"}
        if not cited or not cited.issubset(allowed):
            return {
                "answer": "Resposta descartada: citações ausentes ou inválidas.",
                "sources": sources,
                "facts": facts,
                "mode": "abstention",
            }
        return {
            "answer": answer,
            "sources": sources,
            "facts": facts,
            "mode": "rag",
            "notice": "Explicação gerada; confira os valores em facts. "
            "O consolidado é eventualmente consistente; não representa fechamento final.",
        }
