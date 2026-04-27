import asyncio
from telegram import Bot

async def main():
    token = "8402067065:AAGtO7q_PWqp9xBjHyjTJHnNIZxfj06_rlk"
    bot = Bot(token)
    try:
        print("Getting me...")
        me = await bot.get_me()
        print("Bot:", me.first_name)
        
        print("Deleting webhook...")
        res = await bot.delete_webhook(drop_pending_updates=True)
        print("Delete webhook result:", res)
        
        print("Getting updates...")
        updates = await bot.get_updates(timeout=10)
        print(f"Got {len(updates)} updates.")
    except Exception as e:
        print("Error:", type(e), str(e))

asyncio.run(main())
