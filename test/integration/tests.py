from test_env.helpers import (
    handle_child_death,
    AlertingServiceHandle,
    MockServiceHandle,
    PingingJob,
    MailServer
)
import signal
from time import sleep


def test_sending_alert():
    mail_server = MailServer(port=1025)
    sleep(2)
    alert_service = AlertingServiceHandle()
    mock_service = MockServiceHandle(7000)
    sleep(0.5)
    new_job = PingingJob("dziekan@localhost", "student@localhost", 100, mock_service, 1000, 1000)
    alert_service.add_pinging_job(new_job)

    mock_service.respond_404()
    sleep(3)

    assert mail_server.got_mail_to("dziekan@localhost")
    sleep(1)
    assert mail_server.got_mail_to("student@localhost")


if __name__ == '__main__':
    orig = signal.signal(signal.SIGCHLD, handle_child_death)

    test_sending_alert()

    signal.signal(signal.SIGCHLD, orig)
    sleep(2)
    exit(0)
