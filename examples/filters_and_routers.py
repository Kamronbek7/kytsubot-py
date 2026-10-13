import os

from kytsubot import Bot, Command, CommandObject, Dispatcher, F, Keyword, Message, Router

commands = Router(name="commands")
conversation = Router(name="conversation")


@commands.message(Command("start"))
async def start(message: Message, command: CommandObject) -> None:
    payload = command.args or "payload yo'q"
    await message.answer(f"Bot ishga tushdi: {payload}")


@conversation.message(Keyword("salom", "hello"))
async def greeting(message: Message) -> None:
    await message.answer("Salom!")


@conversation.message(F.text.regexp(r"^hisobot\s+\d+$"))
async def report(message: Message) -> None:
    await message.answer("Hisobot so'rovi qabul qilindi.")


@conversation.message(F.attachments)
async def attachment(message: Message) -> None:
    await message.answer(f"{len(message.attachments)} ta fayl olindi.")


bot = Bot(os.environ["KYTSUBOT_BOT_TOKEN"], test_mode=True)
dispatcher = Dispatcher()
dispatcher.include_routers(commands, conversation)
dispatcher.run_polling(bot, consumer_id="example")

