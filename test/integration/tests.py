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
    try:
        sleep(5)
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
    finally:
        signal.signal(signal.SIGCHLD, orig)
        mail_server.stop()
        mock_service.close()
        alert_service.close()


def test_normal_behavior():
    orig = signal.signal(signal.SIGCHLD, handle_child_death)
    mail_server = MailServer(port=1025)
    sleep(2)
    alert_service = AlertingServiceHandle(LOGS_DIR)
    mock_service = MockServiceHandle(7000, LOGS_DIR)
    sleep(5)
    try:
        new_job = PingingJob("poker@localhost", "calka@localhost", 100, mock_service, 1000, 5000)
        alert_service.add_pinging_job(new_job)
        sleep(10)
        assert mail_server.last_mail_to("poker@localhost") is None
        assert mail_server.last_mail_to("calka@localhost") is None
    finally:
        signal.signal(signal.SIGCHLD, orig)
        mail_server.stop()
        mock_service.close()
        alert_service.close()


def test_deleting_job():
    orig = signal.signal(signal.SIGCHLD, handle_child_death)
    mail_server = MailServer(port=1025)
    sleep(2)
    alert_service = AlertingServiceHandle(LOGS_DIR)
    mock_service = MockServiceHandle(7000, LOGS_DIR)
    sleep(5)
    try:
        job = PingingJob("mail1@localhost", "mail2@localhost", 100, mock_service, 1000, 5000)
        assert mock_service.get_pings_received() == 0
        job_id = alert_service.add_pinging_job(job)
        sleep(1)
        assert mock_service.get_pings_received() > 0
        alert_service.remove_pinging_job(job_id)
        sleep(3) # after that number of pings should stabilize
        pings_received = mock_service.get_pings_received()
        sleep(1)
        assert (t:=mock_service.get_pings_received()) == pings_received, f"{t}!={pings_received}"
    finally:
        signal.signal(signal.SIGCHLD, orig)
        mail_server.stop()
        mock_service.close()
        alert_service.close()


if __name__ == '__main__':

    test_sending_alert()
    sleep(0.5)
    test_normal_behavior()
    sleep(0.5)
    test_deleting_job()
    exit(0)
