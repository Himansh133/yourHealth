import json

import httpx

from app.services.whatsapp.client import CloudApi


def make(handler):
    return CloudApi("tok", "PNID", "v23.0", transport=httpx.MockTransport(handler))


def test_send_text_posts_to_the_phone_number_messages_endpoint():
    seen = {}

    def handler(r):
        seen.update(url=str(r.url), auth=r.headers["authorization"], body=json.loads(r.content))
        return httpx.Response(200, json={"messages": [{"id": "wamid.1"}]})

    make(handler).send_text("+919812345210", "Hello")
    assert seen["url"] == "https://graph.facebook.com/v23.0/PNID/messages"
    assert seen["auth"] == "Bearer tok"
    assert seen["body"] == {"messaging_product": "whatsapp", "to": "919812345210", "type": "text",
                            "text": {"body": "Hello"}}


def test_buttons_are_capped_at_three_with_short_titles():
    seen = {}
    make(lambda r: (seen.update(body=json.loads(r.content)), httpx.Response(200, json={}))[1]).send_buttons(
        "+911", "Whose report is this?", [("a", "Papa"), ("b", "A very long family member name")])
    action = seen["body"]["interactive"]["action"]
    assert seen["body"]["interactive"]["type"] == "button"
    assert [b["reply"]["title"] for b in action["buttons"]] == ["Papa", "A very long family m"]


def test_list_message_rows():
    seen = {}
    make(lambda r: (seen.update(body=json.loads(r.content)), httpx.Response(200, json={}))[1]).send_list(
        "+911", "Whose report is this?", "Choose", [(str(i), f"Person {i}") for i in range(4)])
    i = seen["body"]["interactive"]
    assert i["type"] == "list" and i["action"]["button"] == "Choose"
    assert [r["id"] for r in i["action"]["sections"][0]["rows"]] == ["0", "1", "2", "3"]


def test_download_media_gets_the_url_then_the_bytes_with_the_token():
    calls = []

    def handler(r):
        calls.append((str(r.url), r.headers["authorization"]))
        if r.url.path.endswith("/MEDIA1"):
            return httpx.Response(200, json={"url": "https://lookaside.example/file", "mime_type": "application/pdf"})
        return httpx.Response(200, content=b"%PDF-1.4")

    data, mime = make(handler).download_media("MEDIA1")
    assert (data, mime) == (b"%PDF-1.4", "application/pdf")
    assert calls == [("https://graph.facebook.com/v23.0/MEDIA1", "Bearer tok"),
                     ("https://lookaside.example/file", "Bearer tok")]


def test_api_base_is_configurable_for_local_testing():
    seen = {}
    api = CloudApi("tok", "PNID", "v23.0", base="http://localhost:8020",
                   transport=httpx.MockTransport(lambda r: (seen.update(url=str(r.url)), httpx.Response(200, json={}))[1]))
    api.send_text("+911", "hi")
    assert seen["url"] == "http://localhost:8020/v23.0/PNID/messages"
