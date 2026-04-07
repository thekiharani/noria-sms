# `noria-messaging`

Reusable Python messaging SDK with channel-oriented gateway integrations.

The package is `httpx`-based and async-first, while still keeping a sync API for callers that do not want to run an event loop. The public surface is split by channel so SMS, WhatsApp, and future transports can evolve without being forced into one payload model.

## Install

```bash
pip install noria-messaging
```

Python requirement: `>=3.11`

## Current Scope

Implemented now:

- top-level sync and async messaging clients
- pluggable sync and async channel gateway protocols
- reusable `httpx` transport with retry and hooks
- SMS channel models and services
- Onfon SMS send
- Onfon balance lookup
- Onfon delivery-report parsing
- WhatsApp channel scaffolding for future gateways

Not implemented yet:

- WhatsApp provider adapters
- other SMS gateways
- provider-side template and group management
- framework-specific webhook helpers

## Main Exports

```python
from noria_messaging import (
    AsyncMessagingClient,
    GatewayError,
    OnfonSmsGateway,
    SmsSendRequest,
    SmsMessage,
    MessagingClient,
    WhatsAppTextRequest,
)
```

## Quick Start

### Async

```python
import asyncio

from noria_messaging import AsyncMessagingClient, OnfonSmsGateway, SmsMessage, SmsSendRequest


async def main() -> None:
    gateway = OnfonSmsGateway(
        access_key="your-access-key",
        api_key="your-api-key",
        client_id="your-client-id",
        default_sender_id="NORIA",
    )

    async with AsyncMessagingClient(sms=gateway) as messaging:
        result = await messaging.sms.send(
            SmsSendRequest(
                messages=[
                    SmsMessage(recipient="254712345678", text="Hello Alice", reference="user-1"),
                    SmsMessage(recipient="254722345678", text="Hello Bob", reference="user-2"),
                ],
                is_unicode=False,
                is_flash=False,
            )
        )

    for receipt in result.messages:
        print(receipt.recipient, receipt.status, receipt.provider_message_id)


asyncio.run(main())
```

### Sync Fallback

```python
from noria_messaging import MessagingClient, OnfonSmsGateway, SmsMessage, SmsSendRequest

gateway = OnfonSmsGateway(
    access_key="your-access-key",
    api_key="your-api-key",
    client_id="your-client-id",
    default_sender_id="NORIA",
)

messaging = MessagingClient(sms=gateway)

result = messaging.sms.send(
    SmsSendRequest(
        messages=[
            SmsMessage(recipient="254712345678", text="Hello Alice", reference="user-1"),
            SmsMessage(recipient="254722345678", text="Hello Bob", reference="user-2"),
        ],
        is_unicode=False,
        is_flash=False,
    )
)

for receipt in result.messages:
    print(receipt.recipient, receipt.status, receipt.provider_message_id)
```

## Balance

Async:

```python
balance = await messaging.sms.get_balance()

for entry in balance.entries:
    print(entry.label, entry.credits_raw, entry.credits)
```

Sync:

```python
balance = messaging.sms.get_balance()
```

## Delivery Events

`OnfonSmsGateway` exposes a parser for the documented DLR query string shape and returns a normalized delivery event:

```python
event = messaging.sms.parse_delivery_report(
    {
        "messageId": "fc103131-5931-4530-ba8e-aa223c769536",
        "mobile": "254712345678",
        "status": "DELIVRD",
        "errorCode": "000",
        "submitDate": "2026-04-08 09:30",
        "doneDate": "2026-04-08 09:31",
    }
)
```

## Channel Layout

Future providers should implement the channel gateway contracts and live under the relevant channel package:

- `noria_messaging.channels.sms.gateways`
- `noria_messaging.channels.whatsapp.gateways`

That keeps shared transport and retry behavior reusable while still letting each channel have its own request models.

## Source Reference

The first implementation was built from the local `ONFON_HTTP_SMS_API_GUIDE.md` guide.
