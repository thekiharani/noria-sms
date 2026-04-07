from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx
import pytest

from noria_sms import (
    AsyncSmsClient,
    ConfigurationError,
    GatewayError,
    OnfonGateway,
    RequestOptions,
    RetryPolicy,
    SendSmsRequest,
    SmsClient,
    SmsMessage,
)


@dataclass(slots=True)
class FakeSyncHttpClient:
    responses: list[httpx.Response]
    calls: list[dict[str, Any]] = field(default_factory=list)
    closed: bool = False

    def request(self, **kwargs: Any) -> httpx.Response:
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("No fake responses left.")
        return self.responses.pop(0)

    def close(self) -> None:
        self.closed = True


@dataclass(slots=True)
class FakeAsyncHttpClient:
    responses: list[httpx.Response]
    calls: list[dict[str, Any]] = field(default_factory=list)
    closed: bool = False

    async def request(self, **kwargs: Any) -> httpx.Response:
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("No fake responses left.")
        return self.responses.pop(0)

    async def aclose(self) -> None:
        self.closed = True


def make_response(status_code: int, payload: Any) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=payload,
        headers={"content-type": "application/json"},
    )


def test_sms_client_sends_onfon_messages_and_formats_payload() -> None:
    client = FakeSyncHttpClient(
        responses=[
            make_response(
                200,
                {
                    "ErrorCode": 0,
                    "ErrorDescription": "Success",
                    "Data": [
                        {
                            "MobileNumber": "254712345678",
                            "MessageId": "msg-123",
                        }
                    ],
                },
            )
        ]
    )

    gateway = OnfonGateway(
        access_key="access-key",
        api_key="api-key",
        client_id="client-id",
        default_sender_id="NORIA",
        client=client,
    )
    client = SmsClient(gateway)

    result = client.send(
        SendSmsRequest(
            messages=[SmsMessage(recipient="254712345678", text="Hello Alice", reference="user-1")],
            is_unicode=False,
            is_flash=False,
            schedule_at=datetime(2026, 4, 8, 9, 30),
        )
    )

    assert result.accepted is True
    assert result.submitted_count == 1
    assert result.messages[0].provider_message_id == "msg-123"
    assert client.gateway.client.calls[0]["method"] == "POST"
    assert client.gateway.client.calls[0]["url"] == "https://api.onfonmedia.co.ke/v1/sms/SendBulkSMS"
    assert client.gateway.client.calls[0]["headers"]["AccessKey"] == "access-key"
    assert client.gateway.client.calls[0]["json"]["SenderId"] == "NORIA"
    assert client.gateway.client.calls[0]["json"]["ApiKey"] == "api-key"
    assert client.gateway.client.calls[0]["json"]["ClientId"] == "client-id"
    assert client.gateway.client.calls[0]["json"]["IsUnicode"] is False
    assert client.gateway.client.calls[0]["json"]["IsFlash"] is False
    assert client.gateway.client.calls[0]["json"]["ScheduleDateTime"] == "2026-04-08 09:30"


def test_onfon_gateway_marks_missing_message_ids_as_failed() -> None:
    client = FakeSyncHttpClient(
        responses=[
            make_response(
                200,
                {
                    "ErrorCode": "000",
                    "ErrorDescription": "Success",
                    "Data": [{"MobileNumber": "254712345678"}],
                },
            )
        ]
    )

    gateway = OnfonGateway(
        access_key="access-key",
        api_key="api-key",
        client_id="client-id",
        default_sender_id="NORIA",
        client=client,
    )

    result = gateway.send(
        SendSmsRequest(messages=[SmsMessage(recipient="254712345678", text="Hello Alice")])
    )

    assert result.accepted is True
    assert result.failed_count == 1
    assert result.messages[0].status == "failed"
    assert result.messages[0].provider_error_code == "MISSING_MESSAGE_ID"


def test_onfon_gateway_raises_gateway_error_on_top_level_provider_failure() -> None:
    client = FakeSyncHttpClient(
        responses=[
            make_response(
                200,
                {
                    "ErrorCode": "007",
                    "ErrorDescription": "Invalid API credentials",
                    "Data": [],
                },
            )
        ]
    )

    gateway = OnfonGateway(
        access_key="access-key",
        api_key="api-key",
        client_id="client-id",
        default_sender_id="NORIA",
        client=client,
    )

    with pytest.raises(GatewayError) as exc:
        gateway.send(
            SendSmsRequest(messages=[SmsMessage(recipient="254712345678", text="Hello Alice")])
        )

    assert exc.value.provider == "onfon"
    assert exc.value.error_code == "007"
    assert exc.value.error_description == "Invalid API credentials"


