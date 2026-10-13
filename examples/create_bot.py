import asyncio
import getpass

from kytsubot import AccessPolicy, KytsuClient, Visibility


async def main() -> None:
    email = (await asyncio.to_thread(input, "Email: ")).strip()
    password = await asyncio.to_thread(getpass.getpass, "Parol: ")
    async with KytsuClient(test_mode=True) as client:
        await client.login(email, password)
        created = await client.create_bot(
            "SDK Echo Bot",
            username="sdk_echo_bot",
            description="Python SDK orqali yaratilgan test bot",
            visibility=Visibility.PUBLIC,
            access_policy=AccessPolicy.GUEST_ALLOWED,
        )
        print(f"Bot: @{created.bot.username}")
        print("Token faqat hozir ko'rsatiladi:")
        print(created.bot_token)


if __name__ == "__main__":
    asyncio.run(main())

