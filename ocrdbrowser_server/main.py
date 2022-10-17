import asyncio
import logging
from pathlib import Path
from uuid import uuid4
import requests

from fastapi import FastAPI, Response, WebSocket, Request
from fastapi import Cookie
from fastapi.templating import Jinja2Templates
import websockets.client as client

import ocrdbrowser
from ocrdbrowser import OcrdBrowser, DockerOcrdBrowserFactory


app = FastAPI()

templates = Jinja2Templates(directory="ocrdbrowser_server/templates")

running_browsers = set()


def _proxy(path: str):
    print("Proxy to", path)
    t_resp = requests.request(method="GET", url=path, allow_redirects=False)

    response = Response(
        content=t_resp.content, status_code=t_resp.status_code, headers=t_resp.headers
    )
    return response


@app.get("/")
def list_workspaces(request: Request):
    workspaces = Path("ocrd_examples")
    valid_workspaces = ocrdbrowser.workspace.list_all(str(workspaces))
    res = templates.TemplateResponse(
        "index.html.j2", {"workspaces": valid_workspaces, "request": request}
    )
    session_id = request.cookies.get("session_id")
    print("SESSION ID", session_id)
    if not session_id:
        res.set_cookie("session_id", str(uuid4()))

    return res


@app.get("/browse/{path:path}")
def browse(path: str, request: Request):
    session_id = request.cookies.get("session_id")
    print("SESSION ID", session_id)
    print(running_browsers)
    if not running_browsers:
        browser = ocrdbrowser.launch(
            path,
            session_id,
            DockerOcrdBrowserFactory("http://localhost", set(range(8100, 8200))),
            running_browsers,
        )

        running_browsers.add(browser)

    return templates.TemplateResponse(
        "view_workspace.html.j2", {"request": request}
    )


@app.get("/browser")
@app.get("/{path:path}")
def reverse_proxy(request: Request, path: str = ""):
    session_id = request.cookies.get("session_id")
    print("SESSION_ID", session_id)
    print(f"{path=}")
    print([b for b in running_browsers])
    my_browser = running_browsers
    path = path.removeprefix("browser/")
    if my_browser:
        browser = my_browser.pop()
        my_browser.add(browser)
        print(browser.address() + "/" + path)
        return _proxy(browser.address() + "/" + path)
    return Response(status_code=404)


@app.websocket("/browser/socket")
async def broadway_socket_proxy(websocket: WebSocket, session_id = Cookie()):
    print(session_id)
    print("SOCKET SESSION ID", session_id)

    browser = running_browsers.pop()
    running_browsers.add(browser)

    socket_address = browser.address().replace("http://", "ws://")

    await websocket.accept(subprotocol="broadway")
    async with client.connect(
        socket_address + "/socket",
        subprotocols=("broadway",),
        open_timeout=None,
        ping_timeout=None,
        close_timeout=None,
        max_size=2 ** 32
    ) as broadway_socket:
        while True:
            try:
                client_data = await asyncio.wait_for(websocket.receive_bytes(), 0.001)
                await broadway_socket.send(client_data)
            except asyncio.exceptions.TimeoutError:
                logging.info("Timeout occurred on receive from client")

            try:
                broadway_data = await asyncio.wait_for(broadway_socket.recv(), 0.001)
                await websocket.send_bytes(broadway_data)
            except asyncio.exceptions.TimeoutError:
                logging.info("Timeout occurred on receive from broadway")
