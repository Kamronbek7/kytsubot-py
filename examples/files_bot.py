import os
from pathlib import Path

from kytsubot import Bot, Command, Dispatcher, Message, Router

router = Router(name="files")


@router.message(Command("document"))
async def document(message: Message, bot: Bot) -> None:
    uploaded = await bot.upload_file(Path("example.txt"))
    await message.answer("Tayyor fayl", attachments=[uploaded.file_id])


bot = Bot(os.environ["KYTSUBOT_BOT_TOKEN"], test_mode=True)
dispatcher = Dispatcher()
dispatcher.include_router(router)
dispatcher.run_polling(bot)

