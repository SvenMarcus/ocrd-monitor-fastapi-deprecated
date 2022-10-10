import asyncio
import logging
import requests

from fastapi import FastAPI, Response, WebSocket
from fastapi.templating import Jinja2Templates
import websockets.client as client

app = FastAPI()

templates = Jinja2Templates(directory="ocrdbrowser_server/templates")


def _proxy(path: str):
    t_resp = requests.request(
        method="GET", url="http://localhost:8085/" + path, allow_redirects=False
    )

    response = Response(
        content=t_resp.content, status_code=t_resp.status_code, headers=t_resp.headers
    )
    return response


@app.get("/{path:path}")
def index(path: str):
    return _proxy(path)


@app.websocket("/socket")
async def broadway_socket_proxy(websocket: WebSocket):
    await websocket.accept(subprotocol="broadway")
    async with client.connect(
        "ws://localhost:8085/socket",
        subprotocols=("broadway",),
        open_timeout=None,
        ping_timeout=None,
        close_timeout=None,
    ) as broadway_socket:
        while True:
            try:
                client_data = await asyncio.wait_for(websocket.receive_bytes(), .01)
                await broadway_socket.send(client_data)
            except asyncio.exceptions.TimeoutError:
                logging.info("Timeout occurred on receive from client")

            try:
                broadway_data = await asyncio.wait_for(broadway_socket.recv(), .01)
                await websocket.send_bytes(broadway_data)
            except asyncio.exceptions.TimeoutError:
                logging.info("Timeout occurred on receive from broadway")