def test_onfon_gateway_parses_balance_response() -> None:
    client = FakeSyncHttpClient(
        responses=[
            make_response(
                200,
                {
                    "ErrorCode": 0,
                    "ErrorDescription": "Success",
                    "Data": [{"PluginType": "SMS", "Credits": "KSh7578560.8000"}],
                },
            )
        ]
    )

    gateway = OnfonGateway(
        access_key="access-key",
        api_key="api-key",
        client_id="client-id",
        client=client,
    )

    balance = gateway.get_balance()

    assert len(balance.entries) == 1
    assert balance.entries[0].label == "SMS"
    assert balance.entries[0].credits_raw == "KSh7578560.8000"
    assert str(balance.entries[0].credits) == "7578560.8000"
    assert client.calls[0]["method"] == "GET"
    assert client.calls[0]["params"] == {"ApiKey": "api-key", "ClientId": "client-id"}


def test_onfon_gateway_parses_delivery_reports() -> None:
    gateway = OnfonGateway(
        access_key="access-key",
        api_key="api-key",
        client_id="client-id",
    )

    report = gateway.parse_delivery_report(
        {
            "messageId": ["msg-123"],
            "mobile": "254712345678",
            "status": "DELIVRD",
            "errorCode": "000",
            "submitDate": "2026-04-08 09:30",
            "doneDate": "2026-04-08 09:31",
            "shortMessage": "Hello Alice",
        }
    )

    assert report is not None
    assert report.provider == "onfon"
    assert report.provider_message_id == "msg-123"
    assert report.recipient == "254712345678"
    assert report.status == "DELIVRD"


def test_onfon_gateway_requires_sender_id_for_send() -> None:
    gateway = OnfonGateway(
        access_key="access-key",
        api_key="api-key",
        client_id="client-id",
    )

    with pytest.raises(ConfigurationError):
        gateway.send(SendSmsRequest(messages=[SmsMessage(recipient="254712345678", text="Hello")]))


def test_onfon_gateway_uses_client_retry_policy_when_retry_true_is_requested() -> None:
    client = FakeSyncHttpClient(
        responses=[
            make_response(500, {"detail": "temporary failure"}),
            make_response(
                200,
                {
                    "ErrorCode": 0,
                    "ErrorDescription": "Success",
                    "Data": [{"MobileNumber": "254712345678", "MessageId": "msg-123"}],
                },
            ),
        ]
    )

    gateway = OnfonGateway(
        access_key="access-key",
        api_key="api-key",
        client_id="client-id",
        default_sender_id="NORIA",
        client=client,
        retry=RetryPolicy(
            max_attempts=2,
            retry_methods=("POST",),
            retry_on_statuses=(500,),
            base_delay_seconds=0.0,
        ),
    )

    result = gateway.send(
        SendSmsRequest(messages=[SmsMessage(recipient="254712345678", text="Hello Alice")]),
        options=RequestOptions(retry=True),
    )

    assert result.submitted_count == 1
    assert len(client.calls) == 2


def test_async_sms_client_sends_messages_with_httpx_async_client() -> None:
    async_client = FakeAsyncHttpClient(
        responses=[
            make_response(
                200,
                {
                    "ErrorCode": 0,
                    "ErrorDescription": "Success",
                    "Data": [
                        {
                            "MobileNumber": "254712345678",
                            "MessageId": "msg-async-123",
                        }
                    ],
                },
            )
        ]
    )

    gateway = OnfonGateway(
        access_key="access-key",
        api_key="api-key",
        client_id="client-id",
        default_sender_id="NORIA",
        async_client=async_client,
    )

    async def run() -> None:
        async with AsyncSmsClient(gateway) as sms:
            result = await sms.send(
                SendSmsRequest(messages=[SmsMessage(recipient="254712345678", text="Hello Alice")])
            )

            assert result.submitted_count == 1
            assert result.messages[0].provider_message_id == "msg-async-123"
            assert async_client.calls[0]["method"] == "POST"
            assert async_client.calls[0]["headers"]["AccessKey"] == "access-key"

        assert async_client.closed is False

    asyncio.run(run())
