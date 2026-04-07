from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import httpx

from ..exceptions import ConfigurationError, GatewayError
from ..http import AsyncHttpClient, HttpClient
from ..models import (
    DeliveryReport,
    SendReceipt,
    SendSmsRequest,
    SendSmsResult,
    SmsBalance,
    SmsBalanceEntry,
)
from ..types import Hooks, HttpRequestOptions, RequestOptions, RetryPolicy
from ..utils import (
    coerce_string,
    first_text,
    format_schedule_time,
    merge_headers,
    normalize_query_mapping,
    parse_decimal_from_text,
    to_object,
)

ONFON_BASE_URL = "https://api.onfonmedia.co.ke/v1/sms"


@dataclass(slots=True)
class OnfonGateway:
    access_key: str
    api_key: str
    client_id: str
    default_sender_id: str | None = None
    base_url: str = ONFON_BASE_URL
    client: httpx.Client | Any | None = None
    async_client: httpx.AsyncClient | Any | None = None
    timeout_seconds: float | None = 30.0
    default_headers: Mapping[str, str] | None = None
    retry: RetryPolicy | None = None
    hooks: Hooks | None = None
    provider_name: str = field(init=False, default="onfon")
    _transport_headers: dict[str, str] = field(init=False, repr=False)
    _http: HttpClient | None = field(init=False, repr=False, default=None)
    _async_http: AsyncHttpClient | None = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self.access_key = _require_text(self.access_key, "access_key")
        self.api_key = _require_text(self.api_key, "api_key")
        self.client_id = _require_text(self.client_id, "client_id")
        self.default_sender_id = coerce_string(self.default_sender_id)
        self._transport_headers = merge_headers(
            self.default_headers,
            {
                "AccessKey": self.access_key,
                "Content-Type": "application/json",
            },
        )

    def send(
        self,
        request: SendSmsRequest,
        *,
        options: RequestOptions | None = None,
    ) -> SendSmsResult:
        payload = self._build_send_payload(request)
        response = self._request(
            HttpRequestOptions(
                path="/SendBulkSMS",
                method="POST",
                body=payload,
                headers=options.headers if options else None,
                timeout_seconds=options.timeout_seconds if options else None,
                retry=options.retry if options else None,
            )
        )
        return self._build_send_result(request, response)

    async def asend(
        self,
        request: SendSmsRequest,
        *,
        options: RequestOptions | None = None,
    ) -> SendSmsResult:
        payload = self._build_send_payload(request)
        response = await self._arequest(
            HttpRequestOptions(
                path="/SendBulkSMS",
                method="POST",
                body=payload,
                headers=options.headers if options else None,
                timeout_seconds=options.timeout_seconds if options else None,
                retry=options.retry if options else None,
            )
        )
        return self._build_send_result(request, response)

    def get_balance(self, *, options: RequestOptions | None = None) -> SmsBalance:
        response = self._request(
            HttpRequestOptions(
                path="/Balance",
                method="GET",
                query=self._auth_query(),
                headers=options.headers if options else None,
                timeout_seconds=options.timeout_seconds if options else None,
                retry=options.retry if options else None,
            )
        )
        return self._build_balance_result(response)

    async def aget_balance(self, *, options: RequestOptions | None = None) -> SmsBalance:
        response = await self._arequest(
            HttpRequestOptions(
                path="/Balance",
                method="GET",
                query=self._auth_query(),
                headers=options.headers if options else None,
                timeout_seconds=options.timeout_seconds if options else None,
                retry=options.retry if options else None,
            )
        )
        return self._build_balance_result(response)

    def parse_delivery_report(self, payload: Mapping[str, object]) -> DeliveryReport | None:
        normalized = normalize_query_mapping(payload)
        provider_message_id = first_text(normalized.get("messageId"), normalized.get("MessageId"))
        if provider_message_id is None:
            return None

        return DeliveryReport(
            provider=self.provider_name,
            provider_message_id=provider_message_id,
            recipient=first_text(normalized.get("mobile"), normalized.get("MobileNumber")),
            status=first_text(normalized.get("status"), normalized.get("Status")),
            error_code=first_text(normalized.get("errorCode"), normalized.get("ErrorCode")),
            submitted_at=first_text(normalized.get("submitDate"), normalized.get("SubmitDate")),
            completed_at=first_text(normalized.get("doneDate"), normalized.get("DoneDate")),
            short_message=first_text(
                normalized.get("shortMessage"),
                normalized.get("ShortMessage"),
            ),
            raw=normalized,
        )

    def close(self) -> None:
        if self._http is not None:
            self._http.close()

    async def aclose(self) -> None:
        if self._async_http is not None:
            await self._async_http.aclose()

    def _build_send_payload(self, request: SendSmsRequest) -> dict[str, Any]:
        _validate_send_request(request)
        sender_id = first_text(request.sender_id, self.default_sender_id)
        if sender_id is None:
            raise ConfigurationError(
                "sender_id is required either on SendSmsRequest or as default_sender_id."
            )

        payload = dict(request.provider_options or {})
        payload.update(
            {
                "SenderId": sender_id,
                "MessageParameters": [
                    {
                        "Number": message.recipient,
                        "Text": message.text,
                    }
                    for message in request.messages
                ],
                "ApiKey": self.api_key,
                "ClientId": self.client_id,
            }
        )

        if request.is_unicode is not None:
            payload["IsUnicode"] = request.is_unicode
        if request.is_flash is not None:
            payload["IsFlash"] = request.is_flash
        if request.schedule_at is not None:
            payload["ScheduleDateTime"] = format_schedule_time(request.schedule_at)

        return payload

    def _build_send_result(
        self,
        request: SendSmsRequest,
        response: Mapping[str, object],
    ) -> SendSmsResult:
        rows = response.get("Data")
        items = rows if isinstance(rows, list) else []
        receipts: list[SendReceipt] = []

        for index, message in enumerate(request.messages):
            row = to_object(items[index]) if index < len(items) else {}
            provider_message_id = coerce_string(row.get("MessageId"))
            recipient = first_text(row.get("MobileNumber"), message.recipient) or message.recipient

            if provider_message_id is None:
                status = "failed"
                provider_error_code = "MISSING_MESSAGE_ID"
                provider_error_description = (
                    "Provider accepted the request but did not return "
                    "a MessageId for this recipient."
                )
            else:
                status = "submitted"
                provider_error_code = None
                provider_error_description = None

            receipts.append(
                SendReceipt(
                    provider=self.provider_name,
                    recipient=recipient,
                    text=message.text,
                    status=status,
                    provider_message_id=provider_message_id,
                    reference=message.reference,
                    provider_error_code=provider_error_code,
                    provider_error_description=provider_error_description,
                    raw=row or None,
                )
            )

        return SendSmsResult(
            provider=self.provider_name,
            accepted=True,
            error_code=_normalize_error_code(response.get("ErrorCode")),
            error_description=coerce_string(response.get("ErrorDescription")),
            messages=tuple(receipts),
            raw=response,
        )

    def _build_balance_result(self, response: Mapping[str, object]) -> SmsBalance:
        rows = response.get("Data")
        items = rows if isinstance(rows, list) else []
        entries = tuple(
            SmsBalanceEntry(
                label=coerce_string(item.get("PluginType")),
                credits_raw=coerce_string(item.get("Credits")),
                credits=parse_decimal_from_text(coerce_string(item.get("Credits"))),
                raw=item,
            )
            for item in (to_object(row) for row in items)
        )
        return SmsBalance(provider=self.provider_name, entries=entries, raw=response)

    def _request(self, options: HttpRequestOptions) -> dict[str, Any]:
        response = self._get_http().request(options)
        return self._validate_response(response)

    async def _arequest(self, options: HttpRequestOptions) -> dict[str, Any]:
        response = await self._get_async_http().request(options)
        return self._validate_response(response)

    def _get_http(self) -> HttpClient:
        if self._http is None:
            self._http = HttpClient(
                base_url=self.base_url,
                client=self.client,
                timeout_seconds=self.timeout_seconds,
                default_headers=self._transport_headers,
                retry=self.retry,
                hooks=self.hooks,
            )
        return self._http

    def _get_async_http(self) -> AsyncHttpClient:
        if self._async_http is None:
            self._async_http = AsyncHttpClient(
                base_url=self.base_url,
                client=self.async_client,
                timeout_seconds=self.timeout_seconds,
                default_headers=self._transport_headers,
                retry=self.retry,
                hooks=self.hooks,
            )
        return self._async_http

    def _validate_response(self, response: object) -> dict[str, Any]:
        payload = to_object(response)
        if not payload:
            raise GatewayError(
                "Onfon returned a non-object response.",
                provider=self.provider_name,
                response_body=response,
            )

        if not _is_success_payload(payload):
            error_code = _normalize_error_code(payload.get("ErrorCode"))
            error_description = (
                coerce_string(payload.get("ErrorDescription")) or "Provider request failed."
            )
            raise GatewayError(
                f"Onfon request failed: {error_description}",
                provider=self.provider_name,
                error_code=error_code,
                error_description=error_description,
                response_body=payload,
            )

        return payload

    def _auth_query(self) -> dict[str, str]:
        return {
            "ApiKey": self.api_key,
            "ClientId": self.client_id,
        }


def _validate_send_request(request: SendSmsRequest) -> None:
    if not request.messages:
        raise ValueError("SendSmsRequest.messages must not be empty.")

    for index, message in enumerate(request.messages):
        if coerce_string(message.recipient) is None:
            raise ValueError(f"messages[{index}].recipient must not be empty.")
        if coerce_string(message.text) is None:
            raise ValueError(f"messages[{index}].text must not be empty.")


def _require_text(value: str | None, field_name: str) -> str:
    text = coerce_string(value)
    if text is None:
        raise ConfigurationError(f"{field_name} is required.")
    return text


def _normalize_error_code(value: object) -> str | None:
    text = coerce_string(value)
    if text is None:
        return None
    if text.isdigit():
        return text.zfill(3)
    return text


def _is_success_payload(payload: Mapping[str, object]) -> bool:
    error_code = payload.get("ErrorCode")
    error_description = coerce_string(payload.get("ErrorDescription"))
    if not _is_success_code(error_code):
        return False
    if error_description is None:
        return True
    return "success" in error_description.lower()


def _is_success_code(value: object) -> bool:
    text = coerce_string(value)
    if text is None:
        return False
    try:
        return int(text) == 0
    except ValueError:
        return False
