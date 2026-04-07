from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from ....events import DeliveryEvent
from ....types import RequestOptions
from ..models import WhatsAppSendResult, WhatsAppTemplateRequest, WhatsAppTextRequest


class WhatsAppGateway(Protocol):
    provider_name: str

    def send_text(
        self,
        request: WhatsAppTextRequest,
        *,
        options: RequestOptions | None = None,
    ) -> WhatsAppSendResult: ...

    def send_template(
        self,
        request: WhatsAppTemplateRequest,
        *,
        options: RequestOptions | None = None,
    ) -> WhatsAppSendResult: ...

    def parse_event(self, payload: Mapping[str, object]) -> DeliveryEvent | None: ...

    def close(self) -> None: ...


class AsyncWhatsAppGateway(Protocol):
    provider_name: str

    async def asend_text(
        self,
        request: WhatsAppTextRequest,
        *,
        options: RequestOptions | None = None,
    ) -> WhatsAppSendResult: ...

    async def asend_template(
        self,
        request: WhatsAppTemplateRequest,
        *,
        options: RequestOptions | None = None,
    ) -> WhatsAppSendResult: ...

    def parse_event(self, payload: Mapping[str, object]) -> DeliveryEvent | None: ...

    async def aclose(self) -> None: ...
