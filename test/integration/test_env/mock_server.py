import sys
from asyncio import sleep
from traceback import print_tb

from aiohttp import web
from aiohttp.web import GracefulExit
from sys import argv, exit, stderr, stdout
import signal
import os


response_mode = 'normal'
response_modes = {'normal', 'timeout', '404'}


def panic(where: str, reason: str) -> None:
    stderr.write("error in mock server:\n")
    stderr.write(f"{where}\n")
    stderr.write("reason:\n")
    stderr.write(f"{reason}\n")
    raise GracefulExit()


async def set_response_mode(request: web.Request) -> web.Response:
    global response_mode
    try:
        mode = request.query['mode']
        assert mode in response_modes, f"response mode should be one of: {response_modes}"
    except (KeyError, AssertionError) as e:
        panic("set_response_mode", f"{type(e).__name__}: {e}")
    else:
        response_mode = mode
        return web.Response(status=200)


async def pinging_endpoint(request: web.Request) -> web.Response:
    match response_mode:
        case 'normal':
            return web.Response(status=200, text='hello world')
        case 'timeout':
            await sleep(100000)
            return web.Response(status=200, text='hello world')
        case '404':
            return web.Response(status=404)
        case _:
            panic("pinging_endpoint", f"Unknown response mode '{response_mode}'")


app = web.Application()
app.router.add_post('/set_response_mode', set_response_mode)
app.router.add_get('/pinging_endpoint', pinging_endpoint)


def handle_SIGINT(sig, frame):
    raise GracefulExit()


signal.signal(signal.SIGTERM, handle_SIGINT)


if __name__ == '__main__':
    assert len(argv) == 3, "usage: python mock_server.py host port"
    host = argv[1]
    try:
        port = int(argv[2])
    except ValueError:
        raise ValueError("port number must be an integer but was {}".format(argv[2]))
    web.run_app(app, host=host, port=port)