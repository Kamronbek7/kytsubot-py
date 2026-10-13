import asyncio

from kytsubot import KytsuClient


async def main() -> None:
    async with KytsuClient(test_mode=True) as client:
        auth = await client.create_guest()
        print(f"Guest: {auth.user.id}")
        await client.start_bot("echo_bot", payload="python_sdk")
        sent = await client.send_message("echo_bot", "Salom")
        print(f"Yuborildi: {sent.message_id}")


if __name__ == "__main__":
    asyncio.run(main())

