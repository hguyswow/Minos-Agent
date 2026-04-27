import asyncio
import httpx
import time

async def main():
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get("https://api.telegram.org/bot8402067065:AAGtO7q_PWqp9xBjHyjTJHnNIZxfj06_rlk/getMe")
            print("HTTPX Success:", resp.status_code, resp.text[:100])
    except Exception as e:
        print("HTTPX Error:", type(e), e)
    print(f"Elapsed: {time.time() - start:.2f}s")

asyncio.run(main())
