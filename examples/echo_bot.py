import os

from kytsubot import Bot, Command, Dispatcher, Message, Router

router = Router(name="echo")


@router.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer("Salom! Yozgan xabaringizni qaytaraman.")


@router.message()
async def echo(message: Message) -> None:
    await message.answer(f"Echo: {message.text or ''}")


def main() -> None:
    bot = Bot(
        os.environ["KYTSUBOT_BOT_TOKEN"],
        test_mode=os.getenv("KYTSUBOT_TEST_MODE", "1") == "1",
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    dispatcher.run_polling(bot)


if __name__ == "__main__":
    main()

