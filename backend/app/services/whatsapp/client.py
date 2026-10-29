"""WhatsApp Cloud API (plan 7.4): send replies and download media. Behind an interface, with a fake in tests."""
import logging
from typing import Protocol

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

BUTTON_TITLE_MAX = 20  # Meta's limits
LIST_ROW_TITLE_MAX = 24
MAX_BUTTONS = 3
MAX_LIST_ROWS = 10


class WhatsApp(Protocol):
    def send_text(self, to: str, body: str) -> None: ...
    def send_buttons(self, to: str, body: str, buttons: list[tuple[str, str]]) -> None: ...
    def send_list(self, to: str, body: str, button: str, rows: list[tuple[str, str]]) -> None: ...
    def download_media(self, media_id: str) -> tuple[bytes, str | None]: ...


class CloudApi:
    def __init__(self, token: str, phone_number_id: str, version: str, base: str = "https://graph.facebook.com",
                 transport: httpx.BaseTransport | None = None):
        self._client = httpx.Client(base_url=f"{base.rstrip('/')}/{version}/", timeout=30,
                                    headers={"Authorization": f"Bearer {token}"}, transport=transport)
        self._phone_number_id = phone_number_id

    def _send(self, to: str, payload: dict) -> None:
        body = {"messaging_product": "whatsapp", "to": to.lstrip("+"), **payload}
        resp = self._client.post(f"{self._phone_number_id}/messages", json=body)
        if resp.status_code != 200:
            log.warning("WhatsApp send failed: %s", resp.status_code)  # never log the message text

    def send_text(self, to: str, body: str) -> None:
        self._send(to, {"type": "text", "text": {"body": body}})

    def send_buttons(self, to: str, body: str, buttons: list[tuple[str, str]]) -> None:
        self._send(to, {"type": "interactive", "interactive": {"type": "button", "body": {"text": body}, "action": {
            "buttons": [{"type": "reply", "reply": {"id": i, "title": t[:BUTTON_TITLE_MAX]}}
                        for i, t in buttons[:MAX_BUTTONS]]}}})

    def send_list(self, to: str, body: str, button: str, rows: list[tuple[str, str]]) -> None:
        self._send(to, {"type": "interactive", "interactive": {"type": "list", "body": {"text": body}, "action": {
            "button": button, "sections": [{"title": "Family", "rows": [
                {"id": i, "title": t[:LIST_ROW_TITLE_MAX]} for i, t in rows[:MAX_LIST_ROWS]]}]}}})

    def download_media(self, media_id: str) -> tuple[bytes, str | None]:
        meta = self._client.get(media_id)
        meta.raise_for_status()
        info = meta.json()
        # The media URL is short-lived and needs the same token (plan 7.4).
        data = self._client.get(info["url"])
        data.raise_for_status()
        return data.content, info.get("mime_type")


class LogOnly:
    """When WhatsApp isn't configured: nothing is sent."""

    def send_text(self, to, body): log.info("WhatsApp not configured; reply dropped")
    def send_buttons(self, to, body, buttons): log.info("WhatsApp not configured; reply dropped")
    def send_list(self, to, body, button, rows): log.info("WhatsApp not configured; reply dropped")
    def download_media(self, media_id): raise RuntimeError("WhatsApp is not configured")


def get_whatsapp() -> WhatsApp:
    if not (settings.wa_token and settings.wa_phone_number_id):
        return LogOnly()
    return CloudApi(settings.wa_token, settings.wa_phone_number_id, settings.wa_graph_version, settings.wa_api_base)
