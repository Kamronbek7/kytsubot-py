# API qo'llanmasi

## `Bot`

Bot tokenli `bot.kytsubot.uz` endpointlarini qoplaydi:

- `health()`;
- `get_updates(consumer_id, offset, limit, timeout)`;
- `ack_update(update_id, consumer_id)`;
- `send_message(chat_id, text, attachments, idempotency_key)`;
- `upload_file(source, filename)`;
- `download_file(file_id)`;
- `close()`.

`offset` faqat recovery/debug uchun. Oddiy polling serverda saqlanadigan `consumer_id`
cursoridan foydalanadi.

Production Bot API tartibi: `bot.inviprog.uz` → tarmoq xatosida `bot.kytsubot.uz`.
`test_mode=True` faqat localhost `8081`ni ishlatadi va production fallbacklarni qo'llamaydi.

## `Dispatcher`

- `include_router()` / `include_routers()`;
- `feed_update()` — test yoki maxsus transport uchun bitta update;
- `start_polling()` — async long polling;
- `run_polling()` — oddiy sync entrypoint;
- `stop_polling()`;
- `startup()` va `shutdown()` callback registratsiyasi.

Handler exception bersa update ACK qilinmaydi. `@router.error()` bilan exception handler
yozish mumkin, lekin xato bo'lgan update baribir avtomatik ACK qilinmaydi.

## Filtrlar

```python
Command("start")
Command("start", "help")
Keyword("ha", "yo'q")
Keyword("muhim", contains=True)
F.text == "ping"
F.text.casefold() == "salom"
F.text.startswith("/admin")
F.text.contains("hisobot")
F.text.regexp(r"^ID: \\d+$")
F.sender_type == "user"
```

Custom filtr `event` qabul qilib `bool`, `dict` yoki awaitable natija qaytaradigan callable
bo'lishi mumkin. `dict` qiymatlar handler argumentlariga uzatiladi.

## `Message`

Asosiy maydonlar: `message_id`, `chat_id`, `sender_type`, `text`, `attachments`,
`created_at`. Pollingdan kelgan message Bot'ga bog'lanadi va quyidagilarni beradi:

```python
await message.answer("Javob")
await message.reply("Javob")
```

## `KytsuClient`

Asosiy sayt/user API'sining barcha joriy endpointlarini qoplaydi:

- `health`;
- `create_guest`, `register`, `login`, `get_me`;
- `list_bots`, `get_bot`, `list_owned_bots`;
- `create_bot`, `update_bot`, `delete_bot`, `rotate_bot_token`;
- `start_bot`, `stop_bot`, `list_messages`, `send_message`;
- `upload_file`, `download_file`.

Auth metodlari muvaffaqiyatli bo'lsa session token klientga avtomatik o'rnatiladi.
`test_mode=True` user API uchun `http://127.0.0.1:8080`ni tanlaydi.
Production user API tartibi: `kytsubot.inviprog.uz` → tarmoq xatosida `kytsubot.uz`.

## Xatolar

Barcha SDK xatolari `KytsuBotError`dan kelib chiqadi. HTTP holatlari uchun:

- `Unauthorized`;
- `Forbidden`;
- `NotFound`;
- `Conflict`;
- `RateLimited`;
- `ServerUnavailable`;
- `NetworkError`;
- `InvalidResponse`.

Har bir `APIError`da `status_code`, server `code` va `details` mavjud.
