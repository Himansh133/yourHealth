import json

import httpx
import pytest

from app.services.chat.llm import FakeLLM, LLMError, OpenAICompatibleLLM


def test_fake_llm_returns_scripted_replies_in_order_and_records_prompts():
    llm = FakeLLM(["first", "second"])
    assert llm.complete_json("sys", "q1") == "first"
    assert llm.complete_json("sys", "q2") == "second"
    assert [p[1] for p in llm.prompts] == ["q1", "q2"]


def test_openai_compatible_client_sends_json_mode_chat_request():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"answerable": false}'}}]})

    llm = OpenAICompatibleLLM("https://api.gmi-serving.com/v1", "key-123", "some/model",
                              transport=httpx.MockTransport(handler))
    out = llm.complete_json("system rules", "the question")

    assert out == '{"answerable": false}'
    assert seen["url"] == "https://api.gmi-serving.com/v1/chat/completions"
    assert seen["auth"] == "Bearer key-123"
    assert seen["body"]["model"] == "some/model"
    assert seen["body"]["messages"] == [{"role": "system", "content": "system rules"},
                                        {"role": "user", "content": "the question"}]
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert seen["body"]["temperature"] == 0


def test_provider_error_raises_llm_error_without_leaking_the_key():
    transport = httpx.MockTransport(lambda r: httpx.Response(401, json={"error": "bad key"}))
    llm = OpenAICompatibleLLM("https://api.gmi-serving.com/v1", "key-123", "m", transport=transport)
    with pytest.raises(LLMError) as e:
        llm.complete_json("s", "u")
    assert "401" in str(e.value)
    assert "key-123" not in str(e.value)


def _sent_body(**kwargs) -> dict:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    OpenAICompatibleLLM("https://x/v1", "k", "m", transport=httpx.MockTransport(handler), **kwargs).complete_json("s", "u")
    return seen["body"]


def test_thinking_can_be_turned_off():
    assert _sent_body(thinking=False)["thinking"] == {"type": "disabled"}


def test_thinking_field_is_not_sent_by_default():
    assert "thinking" not in _sent_body()


def test_get_llm_passes_the_thinking_setting(monkeypatch):
    from app.core.config import settings
    from app.services.chat.llm import get_llm
    monkeypatch.setattr(settings, "llm_api_key", "k")
    monkeypatch.setattr(settings, "llm_model", "m")
    monkeypatch.setattr(settings, "llm_thinking", False)
    assert get_llm().thinking is False
