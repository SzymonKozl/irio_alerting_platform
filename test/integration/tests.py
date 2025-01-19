from test_env.helpers import handle_child_death
import signal


def test_sending_alert():
    pass


if __name__ == '__main__':
    signal.signal(signal.SIGCHLD, handle_child_death)