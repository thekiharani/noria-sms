from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

MessageStatus = Literal["submitted", "failed"]


@dataclass(slots=True)
class SmsMessage:
    recipient: str
    text: str
    reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SendSmsRequest:
    messages: Sequence[SmsMessage]
    sender_id: str | None = None
    schedule_at: datetime | str | None = None
    is_unicode: bool | None = None
    is_flash: bool | None = None
    provider_options: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SendReceipt:
    provider: str
    recipient: str
    text: str
    status: MessageStatus
    provider_message_id: str | None = None
    reference: str | None = None
    provider_error_code: str | None = None
    provider_error_description: str | None = None
    raw: object = None


@dataclass(slots=True)
class SendSmsResult:
    provider: str
    accepted: bool
    error_code: str | None
    error_description: str | None
    messages: tuple[SendReceipt, ...]
    raw: object = None

    @property
    def submitted_count(self) -> int:
        return sum(1 for message in self.messages if message.status == "submitted")

    @property
    def failed_count(self) -> int:
        return sum(1 for message in self.messages if message.status == "failed")


@dataclass(slots=True)
class SmsBalanceEntry:
    label: str | None
    credits_raw: str | None
    credits: Decimal | None
    raw: object = None


@dataclass(slots=True)
class SmsBalance:
    provider: str
    entries: tuple[SmsBalanceEntry, ...]
    raw: object = None


@dataclass(slots=True)
class DeliveryReport:
    provider: str
    provider_message_id: str
    recipient: str | None = None
    status: str | None = None
    error_code: str | None = None
    submitted_at: str | None = None
    completed_at: str | None = None
    short_message: str | None = None
    raw: Mapping[str, str | None] = field(default_factory=dict)
