import asyncio
import websockets

ROOM = "6GUATW"
PARTICIPANT = "1b3cdf0a-21d7-4d1c-971b-b17494f5a556"

async def main():
    url = f"ws://127.0.0.1:8000/ws/rooms/{ROOM}/{PARTICIPANT}"
    print("CONNECTING:", url)

    async with websockets.connect(url) as ws:
        print("HOST CONNECTED")
        message = await ws.recv()
        print("HOST RECEIVED:", message)

asyncio.run(main())