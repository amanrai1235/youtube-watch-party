import asyncio
import websockets

ROOM = "6GUATW"
PARTICIPANT = "82dcbd70-8c3b-48f4-b26f-58628d80f817"


async def main():
    url = f"ws://127.0.0.1:8000/ws/rooms/{ROOM}/{PARTICIPANT}"

    async with websockets.connect(url) as ws:
        print("REMOVETEST CONNECTED")

        while True:
            message = await ws.recv()
            print("REMOVETEST RECEIVED:", message)


asyncio.run(main())