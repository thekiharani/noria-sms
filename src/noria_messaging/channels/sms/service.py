from __future__ import annotations

from collections.abc import Mapping

from ...events import DeliveryEvent
from ...exceptions import ConfigurationError
from ...types import RequestOptions
from .gateways.base import AsyncSmsGateway, SmsGateway
from .models import SmsBalance, SmsSendRequest, SmsSendResult


class SmsService:
    def __init__(self, gateway: SmsGateway | None) -> None:
        self.gateway = gateway

    @property
    def configured(self) -> bool:
        return self.gateway is not None

    @property
    def provider(self) -> str | None:
        if self.gateway is None:
            return None
        return self.gateway.provider_name

    def send(
        self,
        request: SmsSendRequest,
        *,
        options: RequestOptions | None = None,
    ) -> SmsSendResult:
        return _require_gateway(self.gateway).send(request, options=options)

    def get_balance(self, *, options: RequestOptions | None = None) -> SmsBalance | None:
        return _require_gateway(self.gateway).get_balance(options=options)

    def parse_delivery_report(self, payload: Mapping[str, object]) -> DeliveryEvent | None:
        return _require_gateway(self.gateway).parse_delivery_report(payload)

    def close(self) -> None:
        if self.gateway is not None:
            self.gateway.close()


class AsyncSmsService:
    def __init__(self, gateway: AsyncSmsGateway | None) -> None:
        self.gateway = gateway

    @property
    def configured(self) -> bool:
        return self.gateway is not None

    @property
    def provider(self) -> str | None:
        if self.gateway is None:
            return None
        return self.gateway.provider_name

    async def send(
        self,
        request: SmsSendRequest,
        *,
        options: RequestOptions | None = None,
    ) -> SmsSendResult:
        return await _require_async_gateway(self.gateway).asend(request, options=options)

    async def get_balance(self, *, options: RequestOptions | None = None) -> SmsBalance | None:
        return await _require_async_gateway(self.gateway).aget_balance(options=options)

    def parse_delivery_report(self, payload: Mapping[str, object]) -> DeliveryEvent | None:
        return _require_async_gateway(self.gateway).parse_delivery_report(payload)

    async def aclose(self) -> None:
        if self.gateway is not None:
            await self.gateway.aclose()


def _require_gateway(gateway: SmsGateway | None) -> SmsGateway:
    if gateway is None:
        raise ConfigurationError("SMS gateway is not configured on this client.")
    return gateway


def _require_async_gateway(gateway: AsyncSmsGateway | None) -> AsyncSmsGateway:
    if gateway is None:
        raise ConfigurationError("SMS gateway is not configured on this client.")
    return gateway
