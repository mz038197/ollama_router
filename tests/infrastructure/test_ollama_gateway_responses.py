import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.gateways.ollama_gateway import OllamaGateway


@pytest.fixture
def gateway():
    g = OllamaGateway(["http://127.0.0.1:11434"], max_concurrent_per_backend=1)
    mock_client = AsyncMock()
    g.client = mock_client
    return g, mock_client


@pytest.mark.asyncio
async def test_responses_create_strips_reasoning_when_model_not_thinking(gateway):
    g, mock_client = gateway

    show_response = MagicMock()
    show_response.status_code = 200
    show_response.json.return_value = {"capabilities": ["completion"]}

    responses_response = MagicMock()
    responses_response.status_code = 200
    responses_response.json.return_value = {"id": "resp_1", "object": "response", "output": []}

    mock_client.post = AsyncMock(side_effect=[show_response, responses_response])

    body = {
        "model": "llama3.2:3b",
        "input": "hello",
        "reasoning": {"effort": "high"},
    }
    result = await g.responses_create(body)

    assert result["id"] == "resp_1"
    forwarded = mock_client.post.call_args_list[1].kwargs["json"]
    assert "reasoning" not in forwarded


@pytest.mark.asyncio
async def test_responses_create_keeps_reasoning_for_thinking_model(gateway):
    g, mock_client = gateway

    show_response = MagicMock()
    show_response.status_code = 200
    show_response.json.return_value = {"capabilities": ["completion", "thinking"]}

    responses_response = MagicMock()
    responses_response.status_code = 200
    responses_response.json.return_value = {"id": "resp_2", "object": "response", "output": []}

    mock_client.post = AsyncMock(side_effect=[show_response, responses_response])

    body = {
        "model": "gemma4:26b",
        "input": "hello",
        "reasoning": {"effort": "low"},
    }
    await g.responses_create(body)

    forwarded = mock_client.post.call_args_list[1].kwargs["json"]
    assert forwarded["reasoning"] == {"effort": "low"}


@pytest.mark.asyncio
async def test_model_supports_thinking_cache(gateway):
    g, mock_client = gateway

    show_response = MagicMock()
    show_response.status_code = 200
    show_response.json.return_value = {"capabilities": ["thinking"]}
    mock_client.post = AsyncMock(return_value=show_response)

    first = await g._model_supports_thinking("http://127.0.0.1:11434", "gemma4:26b")
    second = await g._model_supports_thinking("http://127.0.0.1:11434", "gemma4:26b")

    assert first is True
    assert second is True
    assert mock_client.post.call_count == 1
