import asyncio
import json
import websockets

ROOM = "6GUATW"
CURRENT_HOST = "1b3cdf0a-21d7-4d1c-971b-b17494f5a556"
NEW_HOST = "94e379ba-93f0-464c-949a-27b2558cb838"


async def main():
    url = f"ws://127.0.0.1:8000/ws/rooms/{ROOM}/{CURRENT_HOST}"

    async with websockets.connect(url) as ws:
        print("CURRENT HOST CONNECTED")

        # Initial sync
        message = await ws.recv()
        print("CURRENT HOST RECEIVED:", message)

        # Transfer host
        await ws.send(json.dumps({
            "event": "transfer_host",
            "payload": {
                "userId": NEW_HOST
            },
            "requestId": "host-transfer-test"
        }))

        print("CURRENT HOST SENT: transfer_host")

        message = await ws.recv()
        print("CURRENT HOST RECEIVED:", message)

        await asyncio.sleep(2)


asyncio.run(main())