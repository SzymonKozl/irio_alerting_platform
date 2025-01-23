from test_env.helpers import (
    handle_child_death,
    AlertingServiceHandle,
    MockServiceHandle,
    PingingJob,
    MailServer,
    scrap_ack_url
)
import signal
from time import sleep


LOGS_DIR = '../../logs'


def test_sending_alert():
    orig = signal.signal(signal.SIGCHLD, handle_child_death)
    mail_server = MailServer(port=1025)
    sleep(2)
    alert_service = AlertingServiceHandle(LOGS_DIR)
    mock_service = MockServiceHandle(7000, LOGS_DIR)
    sleep(0.5)
    new_job = PingingJob("dziekan@localhost", "student@localhost", 100, mock_service, 1000, 1000)
    alert_service.add_pinging_job(new_job)
    mock_service.respond_404()
    sleep(3)
    assert mail_server.last_mail_to("dziekan@localhost") is not None
    sleep(1)
    assert mail_server.last_mail_to("student@localhost") is not None

    mock_service.respond_normal()
    new_job = PingingJob("piwo@localhost", "sesja@localhost", 100, mock_service, 1000, 5000)
    alert_service.add_pinging_job(new_job)
    mock_service.respond_timeout()
    sleep(3)
    mail_content = mail_server.last_mail_to("piwo@localhost")
    assert mail_content is not None
    ack_link = scrap_ack_url(mail_content)
    alert_service.confirm_alert(ack_link)
    sleep(5)
    assert mail_server.last_mail_to("sesja@localhost") is None

    signal.signal(signal.SIGCHLD, orig)
    mail_server.stop()
    mock_service.close()


if __name__ == '__main__':

    test_sending_alert()
    sleep(2)
    exit(0)
