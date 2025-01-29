from asyncio import sleep

from aiohttp import web
from aiohttp.web import GracefulExit
from sys import argv, exit, stderr, stdout
import signal
from threading import Lock


response_mode = 'normal'
response_modes = {'normal', 'timeout', '404'}

pings_ctr_lock = Lock()
pings_ctr = 0


def panic(where: str, reason: str) -> None:
    stderr.write("error in mock server:\n")
    stderr.write(f"{where}\n")
    stderr.write("reason:\n")
    stderr.write(f"{reason}\n")
    raise GracefulExit()


async def get_num_of_pings(request: web.Request) -> web.Response:
    global pings_ctr_lock
    with pings_ctr_lock:
        val = pings_ctr
    return web.Response(text=str(val))

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
    global pings_ctr, pings_ctr_lock
    with pings_ctr_lock:
        pings_ctr += 1
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
app.router.add_get('/get_pings_received', get_num_of_pings)
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