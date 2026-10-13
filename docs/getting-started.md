# Boshlash

## Talablar

- Python 3.11–3.13;
- `httpx`;
- ishlayotgan KytsuBot `server` va botlar uchun `botapi`;
- bot tokeni.

Lokal serverlarni alohida terminallarda ishga tushirgandan keyin botni test rejimida yarating:

```python
from kytsubot import Bot

bot = Bot("kb_live...", test_mode=True)
```

Production:

```python
bot = Bot("kb_live...")
```

Production'da primary Bot API `https://bot.inviprog.uz`; DNS/connection xatosida
`https://bot.kytsubot.uz` legacy fallback sifatida sinab ko'riladi. HTTP API xatosi
(masalan 401 yoki 500) boshqa hostga avtomatik takrorlanmaydi.

Maxsus API serveri:

```python
bot = Bot("kb_live...", base_url="https://bots.example.com")
```

Custom fallback bilan:

```python
bot = Bot(
    "kb_live...",
    base_url="https://bots-primary.example.com",
    fallback_base_urls=["https://bots-backup.example.com"],
)
```

## Handlerlar

```python
from kytsubot import Command, F, Keyword, Message, Router

router = Router(name="main")


@router.message(Command("start", "help"))
async def commands(message: Message, command) -> None:
    await message.answer(f"Buyruq: {command.command}; argument: {command.args}")


@router.message(Keyword("salom", "hello"))
async def greeting(message: Message) -> None:
    await message.answer("Salom!")


@router.message(F.text.startswith("qidir "))
async def search(message: Message) -> None:
    await message.answer("Qidiruv boshlandi")
```

Handler quyidagilarni nomi orqali avtomatik olishi mumkin:

- `message` yoki `event`;
- `update`;
- `bot`;
- filtr qaytargan qiymatlar, masalan `command`.

Sync handler ham ishlaydi, lekin tarmoq va boshqa I/O ishlari uchun `async def` tavsiya etiladi.

## Routerlarni ajratish

```python
dispatcher.include_routers(admin_router, help_router, main_router)
```

Birinchi mos handler update'ni qabul qiladi. Aniq filtrli handlerlarni umumiy
`@router.message()` handleridan oldin ro'yxatdan o'tkazing.

## Fayllar

```python
uploaded = await bot.upload_file("report.pdf")
await message.answer("Hisobot", attachments=[uploaded.file_id])

downloaded = await bot.download_file(uploaded.file_id)
downloaded.save("downloads")
```

Serverning hozirgi allowlist'i: JPEG, PNG, WebP, PDF, TXT va CSV. Bitta xabarda maksimal
4 attachment.

## Sessionni yopish

`Dispatcher.start_polling()` default holatda Bot HTTP sessionini yakunda yopadi. Botdan
polling tashqarisida foydalanilganda context manager ishlating:

```python
async with Bot(token) as bot:
    await bot.send_message(chat_id, "Salom")
```
