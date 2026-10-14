import httpx

from cashflow.application.assistant import Assistant
from cashflow.infrastructure.rag import AnthropicModel, ExtractiveModel, KnowledgeIndex
from cashflow.infrastructure.storage import SummaryStore


def test_rag_citations_and_no_match(tmp_path):
    index = KnowledgeIndex(str(tmp_path / "index.db"))
    index.rebuild("knowledge")
    agent = Assistant(index, SummaryStore(str(tmp_path / "summary.db")), ExtractiveModel())
    result = agent.ask("Como funciona o saldo?", "2026-10-13")
    assert result["mode"] == "rag"
    assert result["facts"]["closing_cents"] == 0
    assert any(s["source"] == "fluxo-caixa.md" for s in result["sources"])
    assert agent.ask("quasarxylophone", "2026-10-13")["mode"] == "abstention"


def test_invalid_citation_rejected(tmp_path):
    class BadModel:
        def generate(self, *args):
            return "Invented [unknown-source]"

    index = KnowledgeIndex(str(tmp_path / "index.db"))
    index.rebuild("knowledge")
    agent = Assistant(index, SummaryStore(str(tmp_path / "summary.db")), BadModel())
    assert agent.ask("saldo", "2026-10-13")["mode"] == "abstention"


def test_anthropic_http_contract():
    import json

    def handler(request):
        body = json.loads(request.content)
        assert request.url == "https://api.anthropic.com/v1/messages"
        assert request.headers["anthropic-version"] == "2023-06-01"
        assert body["max_tokens"] == 700
        assert body["model"] == "test-model"
        return httpx.Response(
            200,
            json={
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": "Explicação [balance]"}],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        model = AnthropicModel(client, "test-key", "test-model")
        assert model.generate("saldo", [], {}) == "Explicação [balance]"
