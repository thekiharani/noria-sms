from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from ....events import DeliveryEvent
from ....types import RequestOptions
from ..models import SmsBalance, SmsSendRequest, SmsSendResult


class SmsGateway(Protocol):
    provider_name: str

    def send(
        self,
        request: SmsSendRequest,
        *,
        options: RequestOptions | None = None,
    ) -> SmsSendResult: ...

    def get_balance(self, *, options: RequestOptions | None = None) -> SmsBalance | None: ...

    def parse_delivery_report(self, payload: Mapping[str, object]) -> DeliveryEvent | None: ...

    def close(self) -> None: ...


class AsyncSmsGateway(Protocol):
    provider_name: str

    async def asend(
        self,
        request: SmsSendRequest,
        *,
        options: RequestOptions | None = None,
    ) -> SmsSendResult: ...

    async def aget_balance(self, *, options: RequestOptions | None = None) -> SmsBalance | None: ...

    def parse_delivery_report(self, payload: Mapping[str, object]) -> DeliveryEvent | None: ...

    async def aclose(self) -> None: ...
