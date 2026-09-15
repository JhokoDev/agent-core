"""Execute após instalar requirements.txt; transporte simulado, sem baixar modelo."""
import json
import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.config import Settings
from app.main import create_app
from app.models.base import Message, ProviderError
from app.models.ollama import OllamaProvider


def settings(tmp_path, **kwargs):
    return Settings(_env_file=None, api_token="x" * 48, data_dir=tmp_path, **kwargs)


@pytest.mark.parametrize("url", ["http://example.com", "https://localhost", "http://localhost:11434/api", "http://secret@localhost:11434", "http://localhost/?secret=x"])
def test_nonlocal_or_ambiguous_urls_rejected(tmp_path, url):
    with pytest.raises(ValidationError):
        settings(tmp_path, ollama_url=url)


def test_public_bind_rejected(tmp_path):
    with pytest.raises(ValidationError):
        settings(tmp_path, host="0.0.0.0")


def test_placeholder_token_rejected(tmp_path):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, api_token="CHANGE_ME", data_dir=tmp_path)


def test_auth_readiness_and_disabled_tools(tmp_path):
    config = settings(tmp_path)
    calls = []
    def respond(request):
        calls.append(request.url.path)
        return httpx.Response(200, json={"models": [{"name": config.model}]})
    provider = OllamaProvider(config, httpx.MockTransport(respond))
    with TestClient(create_app(config, provider)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 401
        assert client.get("/ready", headers={"Authorization": "Bearer wrong"}).status_code == 401
        assert calls == []
        response = client.get("/ready", headers={"Authorization": "Bearer " + "x"*48, "X-Request-ID": "untrusted"})
        assert response.status_code == 200
        assert response.json()["tools"] == "disabled"
        assert response.headers["X-Request-ID"] != "untrusted"
        assert client.post("/shell/run", json={"command": "anything"}).status_code == 404
    assert "x"*48 not in (tmp_path / "logs" / "agent.jsonl").read_text()


def test_model_missing_returns_503(tmp_path):
    config = settings(tmp_path)
    provider = OllamaProvider(config, httpx.MockTransport(lambda r: httpx.Response(200, json={"models": []})))
    with TestClient(create_app(config, provider)) as client:
        response = client.get("/ready", headers={"Authorization": "Bearer " + "x"*48})
        assert response.status_code == 503
        assert response.json()["llm"]["status"] == "model_missing"


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [{}, {"models": None}, {"models": [None]}, {"models": [{"name": 1}]}])
async def test_malformed_health(tmp_path, body):
    provider = OllamaProvider(settings(tmp_path), httpx.MockTransport(lambda r: httpx.Response(200, json=body)))
    try:
        assert (await provider.health()).status == "invalid_response"
    finally:
        await provider.aclose()


@pytest.mark.asyncio
async def test_timeout_and_sanitized_error(tmp_path):
    def timeout(request):
        raise httpx.ReadTimeout("SECRET", request=request)
    provider = OllamaProvider(settings(tmp_path), httpx.MockTransport(timeout))
    try:
        assert (await provider.health()).status == "unreachable"
        with pytest.raises(ProviderError, match="^ollama_request_failed$"):
            await provider.chat([Message(role="user", content="Olá")])
    finally:
        await provider.aclose()


@pytest.mark.asyncio
async def test_chat_uses_configured_model_and_limits(tmp_path):
    config = settings(tmp_path, model="test-model:1b")
    def respond(request):
        body = json.loads(request.content)
        assert request.url.path == "/api/chat"
        assert body["model"] == "test-model:1b"
        assert body["stream"] is False
        assert body["options"]["num_ctx"] == 2048
        assert body["options"]["num_predict"] == 128
        assert "tools" not in body
        return httpx.Response(200, json={"done": True, "message": {"content": "Olá!"}})
    provider = OllamaProvider(config, httpx.MockTransport(respond))
    try:
        assert (await provider.chat([Message(role="user", content="Olá")])).content == "Olá!"
    finally:
        await provider.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [{"done": False, "message": {"content": "partial"}}, {"done": True, "message": {"content": ""}}, {}])
async def test_incomplete_generation_rejected(tmp_path, body):
    provider = OllamaProvider(settings(tmp_path), httpx.MockTransport(lambda r: httpx.Response(200, json=body)))
    try:
        with pytest.raises(ProviderError, match="^ollama_invalid_response$"):
            await provider.chat([Message(role="user", content="Olá")])
    finally:
        await provider.aclose()
