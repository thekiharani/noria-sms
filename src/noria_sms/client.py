from __future__ import annotations

from collections.abc import Mapping

from .gateways.base import AsyncSmsGateway, SmsGateway
from .models import DeliveryReport, SendSmsRequest, SendSmsResult, SmsBalance
from .types import RequestOptions


class SmsClient:
    def __init__(self, gateway: SmsGateway) -> None:
        self.gateway = gateway

    @property
    def provider(self) -> str:
        return self.gateway.provider_name

    def send(
        self,
        request: SendSmsRequest,
        *,
        options: RequestOptions | None = None,
    ) -> SendSmsResult:
        return self.gateway.send(request, options=options)

    def get_balance(self, *, options: RequestOptions | None = None) -> SmsBalance | None:
        return self.gateway.get_balance(options=options)

    def parse_delivery_report(self, payload: Mapping[str, object]) -> DeliveryReport | None:
        return self.gateway.parse_delivery_report(payload)

    def close(self) -> None:
        self.gateway.close()

    def __enter__(self) -> SmsClient:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()


class AsyncSmsClient:
    def __init__(self, gateway: AsyncSmsGateway) -> None:
        self.gateway = gateway

    @property
    def provider(self) -> str:
        return self.gateway.provider_name

    async def send(
        self,
        request: SendSmsRequest,
        *,
        options: RequestOptions | None = None,
    ) -> SendSmsResult:
        return await self.gateway.asend(request, options=options)

    async def get_balance(self, *, options: RequestOptions | None = None) -> SmsBalance | None:
        return await self.gateway.aget_balance(options=options)

    def parse_delivery_report(self, payload: Mapping[str, object]) -> DeliveryReport | None:
        return self.gateway.parse_delivery_report(payload)

    async def aclose(self) -> None:
        await self.gateway.aclose()

    async def __aenter__(self) -> AsyncSmsClient:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.aclose()
