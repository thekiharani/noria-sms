from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from ..models import DeliveryReport, SendSmsRequest, SendSmsResult, SmsBalance
from ..types import RequestOptions


class SmsGateway(Protocol):
    provider_name: str

    def send(
        self,
        request: SendSmsRequest,
        *,
        options: RequestOptions | None = None,
    ) -> SendSmsResult: ...

    def get_balance(self, *, options: RequestOptions | None = None) -> SmsBalance | None: ...

    def parse_delivery_report(self, payload: Mapping[str, object]) -> DeliveryReport | None: ...

    def close(self) -> None: ...


class AsyncSmsGateway(Protocol):
    provider_name: str

    async def asend(
        self,
        request: SendSmsRequest,
        *,
        options: RequestOptions | None = None,
    ) -> SendSmsResult: ...

    async def aget_balance(self, *, options: RequestOptions | None = None) -> SmsBalance | None: ...

    def parse_delivery_report(self, payload: Mapping[str, object]) -> DeliveryReport | None: ...

    async def aclose(self) -> None: ...
