# `noria-sms`

Reusable Python SMS SDK with pluggable gateway integrations.

The package is now `httpx`-based and async-first, while still keeping a sync API for callers that do not want to run an event loop. Provider-specific code lives in dedicated adapters instead of leaking into the public API. `OnfonGateway` is the first implementation.

## Install

```bash
pip install noria-sms
```

Python requirement: `>=3.11`

## Current Scope

Implemented now:

- generic SMS request and result models
- pluggable sync and async gateway protocols
- reusable `httpx` transport with retry and hooks
- Onfon SMS send
- Onfon balance lookup
- Onfon delivery-report parsing

Not implemented yet:

- other SMS gateways
- provider-side template and group management
- framework-specific webhook helpers

## Main Exports

```python
from noria_sms import (
    AsyncSmsClient,
    GatewayError,
    OnfonGateway,
    SendSmsRequest,
    SmsMessage,
    SmsClient,
)
```

## Quick Start

### Async

```python
import asyncio

from noria_sms import AsyncSmsClient, OnfonGateway, SendSmsRequest, SmsMessage


async def main() -> None:
    gateway = OnfonGateway(
        access_key="your-access-key",
        api_key="your-api-key",
        client_id="your-client-id",
        default_sender_id="NORIA",
    )

    async with AsyncSmsClient(gateway) as sms:
        result = await sms.send(
            SendSmsRequest(
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
from noria_sms import OnfonGateway, SendSmsRequest, SmsClient, SmsMessage

gateway = OnfonGateway(
    access_key="your-access-key",
    api_key="your-api-key",
    client_id="your-client-id",
    default_sender_id="NORIA",
)

sms = SmsClient(gateway)

result = sms.send(
    SendSmsRequest(
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
balance = await sms.get_balance()

for entry in balance.entries:
    print(entry.label, entry.credits_raw, entry.credits)
```

Sync:

```python
balance = sms.get_balance()
```

## Delivery Reports

`OnfonGateway` exposes a parser for the documented DLR query string shape:

```python
report = sms.parse_delivery_report(
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

## Extending With More Gateways

Future providers should implement the `AsyncSmsGateway` and `SmsGateway` contracts and live under `noria_sms.gateways`.

That keeps:

- shared transport and retry behavior reusable
- provider response quirks isolated
- the public send/balance/DLR models stable across gateways

## Source Reference

The first implementation was built from the local `ONFON_HTTP_SMS_API_GUIDE.md` guide.
