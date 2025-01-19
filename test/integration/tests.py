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
    alert_service = AlertingServiceHandle(6000)
    mock_service = MockServiceHandle(7000)
    mail_server = MailServer(port=587)

    new_job = PingingJob("dziekan@localhost", "student@localhost", 100, mock_service, 1000, 1000)
    alert_service.add_pinging_job(new_job)

    mock_service.respond_404()
    sleep(1)


if __name__ == '__main__':
    signal.signal(signal.SIGCHLD, handle_child_death)

    test_sending_alert()
