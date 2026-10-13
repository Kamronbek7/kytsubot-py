# KytsuBot Python SDK — AI reference

Bu fayl kod generatsiya qiluvchi AI uchun qisqa, normativ kontekst.

## Runtime

- Package: `kytsubot`
- Python: `>=3.11`; CI targetlari 3.11, 3.12, 3.13
- Async HTTP: `httpx.AsyncClient`
- Bot production roots: `https://bot.inviprog.uz`, then network fallback `https://bot.kytsubot.uz`
- Bot test root: `http://127.0.0.1:8081`
- User production roots: `https://kytsubot.inviprog.uz`, then network fallback `https://kytsubot.uz`
- User test root: `http://127.0.0.1:8080`
- API paths internally contain `/v1`; custom `base_url` origin/root yoki `/v1` bilan berilishi
  mumkin, transport ikkala ko'rinishni normallashtiradi.
- `test_mode=True` production hostlar yoki fallbacklardan foydalanmaydi.

## Canonical imports

```python
from kytsubot import Bot, Dispatcher, Router, F, Command, Keyword, Message
```

## Canonical polling program

```python
router = Router()

@router.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer("Hello")

bot = Bot(TOKEN, test_mode=False)
dp = Dispatcher()
dp.include_router(router)
dp.run_polling(bot)
```

## Reliability invariants

- Do not manually ACK inside normal handlers.
- Dispatcher ACKs only after successful handler completion.
- Failed updates remain unacknowledged and can be delivered again.
- Prefer `message.answer()` because it derives `idempotency_key` from `update_id`.
- For direct `bot.send_message()`, supply a stable `idempotency_key` when retry is possible.
- Use one `consumer_id` for workers sharing one queue; use distinct IDs for independent consumers.
- Do not combine explicit `offset` with normal durable-consumer polling unless doing recovery.

## Current update schema

Only `type="message"` is currently emitted. Parsed fields:

```text
Update.update_id: int
Update.type: UpdateType | str
Update.message: Message | None
Update.user: User | None
Update.chat_id: str | None
Update.payload: dict
```

Unknown future update types must remain accessible through `Update.payload` and generic
`@router.update()` handlers.

## Extension rules

- Keep network I/O async.
- Add server methods to `Bot` or `KytsuClient`, never directly to Dispatcher.
- Keep API models tolerant of additional server fields.
- Raise typed SDK exceptions; do not expose raw `httpx` exceptions.
- Keep bot-token and user-session APIs on their separate hosts.
- Update docs, types, exports and tests together.
